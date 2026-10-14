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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --brand: #F26B21;
    --brand-dark: #D9530F;
    --brand-light: #FFF4ED;
    --bg-app: #F8FAFC;
    --surface: #FFFFFF;
    --text-main: #0F172A;
    --text-sub: #475569;
    --text-muted: #94A3B8;
    --border: #E2E8F0;
    --success: #059669;
    --success-bg: #ECFDF5;
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

header[data-testid="stHeader"], #MainMenu, footer {display:none !important;}

.block-container {
    max-width: 540px;
    padding: 1.25rem 1rem 5rem;
}

.stApp {
    background: var(--bg-app);
}

/* Hero Header Moderno */
.hero {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
    color: #fff;
    border-radius: 24px;
    padding: 22px 24px;
    margin-bottom: 14px;
    box-shadow: 0 12px 28px -6px rgba(15, 23, 42, 0.25);
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
.hero::after {
    content: "";
    position: absolute;
    top: -50%;
    right: -15%;
    width: 240px;
    height: 240px;
    background: radial-gradient(circle, rgba(242,107,33,0.32) 0%, rgba(242,107,33,0) 70%);
    border-radius: 50%;
    pointer-events: none;
}
.hero-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}
.hero-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}
.hero-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    background: linear-gradient(135deg, #F26B21 0%, #FF8C42 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(242, 107, 33, 0.4);
    flex-shrink: 0;
}
.hero h1 {
    font-size: 1.35rem;
    margin: 0;
    padding: 0;
    color: #fff;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.2;
}
.hero p {
    margin: 3px 0 0;
    color: #94A3B8;
    font-size: 0.82rem;
    font-weight: 500;
}
.live-pill {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34D399;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* Inputs, Selects e Botões Nativos */
div[data-baseweb="input"], div[data-baseweb="select"] > div {
    border-radius: 14px !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
    transition: all 0.2s ease !important;
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {
    border-color: var(--brand) !important;
    box-shadow: 0 0 0 3px rgba(242, 107, 33, 0.15) !important;
}
.stButton > button, .stPopover > div > button {
    border-radius: 12px !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    color: var(--text-main) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.45rem 0.85rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
    transition: all 0.18s ease !important;
}
.stButton > button:hover, .stPopover > div > button:hover {
    border-color: #CBD5E1 !important;
    background: #F1F5F9 !important;
    transform: translateY(-1px);
}

/* Segmented Control mais elegante */
div[data-testid="stSegmentedControl"] {
    background: #E2E8F0 !important;
    padding: 4px !important;
    border-radius: 14px !important;
    margin-bottom: 8px !important;
}

/* Cards */
.card {
    background: var(--surface);
    border-radius: 18px;
    padding: 16px 18px;
    margin: 10px 0;
    border: 1px solid var(--border);
    box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.04);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.card.interactive:hover {
    border-color: #CBD5E1;
    box-shadow: 0 8px 20px -4px rgba(15, 23, 42, 0.08);
}
.card.compact {
    padding: 12px 15px;
    margin: 6px 0;
    border-radius: 16px;
}
.card-title {
    font-weight: 700;
    color: var(--text-main);
    font-size: 0.98rem;
    letter-spacing: -0.01em;
}
.card-sub {
    color: var(--text-sub);
    font-size: 0.8rem;
    margin-top: 3px;
    font-weight: 500;
}

/* Empty State Card */
.empty-state {
    background: var(--surface);
    border: 1px dashed #CBD5E1;
    border-radius: 20px;
    padding: 28px 20px;
    text-align: center;
    margin: 14px 0;
}
.empty-icon {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: var(--brand-light);
    color: var(--brand);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 1.4rem;
    margin-bottom: 10px;
}

/* Badges de Linha */
.badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-weight: 800;
    border-radius: 9px;
    padding: 4px 10px;
    font-size: 0.88rem;
    letter-spacing: 0.02em;
    margin-right: 8px;
    box-shadow: inset 0 -1px 0 rgba(0,0,0,0.18), 0 2px 4px rgba(0,0,0,0.08);
}
.badge.mini {
    padding: 2px 7px;
    font-size: 0.72rem;
    margin: 2px 4px 2px 0;
    border-radius: 7px;
}

/* Layout e Linhas de Previsão (ETA) */
.row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}
.eta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 0;
    border-top: 1px solid #F1F5F9;
}
.eta-row:first-of-type {
    border-top: none;
    padding-top: 6px;
}
.eta-row:last-of-type {
    padding-bottom: 2px;
}
.eta-box {
    text-align: right;
    min-width: 78px;
    background: #F8FAFC;
    padding: 6px 12px;
    border-radius: 12px;
    border: 1px solid var(--border);
}
.eta-box.soon {
    background: var(--success-bg);
    border-color: #A7F3D0;
}
.eta-time {
    font-weight: 800;
    font-size: 1.35rem;
    color: var(--text-main);
    line-height: 1.05;
    font-variant-numeric: tabular-nums;
}
.eta-time span {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text-sub);
    margin-left: 2px;
}
.eta-time.soon {
    color: var(--success);
}
.eta-time.soon span {
    color: var(--success);
}

/* Chips e Tags */
.chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: var(--brand-light);
    color: var(--brand-dark);
    border: 1px solid #FFEDD5;
    border-radius: 999px;
    padding: 4px 11px;
    font-size: 0.74rem;
    font-weight: 700;
    margin-right: 6px;
}
.chip.green {
    background: var(--success-bg);
    color: var(--success);
    border-color: #A7F3D0;
}
.chip.gray {
    background: #F1F5F9;
    color: var(--text-sub);
    border-color: var(--border);
}

/* Indicador Ao Vivo Pulsante */
.live {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #10B981;
    margin-right: 6px;
    animation: pulse 1.8s infinite;
}
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
    70% { box-shadow: 0 0 0 7px rgba(16, 185, 129, 0); }
    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.times { font-weight: 700; color: var(--text-main); }
.muted { color: var(--text-muted); font-size: 0.82rem; font-weight: 500; }
.sec {
    font-weight: 800;
    color: var(--text-main);
    margin: 20px 0 6px;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* Container do Mapa Folium Arredondado */
iframe[title="streamlit_folium.st_folium"] {
    border-radius: 20px !important;
    border: 1px solid var(--border) !important;
    box-shadow: 0 6px 18px -4px rgba(15, 23, 42, 0.07) !important;
}
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
    r, g, b = colorsys.hls_to_rgb(hue, 0.36, 0.68)
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


def badge(letreiro: str, mini: bool = False) -> str:
    classe = "badge mini" if mini else "badge"
    return f'<span class="{classe}" style="background:{cor_da_linha(letreiro)}">{h(letreiro)}</span>'


def texto_eta(minutos: int) -> str:
    if minutos <= 0:
        return '<div class="eta-box soon"><div class="eta-time soon">Agora</div></div>'
    soon_cls = "soon" if minutos <= 3 else ""
    return f'<div class="eta-box {soon_cls}"><div class="eta-time {soon_cls}">{minutos}<span>min</span></div></div>'


def linha_eta(prefixo: str, minutos: int, acessivel: bool) -> str:
    extra = " · ♿ Acessível" if acessivel else ""
    return (
        f'<div class="eta-row"><div><div class="card-title">Prefixo {h(prefixo)}</div>'
        f'<div class="card-sub"><span class="live"></span>GPS em tempo real{extra}</div></div>{texto_eta(minutos)}</div>'
    )


def dist_txt(metros: float) -> str:
    return f"{metros:.0f} m" if metros < 1000 else f"{metros / 1000:.1f} km"


def chip_caminhada(metros: float) -> str:
    return f'<span class="chip">🚶 {max(1, round(metros / 80))} min · {dist_txt(metros)}</span>'


def mapa_base(centro) -> folium.Map:
    m = folium.Map(location=centro, zoom_start=15, tiles="OpenStreetMap", zoom_control=True)
    # Suaviza as cores do OpenStreetMap para destacar os ônibus e trajetos, sem precisar de API Key!
    m.get_root().header.add_child(
        folium.Element(
            "<style>.leaflet-tile-pane { filter: saturate(0.55) contrast(1.03) brightness(1.03); }</style>"
        )
    )
    return m


def icone_onibus(cor: str) -> folium.DivIcon:
    svg_bus = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
        'fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M8 6v6"/><path d="M15 6v6"/><path d="M2 12h19.6"/>'
        '<path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3"/>'
        '<circle cx="7" cy="18" r="2"/><path d="M9 18h5"/><circle cx="16" cy="18" r="2"/></svg>'
    )
    return folium.DivIcon(
        icon_size=(34, 34),
        icon_anchor=(17, 17),
        html=(
            f'<div style="background:{cor};border:2.5px solid #fff;border-radius:50%;width:34px;height:34px;'
            'display:flex;align-items:center;justify-content:center;'
            'box-shadow:0 4px 10px rgba(15,23,42,.35)">'
            f'{svg_bus}</div>'
        ),
    )


def icone_parada() -> folium.DivIcon:
    svg_stop = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" '
        'fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect width="16" height="16" x="4" y="3" rx="2"/><path d="M4 11h16"/>'
        '<path d="M12 3v8"/><path d="m8 19-2 3"/><path d="m18 22-2-3"/><path d="M8 15h0"/><path d="M16 15h0"/></svg>'
    )
    return folium.DivIcon(
        icon_size=(36, 36),
        icon_anchor=(18, 36),
        html=(
            f'<div style="background:{COR_MARCA};border:2.5px solid #fff;border-radius:50% 50% 50% 0;'
            'transform:rotate(-45deg);width:36px;height:36px;box-shadow:0 4px 10px rgba(15,23,42,.35);'
            'display:flex;align-items:center;justify-content:center">'
            f'<span style="transform:rotate(45deg);display:flex">{svg_stop}</span></div>'
        ),
    )


def icone_usuario() -> folium.DivIcon:
    return folium.DivIcon(
        icon_size=(24, 24),
        icon_anchor=(12, 12),
        html=(
            '<style>@keyframes p{0%{box-shadow:0 0 0 0 rgba(37,99,235,.55)}'
            '70%{box-shadow:0 0 0 16px rgba(37,99,235,0)}100%{box-shadow:0 0 0 0 rgba(37,99,235,0)}}</style>'
            '<div style="width:18px;height:18px;border-radius:50%;background:#2563EB;border:3px solid #fff;'
            'box-shadow:0 2px 6px rgba(0,0,0,.3);animation:p 2s infinite"></div>'
        ),
    )


def desenhar_mapa(mapa: folium.Map, pontos_foco: list, key: str) -> None:
    if len(pontos_foco) > 1:
        mapa.fit_bounds(pontos_foco, padding=(40, 40), max_zoom=16)
    st_folium(mapa, height=400, use_container_width=True, returned_objects=[], key=key)


def desenhar_trajeto(mapa: folium.Map, pontos: list, cor: str) -> None:
    """Trajeto da linha: contorno branco + cor da linha + setas de sentido."""
    folium.PolyLine(pontos, color="#FFFFFF", weight=9, opacity=0.95).add_to(mapa)
    linha = folium.PolyLine(pontos, color=cor, weight=5, opacity=0.95).add_to(mapa)
    PolyLineTextPath(
        linha, "      ►      ", repeat=True, offset=6, attributes={"fill": "#FFFFFF", "font-size": "12", "font-weight": "bold"}
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


@st.cache_resource(show_spinner="Preparando base de linhas e paradas (só na 1ª vez, ~10 s)...")
def carregar_gtfs() -> dict:
    return gtfs_data.carregar()


def gtfs_ou_none():
    try:
        return carregar_gtfs()
    except Exception as e:
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
st.session_state.setdefault("lembrar", True)
st.session_state.setdefault("gps_n", 0)


def _novo_gps():
    st.session_state["gps_n"] += 1
    st.session_state.pop("pos_manual", None)
    st.session_state.pop("gps_erro", None)


JS_GPS = (
    "(function(){return new Promise(function(resolve){"
    "if(!navigator.geolocation){resolve({error:{code:0,message:'sem suporte'}});return;}"
    "if(window.isSecureContext===false){resolve({error:{code:99,message:'contexto inseguro'}});return;}"
    "navigator.geolocation.getCurrentPosition("
    "function(p){resolve({coords:{latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy}});},"
    "function(e){resolve({error:{code:e.code,message:e.message}});},"
    "{enableHighAccuracy:true,timeout:20000,maximumAge:15000});"
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
    if c1.button("Usar endereço", key=f"btn_end_{chave}", use_container_width=True) and end_txt.strip():
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
    if c2.button("Limpar", key=f"btn_limpar_{chave}", use_container_width=True):
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
        st.session_state["gps_acc"] = coords.get("accuracy")
        st.session_state.pop("gps_erro", None)
    elif res_gps.get("error"):
        st.session_state["gps_erro"] = res_gps["error"].get("code", 2)

# ======================= CABEÇALHO =======================
card(
    '<div class="hero">'
    '<div class="hero-top">'
    '<div class="hero-brand">'
    '<div class="hero-icon">'
    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6v6"/><path d="M15 6v6"/><path d="M2 12h19.6"/><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3"/><circle cx="7" cy="18" r="2"/><path d="M9 18h5"/><circle cx="16" cy="18" r="2"/></svg>'
    '</div>'
    '<div><h1>Olho Vivo SP</h1><p>Monitoramento urbano em tempo real</p></div>'
    '</div>'
    '<div class="live-pill"><span class="live" style="margin-right:2px"></span>Ao vivo</div>'
    '</div>'
    '</div>'
)

col_status, col_cfg = st.columns([3.2, 1.8], vertical_alignment="center")
with col_cfg:
    with st.popover("⚙️ Localização", use_container_width=True):
        st.button("🔄 Atualizar pelo GPS", on_click=_novo_gps, key="btn_gps", use_container_width=True)
        st.toggle(
            "Lembrar localização neste aparelho", key="lembrar",
            help="Ligado: a última posição fica salva e aparece na hora ao abrir o app. "
                 "Desligado: nada é salvo e o app pede o GPS toda vez.",
        )
        st.markdown("**Ou informe um endereço**")
        form_endereco("popover")

if "pos_manual" in st.session_state:
    user_pos, origem_pos = st.session_state["pos_manual"], "Endereço fixado"
elif "pos_gps" in st.session_state:
    user_pos, origem_pos = st.session_state["pos_gps"], "GPS ativo"
elif "pos_salva" in st.session_state:
    user_pos, origem_pos = st.session_state["pos_salva"], "Posição salva"
else:
    user_pos, origem_pos = None, None

# 3) salva (ou apaga) no aparelho
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
        classe = "green" if origem_pos != "Posição salva" else "gray"
        acc = st.session_state.get("gps_acc")
        acc_txt = f" (±{acc:.0f}m)" if acc and origem_pos == "GPS ativo" else ""
        st.markdown(f'<span class="chip {classe}">📍 {origem_pos}{acc_txt}</span>', unsafe_allow_html=True)
    elif st.session_state.get("gps_erro") is not None:
        st.markdown('<span class="chip">📍 Sem localização</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="muted">⏳ Obtendo localização...</span>', unsafe_allow_html=True)

if origem_pos == "Posição salva":
    st.caption("Usando última posição conhecida. Se você se deslocou, acesse ⚙️ Localização → Atualizar.")

# ======================= NAVEGAÇÃO =======================
st.session_state.setdefault("aba", NAV[0])
escolha = st.segmented_control("Navegação", NAV, key="aba", label_visibility="collapsed")
aba = escolha or st.session_state.get("_aba_anterior", NAV[0])
st.session_state["_aba_anterior"] = aba


# ======================= FUNÇÕES COMPARTILHADAS =======================
def destino_da_linha(l: dict) -> str:
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
        st.info("Nenhum ônibus com previsão para este ponto no momento.")
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
            sub = f'<div class="card-sub">Seguintes: <span class="times">{demais}</span></div>' if demais else ""
        else:
            primeiro = '<div class="eta-box"><div class="eta-time"><span>s/ prev.</span></div></div>'
            sub = ""
        card(
            f'<div class="card interactive"><div class="row"><div>{badge(l["c"])}'
            f'<div class="card-sub" style="margin-top:6px">➜ {h(l.get("lt0"))}</div>{sub}</div>'
            f'{primeiro}</div></div>'
        )
    return foco


# ======================= ABA: PERTO DE MIM =======================
def pagina_perto():
    if not user_pos:
        codigo = st.session_state.get("gps_erro")
        if codigo is None:
            card(
                '<div class="empty-state">'
                '<div class="empty-icon">📍</div>'
                '<div class="card-title">Aguardando sua localização</div>'
                '<div class="card-sub" style="max-width:360px;margin:6px auto 0">'
                'Permita o acesso ao GPS no aviso do navegador ou informe um endereço manualmente abaixo.</div>'
                '</div>'
            )
        else:
            card(
                '<div class="empty-state">'
                '<div class="empty-icon">⚠️</div>'
                '<div class="card-title">Localização indisponível</div>'
                '</div>'
            )
            st.warning(MSG_GPS.get(codigo, MSG_GPS[2]))
        st.button("🔄 Tentar capturar GPS novamente", on_click=_novo_gps, key="btn_gps_perto", use_container_width=True)
        st.markdown('<div class="sec">Ou informe onde você está</div>', unsafe_allow_html=True)
        form_endereco("perto")
        return

    G = gtfs_ou_none()
    if G is None:
        st.error("Não consegui carregar os dados de linhas e pontos (GTFS). Verifique a conexão ou coloque o "
                 f"arquivo .zip na pasta `gtfs/`. Detalhe: {st.session_state.get('gtfs_erro')}")
        return

    raio = st.select_slider("Raio de busca", options=[200, 300, 500, 800, 1000], value=500,
                            format_func=lambda m: f"{m} m", key="raio")
    proximas = gtfs_data.paradas_proximas(G, user_pos[0], user_pos[1], raio, limite=25)
    if not proximas:
        st.info("Nenhum ponto de ônibus encontrado nesse raio. Aumente a distância acima.")
        return

    # Garante que os pontos estão rigorosamente do mais perto para o mais longe
    proximas.sort(key=lambda p: p["dist_m"])

    melhor = {}
    for p in proximas:
        for chave in p["linhas"]:
            melhor.setdefault(chave, p)
    total_linhas = len({c[0] for c in melhor})
    card(
        f'<div style="margin: 4px 0 10px">'
        f'<span class="chip green">🚌 {total_linhas} linhas na área</span>'
        f'<span class="chip gray">🚏 {len(proximas)} paradas até {raio} m</span>'
        f'</div>'
    )

    etas = {}
    try:
        for p in proximas[:4]:
            hr, ls = previsao_da_parada(p["cp"])
            for l in ls:
                vs = sorted(l.get("vs") or [], key=lambda v: v["t"])
                if hr and vs:
                    etas[(p["cp"], l["c"], l["sl"])] = [minutos_ate(hr, v["t"]) for v in vs]
    except SPTransError:
        pass

    # ---- Mapa dos pontos ----
    mapa = mapa_base(user_pos)
    folium.Circle(user_pos, radius=raio, color=COR_MARCA, weight=1.5, fill=True, fill_opacity=0.06, dash_array="6").add_to(mapa)
    for i, p in enumerate(proximas):
        folium.CircleMarker(
            (p["lat"], p["lon"]), radius=8 if i == 0 else 6, color="#fff", weight=2, fill=True,
            fill_color=COR_MARCA, fill_opacity=1,
            tooltip=f"{p['nome']} • {dist_txt(p['dist_m'])} • {', '.join(sorted({c[0] for c in p['linhas']})[:6])}",
        ).add_to(mapa)
    folium.Marker(user_pos, icon=icone_usuario(), tooltip="Você está aqui").add_to(mapa)
    desenhar_mapa(mapa, [user_pos] + [(p["lat"], p["lon"]) for p in proximas], key="mapa_perto")

    # ---- Linhas perto de você ----
    st.markdown('<div class="sec">🚌 Linhas próximas</div>', unsafe_allow_html=True)
    ordenadas = sorted(melhor.items(), key=lambda kv: (kv[1]["dist_m"], kv[0]))
    for (rota, direcao), p in ordenadas[:10]:
        sl = 2 - direcao
        mins = etas.get((p["cp"], rota, sl))
        eta_html = texto_eta(mins[0]) if mins else '<div class="eta-box"><div class="eta-time"><span>trajeto</span></div></div>'
        col_a, col_b = st.columns([5.2, 1], vertical_alignment="center")
        with col_a:
            card(
                f'<div class="card compact interactive"><div class="row"><div>{badge(rota)}'
                f'<span class="card-title" style="font-size:0.9rem">➜ {h(G["destino"].get((rota, direcao)))}</span>'
                f'<div class="card-sub" style="margin-top:4px">🚏 {h(p["nome"])} · 🚶 {dist_txt(p["dist_m"])}</div></div>'
                f'{eta_html}</div></div>'
            )
        with col_b:
            st.button("🗺️", key=f"ver_{rota}_{direcao}", on_click=abrir_linha, args=(rota, sl),
                      help="Ver trajeto e frota desta linha", use_container_width=True)
    if len(ordenadas) > 10:
        with st.expander(f"Ver mais {len(ordenadas) - 10} linhas na região"):
            for (rota, direcao), p in ordenadas[10:50]:
                st.button(f"{rota} ➜ {G['destino'].get((rota, direcao))} · {dist_txt(p['dist_m'])}",
                          key=f"ver_{rota}_{direcao}", on_click=abrir_linha, args=(rota, 2 - direcao),
                          use_container_width=True)

    # ---- Chegadas em um ponto ----
    st.markdown('<div class="sec">🚏 Chegadas por parada</div>', unsafe_allow_html=True)
    ponto = st.selectbox(
        "Ponto", proximas, key="ponto_perto", label_visibility="collapsed",
        format_func=lambda p: f"{p['nome']} · {dist_txt(p['dist_m'])}" + (f" — {p['desc']}" if p["desc"] else ""),
    )
    try:
        hr, ls = previsao_da_parada(ponto["cp"])
        card(f'<div class="card"><div class="card-title">🚏 {h(ponto["nome"])}</div>'
             f'<div class="card-sub">{h(ponto["desc"])}</div><div style="margin-top:10px">{chip_caminhada(ponto["dist_m"])}</div></div>')
        cards_de_chegadas(hr, ls)
    except SPTransError as e:
        st.error(f"⚠️ {e}")
    st.caption(f"Malha viária: GTFS SPTrans ({G['origem']}) • Telemetria: API Olho Vivo.")

# ======================= ABA: LINHAS =======================
def pagina_linhas():
    termo_linha = st.text_input(
        "Linha", placeholder="🔍 Digite o número ou nome da linha (ex: 8000, 5300, Lapa)",
        label_visibility="collapsed", key="q_linha"
    ).strip()

    if not termo_linha:
        card(
            '<div class="empty-state">'
            '<div class="empty-icon">🚌</div>'
            '<div class="card-title">Consulte qualquer linha de São Paulo</div>'
            '<div class="card-sub" style="max-width:340px;margin:6px auto 0">'
            'Veja o itinerário completo no mapa, os ônibus em circulação e a previsão no ponto mais próximo.</div>'
            '</div>'
        )
        return

    try:
        linhas = api_buscar_linhas(termo_linha)
        if not linhas:
            st.info("Nenhuma linha encontrada. Tente outro número ou denominação.")
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
        direcao_gtfs = 2 - linha["sl"]  # sl=1 -> dir=1 | sl=2 -> dir=0

        paradas_api = api_paradas_da_linha(cl)
        posicao = api_posicao_linha(cl)
        previsao = api_previsao_linha(cl)
        onibus = posicao.get("vs") or []
        hora_ref = previsao.get("hr") or posicao.get("hr")

        trajeto = None
        G = gtfs_ou_none()
        if G:
            trajeto = gtfs_data.trajeto_da_linha(G, letreiro, linha["sl"], destino)

        # --- Une as paradas da API com TODAS as paradas de rua do GTFS desta linha ---
        mapa_paradas = {p["cp"]: p for p in (paradas_api or [])}
        if G:
            # Procura em possíveis estruturas do dicionário G onde ficam as paradas
            colecoes_stops = []
            for k, val in G.items():
                if isinstance(val, list) and val and isinstance(val[0], dict) and "cp" in val[0] and "linhas" in val[0]:
                    colecoes_stops.append(val)
                elif isinstance(val, dict):
                    amostra = next(iter(val.values()), None)
                    if isinstance(amostra, dict) and "cp" in amostra and "linhas" in amostra:
                        colecoes_stops.append(val.values())

            for lista_s in colecoes_stops:
                for s in lista_s:
                    linhas_s = s.get("linhas") or []
                    if (letreiro, direcao_gtfs) in linhas_s or any(x[0] == letreiro for x in linhas_s):
                        cp_s = s["cp"]
                        if cp_s not in mapa_paradas:
                            mapa_paradas[cp_s] = {
                                "cp": cp_s,
                                "np": s.get("nome") or s.get("np") or f"Parada {cp_s}",
                                "ed": s.get("desc") or s.get("ed") or "",
                                "py": s.get("lat") or s.get("py"),
                                "px": s.get("lon") or s.get("px"),
                            }

            # Garantia extra: inclui paradas próximas a até 2km de você que atendam esta linha
            if user_pos:
                for p_prox in gtfs_data.paradas_proximas(G, user_pos[0], user_pos[1], 2000, limite=80):
                    linhas_p = p_prox.get("linhas") or []
                    if (letreiro, direcao_gtfs) in linhas_p or any(x[0] == letreiro for x in linhas_p):
                        cp_s = p_prox["cp"]
                        if cp_s not in mapa_paradas:
                            mapa_paradas[cp_s] = {
                                "cp": cp_s,
                                "np": p_prox["nome"],
                                "ed": p_prox.get("desc") or "",
                                "py": p_prox["lat"],
                                "px": p_prox["lon"],
                            }

        paradas = list(mapa_paradas.values())

        card(
            f'<div class="card"><div class="row"><div>{badge(letreiro)}'
            f'<span class="card-title">Sentido {h(destino)}</span>'
            f'<div class="card-sub" style="margin-top:6px">Origem: {h(linha["tp"] if linha["sl"] == 1 else linha["ts"])}</div></div>'
            f'<div><span class="chip green"><span class="live"></span>{len(onibus)} ativos</span></div></div></div>'
        )
        if not onibus:
            st.warning("Nenhum veículo desta linha transmitindo sinal GPS neste instante.")

        # --- Ponto de embarque (ordenado do mais próximo para o mais distante) ---
        ponto = None
        if paradas:
            if user_pos:
                paradas.sort(
                    key=lambda p: distancia_km(user_pos[0], user_pos[1], p["py"], p["px"])
                )
                pos_key = f"{user_pos[0]:.4f}_{user_pos[1]:.4f}"
            else:
                pos_key = "noloc"

            def fmt_parada(p: dict) -> str:
                base = rotulo_parada(p)
                if user_pos:
                    d_m = distancia_km(user_pos[0], user_pos[1], p["py"], p["px"]) * 1000
                    return f"📍 {dist_txt(d_m)} • {base}"
                return base

            ponto = st.selectbox(
                "Ponto de embarque",
                paradas,
                index=0,
                format_func=fmt_parada,
                key=f"ponto_{cl}_{pos_key}",
                help="Mostrando todas as paradas da linha ordenadas da mais próxima para a mais distante de você." if user_pos else None,
            )

        chegadas = []
        if ponto:
            # 1) Tenta pegar da previsão geral da linha
            for p in previsao.get("ps") or []:
                if p["cp"] == ponto["cp"]:
                    chegadas = sorted(p.get("vs") or [], key=lambda v: v["t"])
                    break
            # 2) Se for parada comum de rua (fora de corredor), busca a previsão direta da parada
            if not chegadas:
                try:
                    hr_p, ls_p = previsao_da_parada(ponto["cp"])
                    if hr_p:
                        hora_ref = hr_p
                    for l_p in ls_p:
                        if l_p.get("cl") == cl or l_p.get("c") == letreiro:
                            chegadas = sorted(l_p.get("vs") or [], key=lambda v: v["t"])
                            break
                except SPTransError:
                    pass

            caminhada = ""
            if user_pos:
                caminhada = chip_caminhada(distancia_km(user_pos[0], user_pos[1], ponto["py"], ponto["px"]) * 1000)
            if chegadas and hora_ref:
                linhas_html = "".join(
                    linha_eta(v["p"], minutos_ate(hora_ref, v["t"]), v.get("a", False)) for v in chegadas[:4]
                )
            else:
                linhas_html = '<div class="muted" style="padding:10px 0 4px">Sem veículos previstos para esta parada no momento.</div>'
            card(
                f'<div class="card"><div class="card-title">🚏 {h(ponto["np"])}</div>'
                f'<div class="card-sub">{h(ponto.get("ed") or "")}</div>'
                f'<div style="margin:10px 0 6px">{caminhada}</div>{linhas_html}</div>'
            )

        # --- Mapa ---
        if paradas or onibus or trajeto:
            enquadrar = st.segmented_control(
                "Enquadrar", ["🗺️ Linha inteira", "🚏 Meu embarque"], default="🗺️ Linha inteira",
                key="enquadrar", label_visibility="collapsed",
            ) or "🗺️ Linha inteira"
            centro = (ponto["py"], ponto["px"]) if ponto else (onibus[0]["py"], onibus[0]["px"]) if onibus else trajeto[0]
            mapa = mapa_base(centro)

            if trajeto:
                desenhar_trajeto(mapa, trajeto, cor)
            elif len(paradas) > 1:
                desenhar_trajeto(mapa, [(p["py"], p["px"]) for p in paradas], cor)

            for i, p in enumerate(paradas):
                if ponto and p["cp"] == ponto["cp"]:
                    continue
                ponta = i in (0, len(paradas) - 1) and not user_pos
                folium.CircleMarker(
                    (p["py"], p["px"]), radius=7 if ponta else 4,
                    color="#0F172A" if ponta else cor, weight=2, fill=True,
                    fill_color="#10B981" if i == 0 and ponta else "#EF4444" if ponta else "#fff", fill_opacity=1,
                    tooltip=p["np"],
                ).add_to(mapa)

            foco_ponto = []
            if ponto:
                folium.Marker((ponto["py"], ponto["px"]), icon=icone_parada(), tooltip=ponto["np"]).add_to(mapa)
                foco_ponto.append((ponto["py"], ponto["px"]))
            proximos = {v["p"] for v in chegadas[:2]}
            for v in onibus:
                folium.Marker(
                    (v["py"], v["px"]), icon=icone_onibus(cor),
                    tooltip=f"Prefixo {v['p']} • atualizado às {hora_local(v.get('ta'))}" + (" • ♿" if v.get("a") else ""),
                ).add_to(mapa)
                if v["p"] in proximos:
                    foco_ponto.append((v["py"], v["px"]))
            if user_pos:
                folium.Marker(user_pos, icon=icone_usuario(), tooltip="Você está aqui").add_to(mapa)
                foco_ponto.append(user_pos)
                if ponto:
                    folium.PolyLine([user_pos, (ponto["py"], ponto["px"])], color="#2563EB", weight=3, dash_array="4 8").add_to(mapa)

            if enquadrar == "🗺️ Linha inteira":
                foco = list(trajeto) if trajeto else [(p["py"], p["px"]) for p in paradas] or foco_ponto
            else:
                foco = foco_ponto
            desenhar_mapa(mapa, foco, key=f"mapa_linha_{cl}_{enquadrar}")
            st.caption("🟢 Partida · 🔴 Terminal · ► Sentido da viagem · Atualização automática a cada 30s."
                       + ("" if trajeto else " (Trajeto esquemático entre paradas.)"))
    except SPTransError as e:
        st.error(f"⚠️ {e}")

# ======================= ABA: PARADAS =======================
def pagina_paradas():
    termo_parada = st.text_input(
        "Parada", placeholder="🔍 Busque por rua, avenida ou terminal (ex: Av Paulista, Lapa)",
        label_visibility="collapsed", key="q_parada",
    ).strip()

    if not termo_parada:
        card(
            '<div class="empty-state">'
            '<div class="empty-icon">🚏</div>'
            '<div class="card-title">Painel de chegadas por parada</div>'
            '<div class="card-sub" style="max-width:340px;margin:6px auto 0">'
            'Pesquise pelo endereço ou ponto de referência para listar todas as linhas que atendem o local.</div>'
            '</div>'
        )
        return

    try:
        achadas = api_buscar_paradas(termo_parada)
        if not achadas:
            st.info("Nenhuma parada encontrada com esse termo. Tente outro endereço.")
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
            cabecalho += f'<div style="margin-top:10px">{chip_caminhada(distancia_km(user_pos[0], user_pos[1], parada["py"], parada["px"]) * 1000)}</div>'
        card(cabecalho + "</div>")

        proximos_foco = cards_de_chegadas(hora_ref, linhas_parada)

        mapa = mapa_base((parada["py"], parada["px"]))
        folium.Marker((parada["py"], parada["px"]), icon=icone_parada(), tooltip=parada["np"]).add_to(mapa)
        foco = [(parada["py"], parada["px"])] + proximos_foco[:5]
        for l in linhas_parada:
            for v in (l.get("vs") or [])[:1]:
                folium.Marker(
                    (v["py"], v["px"]), icon=icone_onibus(cor_da_linha(l["c"])),
                    tooltip=f"Linha {l['c']} • Prefixo {v['p']}",
                ).add_to(mapa)
        if user_pos:
            folium.Marker(user_pos, icon=icone_usuario(), tooltip="Você está aqui").add_to(mapa)
            foco.append(user_pos)
        desenhar_mapa(mapa, foco, key=f"mapa_parada_{parada['cp']}")
    except SPTransError as e:
        st.error(f"⚠️ {e}")


{NAV[0]: pagina_perto, NAV[1]: pagina_linhas, NAV[2]: pagina_paradas}[aba]()