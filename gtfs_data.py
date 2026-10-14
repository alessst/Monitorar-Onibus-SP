"""Dados estáticos (GTFS) da SPTrans: trajetos das linhas e pontos de parada.

O app usa o GTFS para:
  * desenhar o trajeto (shape) de cada linha/sentido;
  * descobrir quais pontos e linhas passam perto de uma coordenada.

Para usar uma versão mais nova (a oficial exige login em sptrans.com.br/desenvolvedores),
basta colocar o .zip em `gtfs/`: o arquivo mais recente da pasta é o que vale.
Se a pasta estiver vazia, baixamos um espelho público (dados de 2022).
"""
import math
import pickle
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).parent
GTFS_DIR = BASE / "gtfs"
CACHE_DIR = BASE / "data"
ESPELHO_URL = "https://github.com/spstreets/gtfs_manager/releases/download/v0.1.0/sao-paulo-sptrans.zip"
VERSAO_CACHE = 1


def _achar_zip() -> Path:
    GTFS_DIR.mkdir(exist_ok=True)
    zips = sorted(GTFS_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if zips:
        return zips[0]
    destino = GTFS_DIR / "sao-paulo-sptrans.zip"
    urllib.request.urlretrieve(ESPELHO_URL, destino)
    return destino


def _processar(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as z:
        def ler(nome, **kw):
            with z.open(nome) as f:
                return pd.read_csv(f, encoding="utf-8-sig", **kw)

        rotas = ler("routes.txt", dtype=str)
        viagens = ler("trips.txt", dtype=str)
        paradas = ler("stops.txt", dtype={"stop_id": str})
        horarios = ler("stop_times.txt", dtype=str, usecols=["trip_id", "stop_id", "stop_sequence"])
        shapes = ler(
            "shapes.txt",
            dtype={"shape_id": str},
            usecols=["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
        )

    # Uma viagem representativa por (linha, sentido), que tenha stop_times.
    viagens = viagens[viagens["trip_id"].isin(set(horarios["trip_id"]))]
    viagens = viagens.drop_duplicates(["route_id", "direction_id"]).copy()
    viagens["direction_id"] = viagens["direction_id"].astype(int)

    # Sequência de pontos de cada viagem representativa.
    horarios = horarios[horarios["trip_id"].isin(set(viagens["trip_id"]))].copy()
    horarios["stop_sequence"] = horarios["stop_sequence"].astype(int)
    horarios = horarios.sort_values(["trip_id", "stop_sequence"])
    seq_por_viagem = horarios.groupby("trip_id")["stop_id"].apply(list).to_dict()

    # Trajetos.
    shapes = shapes[shapes["shape_id"].isin(set(viagens["shape_id"]))]
    shapes = shapes.sort_values(["shape_id", "shape_pt_sequence"])
    shape_por_id = {
        sid: g[["shape_pt_lat", "shape_pt_lon"]].to_numpy(dtype="float32")
        for sid, g in shapes.groupby("shape_id")
    }

    cores = dict(zip(rotas["route_id"], rotas["route_color"]))
    nomes = dict(zip(rotas["route_id"], rotas["route_long_name"]))

    destino, trajeto, pontos_da_linha, linhas_do_ponto = {}, {}, {}, {}
    for v in viagens.itertuples():
        chave = (v.route_id, v.direction_id)
        destino[chave] = v.trip_headsign
        if v.shape_id in shape_por_id:
            trajeto[chave] = shape_por_id[v.shape_id]
        seq = seq_por_viagem.get(v.trip_id, [])
        pontos_da_linha[chave] = seq
        for sid in set(seq):
            linhas_do_ponto.setdefault(sid, []).append(chave)

    usados = paradas[paradas["stop_id"].isin(linhas_do_ponto)].copy()
    return {
        "versao": VERSAO_CACHE,
        "nome_linha": nomes,
        "cor_linha": cores,
        "destino": destino,
        "trajeto": trajeto,
        "pontos_da_linha": pontos_da_linha,
        "linhas_do_ponto": linhas_do_ponto,
        "ponto_info": {
            r.stop_id: (r.stop_name, r.stop_desc if isinstance(r.stop_desc, str) else "")
            for r in usados.itertuples()
        },
        "ponto_ids": usados["stop_id"].to_numpy(),
        "ponto_lat": usados["stop_lat"].to_numpy(dtype="float64"),
        "ponto_lon": usados["stop_lon"].to_numpy(dtype="float64"),
        "origem": zip_path.name,
    }


def carregar() -> dict:
    """Lê o cache processado ou gera a partir do zip (primeira vez leva alguns segundos)."""
    zip_path = _achar_zip()
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / "gtfs_cache.pkl"
    assinatura = (zip_path.name, zip_path.stat().st_mtime, zip_path.stat().st_size, VERSAO_CACHE)
    if cache.exists():
        try:
            with open(cache, "rb") as f:
                salvo = pickle.load(f)
            if salvo.get("assinatura") == assinatura:
                return salvo["dados"]
        except Exception:
            pass
    dados = _processar(zip_path)
    with open(cache, "wb") as f:
        pickle.dump({"assinatura": assinatura, "dados": dados}, f, protocol=pickle.HIGHEST_PROTOCOL)
    return dados


# ----------------- Consultas -----------------
def paradas_proximas(dados: dict, lat: float, lon: float, raio_m: float = 500, limite: int = 15) -> list[dict]:
    """Pontos dentro do raio (aprox. equiretangular), do mais perto ao mais longe."""
    dy = (dados["ponto_lat"] - lat) * 111_320
    dx = (dados["ponto_lon"] - lon) * 111_320 * math.cos(math.radians(lat))
    dist = np.hypot(dx, dy)
    idx = np.where(dist <= raio_m)[0]
    idx = idx[np.argsort(dist[idx])][:limite]
    resultado = []
    for i in idx:
        sid = str(dados["ponto_ids"][i])
        nome, desc = dados["ponto_info"][sid]
        resultado.append({
            "cp": int(sid) if sid.isdigit() else sid,
            "nome": nome,
            "desc": desc,
            "lat": float(dados["ponto_lat"][i]),
            "lon": float(dados["ponto_lon"][i]),
            "dist_m": float(dist[i]),
            "linhas": sorted(dados["linhas_do_ponto"].get(sid, [])),
        })
    return resultado


def _norm(texto: str | None) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def _direcao(dados: dict, letreiro: str, sentido: int, destino_api: str | None) -> int:
    """sl=1 da Olho Vivo equivale a direction_id=1 no GTFS (verificado comparando os destinos).
    Se o destino da API for informado, ele desempata para evitar trajeto invertido."""
    padrao = 2 - sentido
    if destino_api:
        for d in (padrao, 1 - padrao):
            if _norm(dados["destino"].get((letreiro, d))) == _norm(destino_api):
                return d
    return padrao


def trajeto_da_linha(dados: dict, letreiro: str, sentido: int, destino_api: str | None = None):
    """Lista [(lat, lon)] do trajeto. `sentido` é o `sl` da Olho Vivo (1 ou 2)."""
    arr = dados["trajeto"].get((letreiro, _direcao(dados, letreiro, sentido, destino_api)))
    return arr.tolist() if arr is not None else None


def destino_gtfs(dados: dict, letreiro: str, sentido: int) -> str | None:
    return dados["destino"].get((letreiro, _direcao(dados, letreiro, sentido, None)))
