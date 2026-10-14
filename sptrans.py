"""Cliente simples para a API Olho Vivo (SPTrans)."""
import math
from datetime import datetime, timedelta, timezone

import requests

BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"
TIMEOUT = 10
FUSO_SP = timezone(timedelta(hours=-3))  # Brasil não tem horário de verão desde 2019


class SPTransError(Exception):
    """Falha ao falar com a API da SPTrans."""


class SPTransClient:
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self._autenticar()

    def _autenticar(self) -> None:
        try:
            r = self.session.post(
                f"{BASE_URL}/Login/Autenticar", params={"token": self.token}, timeout=TIMEOUT
            )
        except requests.RequestException as e:
            raise SPTransError(f"Sem conexão com a SPTrans: {e}") from e
        if r.text.strip().lower() != "true":
            raise SPTransError("Token inválido ou recusado pela SPTrans.")

    def _get(self, caminho: str, **params):
        for tentativa in range(2):
            try:
                r = self.session.get(f"{BASE_URL}{caminho}", params=params, timeout=TIMEOUT)
            except requests.RequestException as e:
                raise SPTransError(f"Sem conexão com a SPTrans: {e}") from e
            if r.status_code == 401 and tentativa == 0:  # sessão expirou
                self._autenticar()
                continue
            if not r.ok:
                raise SPTransError(f"Erro {r.status_code} da SPTrans.")
            try:
                return r.json()
            except ValueError as e:
                raise SPTransError("Resposta inválida da SPTrans.") from e

    # --- Endpoints ---
    def buscar_linhas(self, termo: str) -> list[dict]:
        return self._get("/Linha/Buscar", termosBusca=termo) or []

    def paradas_da_linha(self, codigo_linha: int) -> list[dict]:
        return self._get("/Parada/BuscarParadasPorLinha", codigoLinha=codigo_linha) or []

    def buscar_paradas(self, termo: str) -> list[dict]:
        return self._get("/Parada/Buscar", termosBusca=termo) or []

    def posicao_linha(self, codigo_linha: int) -> dict:
        return self._get("/Posicao/Linha", codigoLinha=codigo_linha) or {}

    def previsao_linha(self, codigo_linha: int) -> dict:
        return self._get("/Previsao/Linha", codigoLinha=codigo_linha) or {}

    def previsao_parada(self, codigo_parada: int) -> dict:
        return self._get("/Previsao/Parada", codigoParada=codigo_parada) or {}


# --- Utilitários ---
def distancia_km(lat1, lon1, lat2, lon2) -> float:
    """Distância entre dois pontos (Haversine)."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def minutos_ate(hora_ref: str, hora_chegada: str) -> int:
    """Minutos entre 'HH:MM' de referência e 'HH:MM' de chegada (trata virada de dia)."""
    h1, m1 = map(int, hora_ref.split(":"))
    h2, m2 = map(int, hora_chegada.split(":"))
    diff = (h2 * 60 + m2) - (h1 * 60 + m1)
    if diff < -120:
        diff += 1440
    return max(diff, 0)


def hora_local(ta_iso: str) -> str:
    """Converte o timestamp UTC do veículo para HH:MM:SS de São Paulo."""
    try:
        dt = datetime.fromisoformat(ta_iso.replace("Z", "+00:00"))
        return dt.astimezone(FUSO_SP).strftime("%H:%M:%S")
    except (ValueError, AttributeError):
        return ta_iso or "--"

