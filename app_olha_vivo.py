import colorsys
import html
import json
import os

import folium
import requests
import streamlit as st
from folium.plugins import PolyLineTextPath
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval

import gtfs_data
from sptrans import (
    SPTransClient,
    SPTransError,
    distancia_km,
    hora_local,
    minutos_ate,
)

# ======================= CONFIGURAÇÃO =======================
st.set_page_config(page_title="Olho Vivo • Ônibus SP", page_icon="🚌", layout="centered")
st_autorefresh(interval=30000, limit=200, key="atualizacao_onibus")

COR_MARCA = "#F26B21"
NAV = ["📍 Perto de mim", "🚌 Linhas", "🚏 Paradas"]

CSS = """
<style>
header[data-testid="stHeader"], #MainMenu, footer {display:none !important;}
.block-container {max-width:520px; padding:1rem 1rem 4rem;}
.stApp {background:#F4F6FA;}
.hero {background:linear-gradient(135deg,#F26B21 0%,#FF9A44 100%); color:#fff; border-radius:20px;
       padding:18px 20px; margin-bottom:12px; box-shadow:0 6px 18px rgba(242,107,33,.35);}
.hero h1 {font-size:1.35rem; margin:0; padding:0; color:#fff; font-weight:800;}
.hero p {margin:2px 0 0; opacity:.9; font-size:.85rem;}
div[data-baseweb="input"], div[data-baseweb="select"] > div {border-radius:14px !important; background:#fff !important;}
div[data-baseweb="input"] {box-shadow:0 2px 8px rgba(0,0,0,.06);}
.card {background:#fff; border-radius:18px; padding:14px 16px; margin:10px 0; box-shadow:0 2px 10px rgba(20,30,60,.07);}
.card.compact {padding:10px 14px; margin:6px 0;}
.card-title {font-weight:700; color:#1B2437; font-size:1rem;}
.card-sub {color:#6B7588; font-size:.8rem; margin-top:2px;}
.badge {display:inline-block; color:#fff; font-weight:800; border-radius:10px; padding:4px 10px;
        font-size:.95rem; letter-spacing:.3px; margin-right:8px;}
.badge.mini {padding:2px 7px; font-size:.75rem; margin:2px 4px 2px 0; border-radius:8px;}
.row {display:flex; align-items:center; justify-content:space-between; gap:10px;}
.eta-row {display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-top:1px solid #EEF1F6;}
.eta-row:first-of-type {border-top:none;}
.eta-time {font-weight:800; font-size:1.5rem; color:#1B2437; text-align:right; min-width:70px; line-height:1;}
.eta-time span {font-size:.75rem; font-weight:600; color:#6B7588; margin-left:2px;}
.eta-time.soon {color:#10A66A;}
.chip {display:inline-block; background:#FFF1E8; color:#C4510F; border-radius:999px; padding:3px 10px;
       font-size:.75rem; font-weight:700; margin-right:6px;}
.chip.green {background:#E3F7EE; color:#0B7D4F;}
.chip.gray {background:#EEF1F6; color:#4B566B;}
.live {display:inline-block; width:8px; height:8px; border-radius:50%; background:#10A66A; margin-right:5px;
       animation:pulse 1.6s infinite;}
@keyframes pulse {0%{box-shadow:0 0 0 0 rgba(16,166,106,.6);} 70%{box-shadow:0 0 0 8px rgba(16,166,106,0);} 100%{box-shadow:0 0 0 0 rgba(16,166,106,0);}}
.times {font-weight:700; color:#1B2437;}
.muted {color:#8A93A6; font-size:.85rem;}
.sec {font-weight:800; color:#1B2437; margin:16px 0 2px; font-size:1.05rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ======================= HELPERS DE UI =======================
def h(texto) -> str:
    return html.escape(str(texto if texto is not None else ""))


def card(conteudo: str) -> None:
    """Renderiza HTML numa linha só (evita que o Markdown trate indentação como bloco de código)."""
    conteudo = "".join(linha.strip() for linha in conteudo.splitlines())
    st.markdown(conteudo, unsafe_allow_html=True)


def cor_da_linha(letreiro: str) -> str:
    """Cor estável por linha, estilo apps de transporte."""
    hue = (sum(ord(c) * (i + 3) for i, c in enumerate(str(letreiro))) % 360) / 360
    r, g, b = colorsys.hls_to_rgb(hue, 0.38, 0.65)
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


def badge(letreiro: str, mini: bool = False) -> str:
    classe = "badge mini" if mini else "badge"
    return f'<span class="{classe}" style="background:{cor_da_linha(letreiro)}">{h(letreiro)}</span>'


def texto_eta(minutos: int) -> str:
    if minutos <= 0:
        return '<div class="eta-time soon">Agora</div>'
    classe = "soon" if minutos <= 3 else ""
    return f'<div class="eta-time {classe}">{minutos}<span>min</span></div>'


def linha_eta(prefixo: str, minutos: int, acessivel: bool) -> str:
    extra = " · ♿ Acessível" if acessivel else ""
    return (
        f'<div class="eta-row"><div><div class="card-title">Ônibus {h(prefixo)}</div>'
        f'<div class="card-sub"><span class="live"></span>Tempo real{extra}</div></div>{texto_eta(minutos)}</div>'
    )


def dist_txt(metros: float) -> str:
    return f"{metros:.0f} m" if metros < 1000 else f"{metros / 1000:.1f} km"


def chip_caminhada(metros: float) -> str:
    return f'<span class="chip">🚶 {max(1, round(metros / 80))} min · {dist_txt(metros)}</span>'


def mapa_base(centro) -> folium.Map:
    return folium.Map(location=centro, zoom_start=15, tiles="OpenStreetMap", zoom_control=True)


def icone_onibus(cor: str) -> folium.DivIcon:
    return folium.DivIcon(
        icon_size=(30, 30),
        icon_anchor=(15, 15),
        html=(
            f'<div style="background:{cor};border:2px solid #fff;border-radius:50%;width:30px;height:30px;'
            'display:flex;align-items:center;justify-content:center;font-size:15px;'
            'box-shadow:0 2px 6px rgba(0,0,0,.35)">🚌</div>'
        ),
    )


def icone_parada() -> folium.DivIcon:
    return folium.DivIcon(
        icon_size=(34, 34),
        icon_anchor=(17, 34),
        html=(
            f'<div style="background:{COR_MARCA};border:2px solid #fff;border-radius:50% 50% 50% 0;'
            'transform:rotate(-45deg);width:34px;height:34px;box-shadow:0 3px 8px rgba(0,0,0,.4);'
            'display:flex;align-items:center;justify-content:center">'
            '<span style="transform:rotate(45deg);font-size:16px">🚏</span></div>'
        ),
    )


def icone_usuario() -> folium.DivIcon:
    return folium.DivIcon(
        icon_size=(22, 22),
        icon_anchor=(11, 11),
        html=(
            '<style>@keyframes p{0%{box-shadow:0 0 0 0 rgba(30,110,255,.6)}'
            '70%{box-shadow:0 0 0 16px rgba(30,110,255,0)}100%{box-shadow:0 0 0 0 rgba(30,110,255,0)}}</style>'
            '<div style="width:18px;height:18px;border-radius:50%;background:#1E6EFF;border:3px solid #fff;'
            'animation:p 2s infinite"></div>'
        ),
    )


def desenhar_mapa(mapa: folium.Map, pontos_foco: list, key: str) -> None:
    if len(pontos_foco) > 1:
        mapa.fit_bounds(pontos_foco, padding=(40, 40), max_zoom=16)
    st_folium(mapa, height=420, use_container_width=True, returned_objects=[], key=key)


def desenhar_trajeto(mapa: folium.Map, pontos: list, cor: str) -> None:
    """Trajeto da linha: contorno branco + cor da linha + setas de sentido."""
    folium.PolyLine(pontos, color="#FFFFFF", weight=9, opacity=0.95).add_to(mapa)
    linha = folium.PolyLine(pontos, color=cor, weight=5, opacity=0.95).add_to(mapa)
    PolyLineTextPath(
        linha, "      ►      ", repeat=True, offset=6, attributes={"fill": "#FFFFFF", "font-size": "13", "font-weight": "bold"}
    ).add_to(mapa)


# ======================= API (com cache) =======================
def _token() -> str | None:
    try:
        if "SPTRANS_TOKEN" in st.secrets:
            return st.secrets["SPTRANS_TOKEN"]
    except Exception:
        pass
    return os.environ.get("SPTRANS_TOKEN")


TOKEN = _token()
if not TOKEN:
    st.error(
        "Token da SPTrans não configurado. Crie o arquivo `.streamlit/secrets.toml` com "
        '`SPTRANS_TOKEN = "seu_token"` (ou defina a variável de ambiente `SPTRANS_TOKEN`).'
    )
    st.stop()


@st.cache_resource
def cliente() -> SPTransClient:
    return SPTransClient(TOKEN)


@st.cache_data(ttl=600, show_spinner=False)
def api_buscar_linhas(termo):
    return cliente().buscar_linhas(termo)


@st.cache_data(ttl=3600, show_spinner=False)
def api_paradas_da_linha(cl):
    return cliente().paradas_da_linha(cl)


@st.cache_data(ttl=600, show_spinner=False)
def api_buscar_paradas(termo):
    return cliente().buscar_paradas(termo)


@st.cache_data(ttl=15, show_spinner=False)
def api_posicao_linha(cl):
    return cliente().posicao_linha(cl)


@st.cache_data(ttl=15, show_spinner=False)
def api_previsao_linha(cl):
    return cliente().previsao_linha(cl)


@st.cache_data(ttl=15, show_spinner=False)
def api_previsao_parada(cp):
    return cliente().previsao_parada(cp)


@st.cache_resource(show_spinner="Preparando mapa de linhas e pontos (só na primeira vez, ~10 s)...")
def carregar_gtfs() -> dict:
    return gtfs_data.carregar()


def gtfs_ou_none():
    try:
        return carregar_gtfs()
    except Exception as e:  # sem internet para baixar, arquivo corrompido, etc.
        st.session_state["gtfs_erro"] = str(e)
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def geocodificar(endereco: str):
    """Endereço -> (lat, lon, nome) via Nominatim/OpenStreetMap, priorizando São Paulo."""
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": endereco, "format": "json", "limit": 1, "countrycodes": "br",
            "viewbox": "-47.2,-23.2,-46.2,-24.1",
        },
        headers={"User-Agent": "OlhoVivoSP-app/1.0"},
        timeout=10,
    )
    r.raise_for_status()
    dados = r.json()
    if not dados:
        return None
    return float(dados[0]["lat"]), float(dados[0]["lon"]), dados[0]["display_name"]


# ======================= LOCALIZAÇÃO =======================
# Prioridade: endereço informado > GPS desta sessão > última localização salva no aparelho.
# O GPS é pedido automaticamente a cada vez que o app abre (o navegador mostra o pedido de permissão
# se você ainda não escolheu "sempre permitir"). A última posição fica salva no navegador (localStorage)
# só se "Lembrar minha localização" estiver ligado.
st.session_state.setdefault("lembrar", True)
st.session_state.setdefault("gps_n", 0)


def _novo_gps():
    st.session_state["gps_n"] += 1
    st.session_state.pop("pos_manual", None)  # voltar a usar o GPS
    st.session_state.pop("gps_erro", None)


# Pede a posição com timeout (o getLocation() padrão da biblioteca nunca desiste) e devolve o motivo
# da falha em vez de ficar mudo. Códigos: 1 negado, 2 indisponível, 3 demorou, 99 página sem HTTPS.
JS_GPS = (
    "(function(){return new Promise(function(resolve){"
    "if(!navigator.geolocation){resolve({error:{code:0,message:'sem suporte'}});return;}"
    "if(window.isSecureContext===false){resolve({error:{code:99,message:'contexto inseguro'}});return;}"
    "navigator.geolocation.getCurrentPosition("
    "function(p){resolve({coords:{latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy}});},"
    "function(e){resolve({error:{code:e.code,message:e.message}});},"
    "{enableHighAccuracy:false,timeout:15000,maximumAge:300000});"
    "});})()"
)

MSG_GPS = {
    0: "Seu navegador não suporta localização.",
    1: "A permissão de localização foi negada. Toque no cadeado ao lado do endereço do site, "
       "permita **Localização** e depois toque em ⚙️ Localização → 🔄 Atualizar pelo GPS.",
    2: "Não foi possível descobrir sua posição (GPS/rede indisponível). Tente de novo em alguns segundos.",
    3: "A localização demorou demais para responder. Toque em 🔄 Atualizar pelo GPS.",
    99: "O navegador só libera o GPS em páginas seguras (HTTPS ou localhost). "
        "Se você abriu pelo IP da rede (http://192.168...), use o endereço abaixo ou publique o app com HTTPS.",
}


def form_endereco(chave: str) -> None:
    """Campo para informar um endereço quando o GPS não está disponível."""
    end_txt = st.text_input("Endereço", placeholder="Ex: Av. Paulista, 1000", label_visibility="collapsed",
                            key=f"end_txt_{chave}")
    c1, c2 = st.columns(2)
    if c1.button("Usar endereço", key=f"btn_end_{chave}") and end_txt.strip():
        try:
            achado = geocodificar(end_txt.strip())
            if achado:
                st.session_state["pos_manual"] = (achado[0], achado[1])
                st.session_state["pos_manual_nome"] = achado[2]
                st.rerun()
            else:
                st.warning("Endereço não encontrado. Tente incluir o bairro ou a cidade.")
        except requests.RequestException:
            st.error("Não foi possível buscar o endereço agora.")
    if c2.button("Limpar", key=f"btn_limpar_{chave}"):
        st.session_state.pop("pos_manual", None)
        st.rerun()


# 1) lê o que foi salvo neste aparelho (uma vez)
if "prefs_carregadas" not in st.session_state:
    bruto = streamlit_js_eval(js_expressions="localStorage.getItem('olhovivo')", key="ls_read")
    if bruto:
        try:
            prefs = json.loads(bruto)
            st.session_state["lembrar"] = bool(prefs.get("lembrar", True))
            if st.session_state["lembrar"] and prefs.get("lat") is not None:
                st.session_state["pos_salva"] = (prefs["lat"], prefs["lon"])
        except (ValueError, TypeError):
            pass
        st.session_state["prefs_carregadas"] = True

# 2) pede o GPS ao abrir
res_gps = streamlit_js_eval(js_expressions=JS_GPS, key=f"gps_{st.session_state['gps_n']}")
if isinstance(res_gps, dict):
    coords = res_gps.get("coords") or {}
    if coords.get("latitude") is not None and coords.get("longitude") is not None:
        st.session_state["pos_gps"] = (coords["latitude"], coords["longitude"])
        st.session_state.pop("gps_erro", None)
    elif res_gps.get("error"):
        st.session_state["gps_erro"] = res_gps["error"].get("code", 2)

# ======================= CABEÇALHO =======================
st.markdown(
    '<div class="hero"><h1>🚌 Olho Vivo SP</h1><p>Ônibus em tempo real, do jeito que você precisa.</p></div>',
    unsafe_allow_html=True,
)

col_status, col_cfg = st.columns([3, 2], vertical_alignment="center")
with col_cfg:
    with st.popover("⚙️ Localização"):
        st.button("🔄 Atualizar pelo GPS", on_click=_novo_gps, key="btn_gps")
        st.toggle(
            "Lembrar minha localização neste aparelho", key="lembrar",
            help="Ligado: a última posição fica salva e aparece na hora ao abrir o app. "
                 "Desligado: nada é salvo e o app pede o GPS toda vez.",
        )
        st.markdown("**Ou informe um endereço**")
        form_endereco("popover")

if "pos_manual" in st.session_state:
    user_pos, origem_pos = st.session_state["pos_manual"], "Endereço informado"
elif "pos_gps" in st.session_state:
    user_pos, origem_pos = st.session_state["pos_gps"], "GPS ativo"
elif "pos_salva" in st.session_state:
    user_pos, origem_pos = st.session_state["pos_salva"], "Última localização salva"
else:
    user_pos, origem_pos = None, None

# 3) salva (ou apaga) no aparelho. Só grava quando há algo novo para guardar, para nunca apagar a
#    posição salva antes de ela ser lida (ou quando o GPS falhou).
_pos_para_salvar = st.session_state.get("pos_gps") or st.session_state.get("pos_salva")
_payload = {"lembrar": bool(st.session_state["lembrar"])}
if st.session_state["lembrar"] and _pos_para_salvar:
    _payload.update(lat=round(_pos_para_salvar[0], 5), lon=round(_pos_para_salvar[1], 5))
if _payload["lembrar"] is False or "lat" in _payload:
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('olhovivo', {json.dumps(json.dumps(_payload))})",
        key=f"ls_save_{json.dumps(_payload, sort_keys=True)}",
    )

with col_status:
    if user_pos:
        classe = "green" if origem_pos != "Última localização salva" else "gray"
        st.markdown(f'<span class="chip {classe}">📍 {origem_pos}</span>', unsafe_allow_html=True)
    elif st.session_state.get("gps_erro") is not None:
        st.markdown('<span class="chip">📍 Sem localização</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="muted">⏳ Aguardando permissão de localização...</span>', unsafe_allow_html=True)

if origem_pos == "Última localização salva":
    st.caption("Mostrando sua última posição enquanto o GPS atualiza. Se você se mexeu, toque em ⚙️ → Atualizar.")

# ======================= NAVEGAÇÃO =======================
st.session_state.setdefault("aba", NAV[0])
escolha = st.segmented_control("Navegação", NAV, key="aba", label_visibility="collapsed")
aba = escolha or st.session_state.get("_aba_anterior", NAV[0])  # clicar na aba ativa a "desmarca"
st.session_state["_aba_anterior"] = aba


# ======================= FUNÇÕES COMPARTILHADAS =======================
def destino_da_linha(l: dict) -> str:
    # sl: 1 = Terminal Principal -> Secundário, 2 = Secundário -> Principal
    return l["ts"] if l["sl"] == 1 else l["tp"]


def rotulo_linha(l: dict) -> str:
    return f"{l['lt']}-{l['tl']}  ➜  {destino_da_linha(l)}"


def rotulo_parada(p: dict) -> str:
    ed = (p.get("ed") or "").strip()
    return f"{p['np']} — {ed}" if ed else p["np"]


def abrir_linha(letreiro: str, sentido: int):
    """Callback: abre a aba Linhas já com a linha/sentido escolhidos."""
    st.session_state["q_linha"] = letreiro
    st.session_state["pref_sl"] = sentido
    st.session_state["aba"] = NAV[1]


def previsao_da_parada(cp) -> tuple[str | None, list]:
    dados = api_previsao_parada(cp)
    return dados.get("hr"), (dados.get("p") or {}).get("l") or []


def cards_de_chegadas(hora_ref, linhas_parada) -> list:
    """Mostra uma linha por ônibus que chega ao ponto; devolve posições para o foco do mapa."""
    if not linhas_parada or not hora_ref:
        st.info("Nenhum ônibus com previsão para este ponto agora.")
        return []
    ordenadas = sorted(
        linhas_parada,
        key=lambda l: min((minutos_ate(hora_ref, v["t"]) for v in l.get("vs") or []), default=9999),
    )
    foco = []
    for l in ordenadas:
        vs = sorted(l.get("vs") or [], key=lambda v: v["t"])
        mins = [minutos_ate(hora_ref, v["t"]) for v in vs]
        foco += [(v["py"], v["px"]) for v in vs[:1]]
        if mins:
            primeiro = texto_eta(mins[0])
            demais = " · ".join(f"{m} min" if m else "agora" for m in mins[1:3])
            sub = f'<div class="card-sub">Depois: <span class="times">{demais}</span></div>' if demais else ""
        else:
            primeiro = '<div class="eta-time"><span>sem previsão</span></div>'
            sub = ""
        card(
            f'<div class="card"><div class="row"><div>{badge(l["c"])}'
            f'<div class="card-sub" style="margin-top:6px">➜ {h(l.get("lt0"))}</div>{sub}</div>'
            f'{primeiro}</div></div>'
        )
    return foco


# ======================= ABA: PERTO DE MIM =======================
def pagina_perto():
    if not user_pos:
        codigo = st.session_state.get("gps_erro")
        if codigo is None:
            card('<div class="card"><div class="card-title">⏳ Aguardando sua localização</div>'
                 '<div class="card-sub">Seu navegador deve mostrar um aviso pedindo permissão. Toque em <b>Permitir</b>. '
                 'Se ele não aparecer, informe um endereço abaixo.</div></div>')
        else:
            card('<div class="card"><div class="card-title">📍 Não consegui pegar sua localização</div></div>')
            st.warning(MSG_GPS.get(codigo, MSG_GPS[2]))
        st.button("🔄 Tentar o GPS de novo", on_click=_novo_gps, key="btn_gps_perto")
        st.markdown("**Ou informe onde você está:**")
        form_endereco("perto")
        return

    G = gtfs_ou_none()
    if G is None:
        st.error("Não consegui carregar os dados de linhas e pontos (GTFS). Verifique a conexão ou coloque o "
                 f"arquivo .zip na pasta `gtfs/`. Detalhe: {st.session_state.get('gtfs_erro')}")
        return

    raio = st.select_slider("Raio de busca", options=[200, 300, 500, 800, 1000], value=500,
                            format_func=lambda m: f"{m} m", key="raio")
    proximas = gtfs_data.paradas_proximas(G, user_pos[0], user_pos[1], raio, limite=15)
    if not proximas:
        st.info("Nenhum ponto de ônibus nesse raio. Aumente o raio de busca.")
        return

    # Melhor ponto de cada linha/sentido (o mais perto de você)
    melhor = {}
    for p in proximas:
        for chave in p["linhas"]:
            melhor.setdefault(chave, p)
    total_linhas = len({c[0] for c in melhor})
    card(f'<span class="chip green">🚌 {total_linhas} linhas</span><span class="chip">🚏 {len(proximas)} pontos até {raio} m</span>')

    # Previsões reais dos pontos mais próximos
    etas = {}
    try:
        for p in proximas[:4]:
            hr, ls = previsao_da_parada(p["cp"])
            for l in ls:
                vs = sorted(l.get("vs") or [], key=lambda v: v["t"])
                if hr and vs:
                    etas[(p["cp"], l["c"], l["sl"])] = [minutos_ate(hr, v["t"]) for v in vs]
    except SPTransError:
        pass  # sem previsão: mostramos só distâncias

    # ---- Mapa dos pontos ----
    mapa = mapa_base(user_pos)
    folium.Circle(user_pos, radius=raio, color=COR_MARCA, weight=1, fill=True, fill_opacity=0.05, dash_array="6").add_to(mapa)
    for i, p in enumerate(proximas):
        folium.CircleMarker(
            (p["lat"], p["lon"]), radius=8 if i == 0 else 6, color="#fff", weight=2, fill=True,
            fill_color=COR_MARCA, fill_opacity=1,
            tooltip=f"{p['nome']} • {dist_txt(p['dist_m'])} • {', '.join(sorted({c[0] for c in p['linhas']})[:6])}",
        ).add_to(mapa)
    folium.Marker(user_pos, icon=icone_usuario(), tooltip="Você está aqui").add_to(mapa)
    desenhar_mapa(mapa, [user_pos] + [(p["lat"], p["lon"]) for p in proximas], key="mapa_perto")

    # ---- Linhas perto de você ----
    st.markdown('<div class="sec">Linhas perto de você</div>', unsafe_allow_html=True)
    ordenadas = sorted(melhor.items(), key=lambda kv: (kv[1]["dist_m"], kv[0]))
    for (rota, direcao), p in ordenadas[:10]:
        sl = 2 - direcao
        mins = etas.get((p["cp"], rota, sl))
        eta_html = texto_eta(mins[0]) if mins else '<div class="eta-time"><span>ver trajeto</span></div>'
        col_a, col_b = st.columns([5, 1], vertical_alignment="center")
        with col_a:
            card(
                f'<div class="card compact"><div class="row"><div>{badge(rota)}'
                f'<span class="card-sub">➜ {h(G["destino"].get((rota, direcao)))}</span>'
                f'<div class="card-sub" style="margin-top:4px">🚏 {h(p["nome"])} · 🚶 {dist_txt(p["dist_m"])}</div></div>'
                f'{eta_html}</div></div>'
            )
        with col_b:
            st.button("🗺️", key=f"ver_{rota}_{direcao}", on_click=abrir_linha, args=(rota, sl),
                      help="Ver trajeto e ônibus desta linha")
    if len(ordenadas) > 10:
        with st.expander(f"Mais {len(ordenadas) - 10} linhas"):
            for (rota, direcao), p in ordenadas[10:50]:
                st.button(f"{rota} ➜ {G['destino'].get((rota, direcao))} · {dist_txt(p['dist_m'])}",
                          key=f"ver_{rota}_{direcao}", on_click=abrir_linha, args=(rota, 2 - direcao))

    # ---- Chegadas em um ponto ----
    st.markdown('<div class="sec">Chegadas em um ponto</div>', unsafe_allow_html=True)
    ponto = st.selectbox(
        "Ponto", proximas, key="ponto_perto", label_visibility="collapsed",
        format_func=lambda p: f"{p['nome']} · {dist_txt(p['dist_m'])}" + (f" — {p['desc']}" if p["desc"] else ""),
    )
    try:
        hr, ls = previsao_da_parada(ponto["cp"])
        card(f'<div class="card"><div class="card-title">🚏 {h(ponto["nome"])}</div>'
             f'<div class="card-sub">{h(ponto["desc"])}</div><div style="margin-top:8px">{chip_caminhada(ponto["dist_m"])}</div></div>')
        cards_de_chegadas(hr, ls)
    except SPTransError as e:
        st.error(f"⚠️ {e}")
    st.caption(f"Pontos e linhas: GTFS da SPTrans ({G['origem']}). Tempos de chegada: Olho Vivo, ao vivo.")


# ======================= ABA: LINHAS =======================
def pagina_linhas():
    termo_linha = st.text_input(
        "Linha", placeholder="🔍 Número ou nome da linha (ex: 5300, 8000, Lapa)", label_visibility="collapsed", key="q_linha"
    ).strip()

    if not termo_linha:
        card('<div class="card"><div class="card-title">Qual ônibus você quer acompanhar?</div>'
             '<div class="card-sub">Digite o número da linha para ver o trajeto, os pontos e quando o próximo passa perto de você.</div></div>')
        return

    try:
        linhas = api_buscar_linhas(termo_linha)
        if not linhas:
            st.info("Nenhuma linha encontrada. Tente outro número ou nome.")
            return

        pref = st.session_state.get("pref_sl")
        idx = 0
        for i, l in enumerate(linhas):
            if f"{l['lt']}-{l['tl']}" == termo_linha and l["sl"] == pref:
                idx = i
                break
        linha = st.selectbox("Sentido", linhas, index=idx, format_func=rotulo_linha,
                             key=f"sel_linha_{termo_linha}_{pref}", label_visibility="collapsed")
        cl = linha["cl"]
        letreiro = f"{linha['lt']}-{linha['tl']}"
        cor = cor_da_linha(letreiro)
        destino = destino_da_linha(linha)

        paradas = api_paradas_da_linha(cl)
        posicao = api_posicao_linha(cl)
        previsao = api_previsao_linha(cl)
        onibus = posicao.get("vs") or []
        hora_ref = previsao.get("hr") or posicao.get("hr")

        trajeto = None
        G = gtfs_ou_none()
        if G:
            trajeto = gtfs_data.trajeto_da_linha(G, letreiro, linha["sl"], destino)

        card(
            f'<div class="card"><div class="row"><div>{badge(letreiro)}'
            f'<span class="card-title">Sentido {h(destino)}</span>'
            f'<div class="card-sub" style="margin-top:6px">Origem: {h(linha["tp"] if linha["sl"] == 1 else linha["ts"])}</div></div>'
            f'<div><span class="chip green">{len(onibus)} em operação</span></div></div></div>'
        )
        if not onibus:
            st.warning("Nenhum ônibus desta linha está transmitindo GPS agora.")

        # --- Ponto de embarque (padrão: o mais próximo de você) ---
        ponto = None
        if paradas:
            idx_padrao = 0
            if user_pos:
                idx_padrao = min(
                    range(len(paradas)),
                    key=lambda i: distancia_km(user_pos[0], user_pos[1], paradas[i]["py"], paradas[i]["px"]),
                )
            ponto = st.selectbox(
                "Ponto de embarque", paradas, index=idx_padrao, format_func=rotulo_parada,
                key=f"ponto_{cl}_{'loc' if user_pos else 'noloc'}",
                help="Por padrão mostramos o ponto mais próximo de você." if user_pos else None,
            )

        chegadas = []
        if ponto:
            for p in previsao.get("ps") or []:
                if p["cp"] == ponto["cp"]:
                    chegadas = sorted(p.get("vs") or [], key=lambda v: v["t"])
                    break
            caminhada = ""
            if user_pos:
                caminhada = chip_caminhada(distancia_km(user_pos[0], user_pos[1], ponto["py"], ponto["px"]) * 1000)
            if chegadas and hora_ref:
                linhas_html = "".join(
                    linha_eta(v["p"], minutos_ate(hora_ref, v["t"]), v.get("a", False)) for v in chegadas[:4]
                )
            else:
                linhas_html = '<div class="muted" style="padding:8px 0">Sem previsão de chegada para este ponto agora.</div>'
            card(
                f'<div class="card"><div class="card-title">🚏 {h(ponto["np"])}</div>'
                f'<div class="card-sub">{h(ponto.get("ed") or "")}</div>'
                f'<div style="margin:8px 0 4px">{caminhada}</div>{linhas_html}</div>'
            )

        # --- Mapa ---
        if paradas or onibus or trajeto:
            enquadrar = st.segmented_control(
                "Enquadrar", ["🗺️ Linha toda", "🚏 Meu ponto"], default="🗺️ Linha toda",
                key="enquadrar", label_visibility="collapsed",
            ) or "🗺️ Linha toda"
            centro = (ponto["py"], ponto["px"]) if ponto else (onibus[0]["py"], onibus[0]["px"]) if onibus else trajeto[0]
            mapa = mapa_base(centro)

            if trajeto:
                desenhar_trajeto(mapa, trajeto, cor)
            elif len(paradas) > 1:  # sem GTFS: liga os pontos em ordem
                desenhar_trajeto(mapa, [(p["py"], p["px"]) for p in paradas], cor)

            for i, p in enumerate(paradas):
                if ponto and p["cp"] == ponto["cp"]:
                    continue
                ponta = i in (0, len(paradas) - 1)
                folium.CircleMarker(
                    (p["py"], p["px"]), radius=7 if ponta else 4,
                    color="#1B2437" if ponta else cor, weight=2, fill=True,
                    fill_color="#10A66A" if i == 0 and ponta else "#E5484D" if ponta else "#fff", fill_opacity=1,
                    tooltip=("Início • " if i == 0 else "Fim • " if ponta else "") + p["np"],
                ).add_to(mapa)

            foco_ponto = []
            if ponto:
                folium.Marker((ponto["py"], ponto["px"]), icon=icone_parada(), tooltip=ponto["np"]).add_to(mapa)
                foco_ponto.append((ponto["py"], ponto["px"]))
            proximos = {v["p"] for v in chegadas[:2]}
            for v in onibus:
                folium.Marker(
                    (v["py"], v["px"]), icon=icone_onibus(cor),
                    tooltip=f"Ônibus {v['p']} • atualizado {hora_local(v.get('ta'))}" + (" • ♿" if v.get("a") else ""),
                ).add_to(mapa)
                if v["p"] in proximos:
                    foco_ponto.append((v["py"], v["px"]))
            if user_pos:
                folium.Marker(user_pos, icon=icone_usuario(), tooltip="Você está aqui").add_to(mapa)
                foco_ponto.append(user_pos)
                if ponto:
                    folium.PolyLine([user_pos, (ponto["py"], ponto["px"])], color="#1E6EFF", weight=3, dash_array="4 8").add_to(mapa)

            if enquadrar == "🗺️ Linha toda":
                foco = list(trajeto) if trajeto else [(p["py"], p["px"]) for p in paradas] or foco_ponto
            else:
                foco = foco_ponto
            desenhar_mapa(mapa, foco, key=f"mapa_linha_{cl}_{enquadrar}")
            st.caption("🟢 início · 🔴 fim · ► sentido da viagem · atualização automática a cada 30 segundos."
                       + ("" if trajeto else " (Trajeto exato indisponível: ligando os pontos.)"))
    except SPTransError as e:
        st.error(f"⚠️ {e}")


# ======================= ABA: PARADAS =======================
def pagina_paradas():
    termo_parada = st.text_input(
        "Parada", placeholder="🔍 Nome ou endereço do ponto (ex: Av Paulista, Terminal Lapa)",
        label_visibility="collapsed", key="q_parada",
    ).strip()

    if not termo_parada:
        card('<div class="card"><div class="card-title">Veja todos os ônibus que passam no seu ponto</div>'
             '<div class="card-sub">Busque pelo nome da rua, terminal ou ponto de referência.</div></div>')
        return

    try:
        achadas = api_buscar_paradas(termo_parada)
        if not achadas:
            st.info("Nenhuma parada encontrada. Tente outro nome ou endereço.")
            return
        if user_pos:
            achadas = sorted(achadas, key=lambda p: distancia_km(user_pos[0], user_pos[1], p["py"], p["px"]))
        parada = st.selectbox("Parada", achadas[:50], format_func=rotulo_parada, key="sel_parada",
                              label_visibility="collapsed")
        hora_ref, linhas_parada = previsao_da_parada(parada["cp"])

        cabecalho = (
            f'<div class="card"><div class="card-title">🚏 {h(parada["np"])}</div>'
            f'<div class="card-sub">{h(parada.get("ed") or "")}</div>'
        )
        if user_pos:
            cabecalho += f'<div style="margin-top:8px">{chip_caminhada(distancia_km(user_pos[0], user_pos[1], parada["py"], parada["px"]) * 1000)}</div>'
        card(cabecalho + "</div>")

        proximos_foco = cards_de_chegadas(hora_ref, linhas_parada)

        mapa = mapa_base((parada["py"], parada["px"]))
        folium.Marker((parada["py"], parada["px"]), icon=icone_parada(), tooltip=parada["np"]).add_to(mapa)
        foco = [(parada["py"], parada["px"])] + proximos_foco[:5]
        for l in linhas_parada:
            for v in (l.get("vs") or [])[:1]:
                folium.Marker(
                    (v["py"], v["px"]), icon=icone_onibus(cor_da_linha(l["c"])),
                    tooltip=f"{l['c']} • ônibus {v['p']}",
                ).add_to(mapa)
        if user_pos:
            folium.Marker(user_pos, icon=icone_usuario(), tooltip="Você está aqui").add_to(mapa)
            foco.append(user_pos)
        desenhar_mapa(mapa, foco, key=f"mapa_parada_{parada['cp']}")
    except SPTransError as e:
        st.error(f"⚠️ {e}")


{NAV[0]: pagina_perto, NAV[1]: pagina_linhas, NAV[2]: pagina_paradas}[aba]()