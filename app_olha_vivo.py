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
    padding: 1rem 1rem 5rem;
}

.stApp {
    background: var(--bg-app);
}

/* Hero Header Compacto e Moderno */
.hero {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
    color: #fff;
    border-radius: 22px;
    padding: 18px 22px;
    margin-bottom: 12px;
    box-shadow: 0 10px 24px -6px rgba(15, 23, 42, 0.25);
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
.hero::after {
    content: "";
    position: absolute;
    top: -50%;
    right: -15%;
    width: 220px;
    height: 220px;
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
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: linear-gradient(135deg, #F26B21 0%, #FF8C42 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(242, 107, 33, 0.4);
    flex-shrink: 0;
}
.hero h1 {
    font-size: 1.25rem;
    margin: 0;
    padding: 0;
    color: #fff;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.2;
}
.hero p {
    margin: 2px 0 0;
    color: #94A3B8;
    font-size: 0.78rem;
    font-weight: 500;
}
.live-pill {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34D399;
    font-size: 0.68rem;
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
    font-size: 0.82rem !important;
    padding: 0.45rem 0.7rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
    transition: all 0.18s ease !important;
}
.stButton > button:hover, .stPopover > div > button:hover {
    border-color: #CBD5E1 !important;
    background: #F1F5F9 !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
    background: var(--brand) !important;
    color: #FFFFFF !important;
    border-color: var(--brand) !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--brand-dark) !important;
}

/* Cards */
.card {
    background: var(--surface);
    border-radius: 18px;
    padding: 15px 17px;
    margin: 8px 0;
    border: 1px solid var(--border);
    box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.04);
    transition: all 0.18s ease;
}
.card.interactive:hover {
    border-color: #CBD5E1;
    box-shadow: 0 8px 20px -4px rgba(15, 23, 42, 0.08);
}
.card.selected {
    border: 2px solid var(--brand);
    background: #FFFDFB;
    box-shadow: 0 8px 22px -4px rgba(242, 107, 33, 0.16);
}
.card.compact {
    padding: 12px 14px;
    margin: 5px 0;
    border-radius: 16px;
}
.card.dest-banner {
    background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%);
    border-color: #FDBA74;
    padding: 12px 16px;
}
.card-title {
    font-weight: 700;
    color: var(--text-main);
    font-size: 0.95rem;
    letter-spacing: -0.01em;
}
.card-sub {
    color: var(--text-sub);
    font-size: 0.78rem;
    margin-top: 3px;
    font-weight: 500;
}

/* Empty State Card */
.empty-state {
    background: var(--surface);
    border: 1px dashed #CBD5E1;
    border-radius: 20px;
    padding: 26px 20px;
    text-align: center;
    margin: 12px 0;
}
.empty-icon {
    width: 46px;
    height: 46px;
    border-radius: 14px;
    background: var(--brand-light);
    color: var(--brand);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 1.35rem;
    margin-bottom: 8px;
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
    font-size: 0.85rem;
    letter-spacing: 0.02em;
    margin-right: 8px;
    box-shadow: inset 0 -1px 0 rgba(0,0,0,0.18), 0 2px 4px rgba(0,0,0,0.08);
}

/* Layout e Linhas de Previsão (ETA) */
.row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}
.eta-box {
    text-align: right;
    min-width: 78px;
    background: #F8FAFC;
    padding: 6px 10px;
    border-radius: 12px;
    border: 1px solid var(--border);
    flex-shrink: 0;
}
.eta-box.soon {
    background: var(--success-bg);
    border-color: #A7F3D0;
}
.eta-time {
    font-weight: 800;
    font-size: 1.25rem;
    color: var(--text-main);
    line-height: 1.05;
    font-variant-numeric: tabular-nums;
}
.eta-time span {
    font-size: 0.68rem;
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
    padding: 3px 10px;
    font-size: 0.72rem;
    font-weight: 700;
    margin-right: 5px;
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
    margin-right: 5px;
    animation: pulse 1.8s infinite;
}
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
    70% { box-shadow: 0 0 0 7px rgba(16, 185, 129, 0); }
    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.muted { color: var(--text-muted); font-size: 0.8rem; font-weight: 500; }
.sec {
    font-weight: 800;
    color: var(--text-main);
    margin: 14px 0 6px;
    font-size: 0.86rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    display: flex;
    align-items: center;
    justify-content: space-between;
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
    conteudo = "".join(linha.strip() for linha in conteudo.splitlines())
    st.markdown(conteudo, unsafe_allow_html=True)


def norm_letreiro(cod: str) -> str:
    """Normaliza '8000-10' e '8000' para comparar GTFS com API sem falhas."""
    return str(cod or "").strip().upper()


def letreiro_base(cod: str) -> str:
    return norm_letreiro(cod).split("-")[0]


def cor_da_linha(letreiro: str) -> str:
    hue = (sum(ord(c) * (i + 3) for i, c in enumerate(str(letreiro))) % 360) / 360
    r, g, b = colorsys.hls_to_rgb(hue, 0.36, 0.68)
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


def badge(letreiro: str) -> str:
    return f'<span class="badge" style="background:{cor_da_linha(letreiro)}">{h(letreiro)}</span>'


def texto_eta(minutos: int | None, demais: list[int] | None = None, estimado: bool = False) -> str:
    if minutos is None:
        return '<div class="eta-box"><div class="eta-time"><span style="margin:0">sem GPS</span></div></div>'
    sub_html = ""
    if demais:
        d_str = ", ".join(f"{m}m" if m > 0 else "já" for m in demais[:2])
        sub_html = f'<div style="font-size:0.64rem;color:#64748B;font-weight:600;margin-top:2px">+{d_str}</div>'
    elif estimado:
        sub_html = '<div style="font-size:0.62rem;color:#059669;font-weight:600;margin-top:2px">via GPS</div>'
    if minutos <= 0:
        return f'<div class="eta-box soon"><div class="eta-time soon">Agora</div>{sub_html}</div>'
    soon_cls = "soon" if minutos <= 4 else ""
    prefixo = "~" if estimado else ""
    return f'<div class="eta-box {soon_cls}"><div class="eta-time {soon_cls}">{prefixo}{minutos}<span>min</span></div>{sub_html}</div>'


def dist_txt(metros: float) -> str:
    return f"{metros:.0f} m" if metros < 1000 else f"{metros / 1000:.1f} km"


def mapa_base(centro, zoom: int = 16) -> folium.Map:
    m = folium.Map(location=centro, zoom_start=zoom, tiles="OpenStreetMap", zoom_control=True)
    m.get_root().header.add_child(
        folium.Element("<style>.leaflet-tile-pane { filter: saturate(0.55) contrast(1.03) brightness(1.03); }</style>")
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
        html=(f'<div style="background:{cor};border:2.5px solid #fff;border-radius:50%;width:34px;height:34px;'
              'display:flex;align-items:center;justify-content:center;'
              'box-shadow:0 4px 10px rgba(15,23,42,.35)">'
              f'{svg_bus}</div>'),
    )


def icone_parada(cor_bg: str = COR_MARCA) -> folium.DivIcon:
    svg_stop = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" '
        'fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect width="16" height="16" x="4" y="3" rx="2"/><path d="M4 11h16"/>'
        '<path d="M12 3v8"/><path d="m8 19-2 3"/><path d="m18 22-2-3"/><path d="M8 15h0"/><path d="M16 15h0"/></svg>'
    )
    return folium.DivIcon(
        icon_size=(36, 36),
        icon_anchor=(18, 36),
        html=(f'<div style="background:{cor_bg};border:2.5px solid #fff;border-radius:50% 50% 50% 0;'
              'transform:rotate(-45deg);width:36px;height:36px;box-shadow:0 4px 10px rgba(15,23,42,.35);'
              'display:flex;align-items:center;justify-content:center">'
              f'<span style="transform:rotate(45deg);display:flex">{svg_stop}</span></div>'),
    )


def icone_usuario() -> folium.DivIcon:
    return folium.DivIcon(
        icon_size=(24, 24),
        icon_anchor=(12, 12),
        html=('<style>@keyframes p{0%{box-shadow:0 0 0 0 rgba(37,99,235,.55)}'
              '70%{box-shadow:0 0 0 16px rgba(37,99,235,0)}100%{box-shadow:0 0 0 0 rgba(37,99,235,0)}}</style>'
              '<div style="width:18px;height:18px;border-radius:50%;background:#2563EB;border:3px solid #fff;'
              'box-shadow:0 2px 6px rgba(0,0,0,.3);animation:p 2s infinite"></div>'),
    )


def icone_destino() -> folium.DivIcon:
    svg_pin = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
        'fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>'
    )
    return folium.DivIcon(
        icon_size=(36, 36),
        icon_anchor=(18, 36),
        html=(f'<div style="background:#EF4444;border:2.5px solid #fff;border-radius:50% 50% 50% 0;'
              'transform:rotate(-45deg);width:36px;height:36px;box-shadow:0 4px 10px rgba(15,23,42,.35);'
              'display:flex;align-items:center;justify-content:center">'
              f'<span style="transform:rotate(45deg);display:flex">{svg_pin}</span></div>'),
    )


def desenhar_mapa(mapa: folium.Map, pontos_foco: list, key: str, altura: int = 340) -> None:
    if len(pontos_foco) > 1:
        mapa.fit_bounds(pontos_foco, padding=(38, 38), max_zoom=17)
    st_folium(mapa, height=altura, use_container_width=True, returned_objects=[], key=key)


def desenhar_trajeto(mapa: folium.Map, pontos: list, cor: str) -> None:
    folium.PolyLine(pontos, color="#FFFFFF", weight=9, opacity=0.95).add_to(mapa)
    linha = folium.PolyLine(pontos, color=cor, weight=5, opacity=0.95).add_to(mapa)
    PolyLineTextPath(
        linha, "      ►      ", repeat=True, offset=6,
        attributes={"fill": "#FFFFFF", "font-size": "12", "font-weight": "bold"}
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
        '`SPTRANS_TOKEN = "seu_token"` (ou configure nos Secrets do Streamlit Cloud).'
    )
    st.stop()


@st.cache_resource
def cliente() -> SPTransClient:
    return SPTransClient(TOKEN)


@st.cache_data(ttl=600, show_spinner=False)
def api_buscar_linhas(termo):
    return cliente().buscar_linhas(termo)


@st.cache_data(ttl=15, show_spinner=False)
def api_posicao_linha(cl):
    return cliente().posicao_linha(cl)


@st.cache_data(ttl=15, show_spinner=False)
def api_previsao_linha(cl):
    return cliente().previsao_linha(cl)


@st.cache_data(ttl=15, show_spinner=False)
def api_previsao_parada(cp):
    return cliente().previsao_parada(cp)


@st.cache_resource(show_spinner="Preparando malha de linhas e paradas de SP (só na 1ª vez, ~10 s)...")
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
    q_busca = endereco if "são paulo" in endereco.lower() or "sp" in endereco.lower() else f"{endereco}, São Paulo, SP"
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": q_busca, "format": "json", "limit": 1, "countrycodes": "br",
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


def previsao_da_parada(cp) -> tuple[str | None, list]:
    dados = api_previsao_parada(cp)
    return dados.get("hr"), (dados.get("p") or {}).get("l") or []


@st.cache_data(ttl=15, show_spinner=False)
def obter_dados_tempo_real_linha(rota: str, sl: int, lat_parada: float, lon_parada: float):
    """
    Busca a frota em tempo real de uma linha e calcula a estimativa de chegada (ETA)
    para paradas comuns de rua que a API PrevisaoParada da SPTrans não cobre.
    """
    try:
        termo = letreiro_base(rota)
        linhas = api_buscar_linhas(termo)
        if not linhas:
            return [], [], None
        alvo = norm_letreiro(rota)
        linha = next(
            (l for l in linhas if f"{l['lt']}-{l['tl']}".upper() == alvo and l["sl"] == sl),
            next((l for l in linhas if l["sl"] == sl), linhas[0]),
        )
        cl = linha["cl"]
        pos = api_posicao_linha(cl)
        vs = pos.get("vs") or []
        if not vs:
            return [], [], cl

        # Calcula a distância de cada veículo ativo até a parada do usuário
        # Velocidade média urbana de ônibus em SP (~17 km/h -> ~280 metros/minuto)
        mins_estimados = []
        for v in vs:
            d_km = distancia_km(lat_parada, lon_parada, v["py"], v["px"])
            # Considera ônibus num raio de até 12 km da parada
            if d_km <= 12.0:
                m_est = max(1, round((d_km * 1.25) / 0.28))  # 1.25 compensa curvas de rua
                mins_estimados.append(m_est)
        mins_estimados.sort()
        return mins_estimados[:3], vs, cl
    except Exception:
        return [], [], None


# ======================= ESTADO & LOCALIZAÇÃO =======================
st.session_state.setdefault("lembrar", True)
st.session_state.setdefault("gps_n", 0)
st.session_state.setdefault("raio", 100)  # Padrão 100m
st.session_state.setdefault("raio_destino", 700)
st.session_state.setdefault("linha_mapa", None)  # (rota, direcao, cp_embarque) selecionada para ver no mapa principal


def _novo_gps():
    st.session_state["gps_n"] += 1
    st.session_state.pop("pos_manual", None)
    st.session_state.pop("gps_erro", None)


def alternar_linha_no_mapa(rota: str, direcao: int, cp_embarque: int):
    atual = st.session_state.get("linha_mapa")
    if atual and atual[0] == rota and atual[1] == direcao:
        st.session_state["linha_mapa"] = None
    else:
        st.session_state["linha_mapa"] = (rota, direcao, cp_embarque)


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
    1: "Permissão de localização negada. Permita o uso do GPS no cadeado do navegador e clique em Atualizar.",
    2: "Não foi possível obter sua posição via satélite/rede agora. Tente novamente.",
    3: "O GPS demorou para responder. Toque em Atualizar pelo GPS.",
    99: "O navegador exige conexão segura (HTTPS ou localhost) para liberar o GPS.",
}


def form_endereco(chave: str) -> None:
    end_txt = st.text_input("Sua origem manual", placeholder="Ex: Av. Paulista, 1000", label_visibility="collapsed", key=f"end_txt_{chave}")
    c1, c2 = st.columns(2)
    if c1.button("Fixar origem", key=f"btn_end_{chave}", use_container_width=True) and end_txt.strip():
        try:
            achado = geocodificar(end_txt.strip())
            if achado:
                st.session_state["pos_manual"] = (achado[0], achado[1])
                st.session_state["pos_manual_nome"] = achado[2]
                st.rerun()
            else:
                st.warning("Endereço não encontrado.")
        except requests.RequestException:
            st.error("Erro ao consultar endereço.")
    if c2.button("Usar GPS", key=f"btn_limpar_{chave}", use_container_width=True):
        st.session_state.pop("pos_manual", None)
        st.rerun()


# 1) Carrega preferências salvas no navegador
if "prefs_carregadas" not in st.session_state:
    bruto = streamlit_js_eval(js_expressions="localStorage.getItem('olhovivo')", key="ls_read")
    if bruto:
        try:
            prefs = json.loads(bruto)
            st.session_state["lembrar"] = bool(prefs.get("lembrar", True))
            if prefs.get("raio") in (100, 200, 300, 500, 800, 1000):
                st.session_state["raio"] = int(prefs["raio"])
            if st.session_state["lembrar"] and prefs.get("lat") is not None:
                st.session_state["pos_salva"] = (prefs["lat"], prefs["lon"])
        except (ValueError, TypeError):
            pass
        st.session_state["prefs_carregadas"] = True

# 2) Solicita GPS de alta precisão
res_gps = streamlit_js_eval(js_expressions=JS_GPS, key=f"gps_{st.session_state['gps_n']}")
if isinstance(res_gps, dict):
    coords = res_gps.get("coords") or {}
    if coords.get("latitude") is not None and coords.get("longitude") is not None:
        st.session_state["pos_gps"] = (coords["latitude"], coords["longitude"])
        st.session_state["gps_acc"] = coords.get("accuracy")
        st.session_state.pop("gps_erro", None)
    elif res_gps.get("error"):
        st.session_state["gps_erro"] = res_gps["error"].get("code", 2)

# ======================= CABEÇALHO & POPOVER DE LOCALIZAÇÃO =======================
card(
    '<div class="hero">'
    '<div class="hero-top">'
    '<div class="hero-brand">'
    '<div class="hero-icon">'
    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6v6"/><path d="M15 6v6"/><path d="M2 12h19.6"/><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3"/><circle cx="7" cy="18" r="2"/><path d="M9 18h5"/><circle cx="16" cy="18" r="2"/></svg>'
    '</div>'
    '<div><h1>Olho Vivo SP</h1><p>Radar inteligente de paradas e destinos</p></div>'
    '</div>'
    '<div class="live-pill"><span class="live" style="margin-right:2px"></span>Ao vivo</div>'
    '</div>'
    '</div>'
)

col_status, col_cfg = st.columns([3.1, 1.9], vertical_alignment="center")
with col_cfg:
    with st.popover(f"⚙️ Local · {st.session_state['raio']}m", use_container_width=True):
        st.markdown("**📏 Raio de busca ao seu redor**")
        st.select_slider(
            "Raio de busca",
            options=[100, 200, 300, 500, 800, 1000],
            format_func=lambda m: f"{m} m",
            key="raio",
            label_visibility="collapsed",
        )
        st.divider()
        st.button("🔄 Atualizar pelo GPS", on_click=_novo_gps, key="btn_gps", use_container_width=True)
        st.toggle(
            "Lembrar minha posição neste aparelho", key="lembrar",
            help="Salva sua última coordenada e raio preferido no navegador."
        )
        st.markdown("**Ou defina seu ponto de partida:**")
        form_endereco("popover")

if "pos_manual" in st.session_state:
    user_pos, origem_pos = st.session_state["pos_manual"], "Origem manual"
elif "pos_gps" in st.session_state:
    user_pos, origem_pos = st.session_state["pos_gps"], "GPS ativo"
elif "pos_salva" in st.session_state:
    user_pos, origem_pos = st.session_state["pos_salva"], "Posição salva"
else:
    user_pos, origem_pos = None, None

# Salva preferências no navegador
_pos_para_salvar = st.session_state.get("pos_gps") or st.session_state.get("pos_salva")
_payload = {"lembrar": bool(st.session_state["lembrar"]), "raio": int(st.session_state["raio"])}
if st.session_state["lembrar"] and _pos_para_salvar:
    _payload.update(lat=round(_pos_para_salvar[0], 5), lon=round(_pos_para_salvar[1], 5))
streamlit_js_eval(
    js_expressions=f"localStorage.setItem('olhovivo', {json.dumps(json.dumps(_payload))})",
    key=f"ls_save_{json.dumps(_payload, sort_keys=True)}",
)

with col_status:
    if user_pos:
        classe = "green" if origem_pos != "Posição salva" else "gray"
        acc = st.session_state.get("gps_acc")
        acc_txt = f" (±{acc:.0f}m)" if acc and origem_pos == "GPS ativo" else ""
        st.markdown(
            f'<span class="chip {classe}">📍 {origem_pos}{acc_txt}</span>'
            f'<span class="chip gray">🎯 Raio {st.session_state["raio"]}m</span>',
            unsafe_allow_html=True,
        )
    elif st.session_state.get("gps_erro") is not None:
        st.markdown('<span class="chip">📍 Sem localização</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="muted">⏳ Obtendo localização...</span>', unsafe_allow_html=True)


# ======================= PAINEL UNIFICADO PRINCIPAL =======================
def painel_principal():
    if not user_pos:
        codigo = st.session_state.get("gps_erro")
        card(
            '<div class="empty-state">'
            '<div class="empty-icon">📍</div>'
            '<div class="card-title">Aguardando sua localização</div>'
            '<div class="card-sub" style="max-width:360px;margin:6px auto 0">'
            'Permita o acesso ao GPS no navegador ou informe um endereço abaixo para ver as paradas e linhas ao seu redor.</div>'
            '</div>'
        )
        if codigo is not None:
            st.warning(MSG_GPS.get(codigo, MSG_GPS[2]))
        st.button("🔄 Tentar capturar GPS novamente", on_click=_novo_gps, key="btn_gps_home", use_container_width=True)
        form_endereco("home")
        return

    G = gtfs_ou_none()
    if G is None:
        st.error(f"Não foi possível carregar a base GTFS: {st.session_state.get('gtfs_erro')}")
        return

    # ---------------- 1. BARRA "PARA ONDE VOCÊ VAI?" ----------------
    c_in, c_btn = st.columns([3.8, 1.2], vertical_alignment="center")
    with c_in:
        dest_query = st.text_input(
            "Para onde você vai?",
            placeholder="🎯 Para onde você vai? (Ex: Av. Paulista, Ibirapuera, Lapa)",
            label_visibility="collapsed",
            key="input_destino",
        ).strip()
    with c_btn:
        btn_ir = st.button("Buscar", use_container_width=True, type="primary")

    if btn_ir and dest_query:
        with st.spinner("Localizando destino e cruzando linhas..."):
            try:
                achado = geocodificar(dest_query)
                if achado:
                    st.session_state["dest_pos"] = (achado[0], achado[1])
                    st.session_state["dest_nome"] = achado[2].split(",")[0]
                    st.session_state["linha_mapa"] = None
                else:
                    st.warning("Local não encontrado em São Paulo. Tente incluir o bairro.")
            except Exception:
                st.error("Não foi possível buscar o destino agora.")

    dest_pos = st.session_state.get("dest_pos")
    dest_nome = st.session_state.get("dest_nome")

    # Mapa de linhas que passam perto do destino -> guarda a parada MAIS PRÓXIMA do endereço pesquisado
    linhas_destino_map = {}  # (letreiro, direcao) -> parada_desembarque
    if dest_pos:
        p_dest_lista = gtfs_data.paradas_proximas(G, dest_pos[0], dest_pos[1], st.session_state["raio_destino"], limite=80)
        p_dest_lista.sort(key=lambda x: x["dist_m"])
        for pd in p_dest_lista:
            for chave in pd["linhas"]:
                linhas_destino_map.setdefault(chave, pd)

        b_col1, b_col2 = st.columns([4.1, 1.3], vertical_alignment="center")
        with b_col1:
            card(
                f'<div class="card dest-banner">'
                f'<div class="card-title">🏁 Destino: {h(dest_nome)}</div>'
                f'<div class="card-sub">Clique em <b>👁️ Ver rota</b> em qualquer ônibus abaixo para ver no mapa onde ele passa!</div>'
                f'</div>'
            )
        with b_col2:
            if st.button("✖ Limpar", use_container_width=True, help="Remover filtro de destino"):
                st.session_state.pop("dest_pos", None)
                st.session_state.pop("dest_nome", None)
                st.session_state["linha_mapa"] = None
                st.rerun()

    # ---------------- 2. BUSCA PARADAS PRÓXIMAS (PADRÃO 100m) ----------------
    raio_atual = st.session_state["raio"]
    proximas = gtfs_data.paradas_proximas(G, user_pos[0], user_pos[1], raio_atual, limite=30)
    proximas.sort(key=lambda p: p["dist_m"])

    if not proximas:
        mais_perto = gtfs_data.paradas_proximas(G, user_pos[0], user_pos[1], 800, limite=5)
        mais_perto.sort(key=lambda p: p["dist_m"])
        dist_sugerida = f" (a parada mais próxima está a **{dist_txt(mais_perto[0]['dist_m'])}**)" if mais_perto else ""
        st.info(f"Nenhuma parada encontrada em um raio de **{raio_atual} m**{dist_sugerida}.")
        c_exp1, c_exp2 = st.columns(2)
        if c_exp1.button("🔍 Expandir para 300 m", use_container_width=True, type="primary"):
            st.session_state["raio"] = 300
            st.rerun()
        if c_exp2.button("🔍 Expandir para 500 m", use_container_width=True):
            st.session_state["raio"] = 500
            st.rerun()
        return

    if dest_pos:
        proximas_filtradas = [
            p for p in proximas
            if any(ch in linhas_destino_map for ch in p["linhas"])
        ]
        if not proximas_filtradas:
            st.warning(
                f"Nenhum ônibus nas paradas a até **{raio_atual} m** de você passa perto de **{dest_nome}**. "
                "Expanda seu raio de busca abaixo:"
            )
            c_e1, c_e2 = st.columns(2)
            if c_e1.button("🔍 Buscar em 400 m de mim", use_container_width=True, type="primary"):
                st.session_state["raio"] = 400
                st.rerun()
            if c_e2.button("🔍 Buscar em 800 m de mim", use_container_width=True):
                st.session_state["raio"] = 800
                st.rerun()
            return
        proximas = proximas_filtradas

    # ---------------- 3. SELETOR DE PARADA (FILTRA PARADA -> FILTRA ÔNIBUS) ----------------
    st.markdown('<div class="sec"><span>🚏 Filtrar por parada próxima</span></div>', unsafe_allow_html=True)

    opcoes_parada = [None] + [p["cp"] for p in proximas]
    mapa_cp_parada = {p["cp"]: p for p in proximas}

    def rotulo_pill_parada(cp_val):
        if cp_val is None:
            return f"✨ Todas ({len(proximas)})"
        p = mapa_cp_parada[cp_val]
        return f"🚏 {p['nome']} ({dist_txt(p['dist_m'])})"

    cp_selecionado = st.pills(
        "Filtrar por parada próxima",
        options=opcoes_parada,
        default=None,
        format_func=rotulo_pill_parada,
        label_visibility="collapsed",
        key=f"pill_parada_{raio_atual}_{'dest' if dest_pos else 'all'}",
    )

    paradas_ativas = [mapa_cp_parada[cp_selecionado]] if cp_selecionado in mapa_cp_parada else proximas

    # ---------------- 4. CONSOLIDAÇÃO DAS LINHAS + PREVISÃO HÍBRIDA (API + GPS) ----------------
    melhor_parada_por_linha = {}
    for p in paradas_ativas:
        for chave in p["linhas"]:
            if dest_pos and chave not in linhas_destino_map:
                continue
            melhor_parada_por_linha.setdefault(chave, p)

    # 4.1) Tenta buscar via API PrevisaoParada (rápido para corredores)
    etas_oficiais = {}  # (cp, letreiro_norm, sl) -> lista de minutos
    etas_base = {}      # (cp, base_num, sl) -> lista de minutos
    try:
        for p in paradas_ativas[:6]:
            hr, ls = previsao_da_parada(p["cp"])
            for l in ls:
                vs = sorted(l.get("vs") or [], key=lambda v: v["t"])
                if hr and vs:
                    mins_l = [minutos_ate(hr, v["t"]) for v in vs]
                    c_norm = norm_letreiro(l.get("c"))
                    c_base = letreiro_base(c_norm)
                    sl_l = l.get("sl")
                    etas_oficiais[(p["cp"], c_norm, sl_l)] = mins_l
                    etas_base[(p["cp"], c_base, sl_l)] = mins_l
    except SPTransError:
        pass

    # 4.2) Para as linhas visíveis que estão em paradas de rua comuns (sem retorno na PrevisaoParada),
    #      consulta a frota ao vivo da linha para nunca deixar a tela principal sem previsão!
    dados_linhas = {}  # (rota, direcao) -> {"mins": list, "estimado": bool, "vs": list}
    candidatas = list(melhor_parada_por_linha.items())

    # Se tiver filtro de destino, ordena primeiro pelas que deixam MAIS PERTO do endereço pesquisado!
    if dest_pos:
        candidatas.sort(key=lambda kv: (linhas_destino_map[kv[0]]["dist_m"], kv[1]["dist_m"]))
    else:
        candidatas.sort(key=lambda kv: (kv[1]["dist_m"], kv[0][0]))

    for (rota, direcao), p in candidatas[:12]:
        sl = 2 - direcao
        r_norm = norm_letreiro(rota)
        r_base = letreiro_base(rota)
        mins = etas_oficiais.get((p["cp"], r_norm, sl)) or etas_base.get((p["cp"], r_base, sl))
        if mins:
            dados_linhas[(rota, direcao)] = {"mins": mins, "estimado": False, "vs": []}
        else:
            mins_est, vs_linha, _ = obter_dados_tempo_real_linha(rota, sl, p["lat"], p["lon"])
            dados_linhas[(rota, direcao)] = {"mins": mins_est, "estimado": True, "vs": vs_linha}

    # ---------------- 5. MAPA INTELIGENTE (MOSTRA PARADAS OU A ROTA DO ÔNIBUS CLICADO) ----------------
    linha_ativa_mapa = st.session_state.get("linha_mapa")
    # Verifica se a linha selecionada ainda pertence à lista atual
    if linha_ativa_mapa and (linha_ativa_mapa[0], linha_ativa_mapa[1]) not in melhor_parada_por_linha:
        linha_ativa_mapa = None
        st.session_state["linha_mapa"] = None

    mapa = mapa_base(user_pos)
    foco_mapa = [user_pos]

    if linha_ativa_mapa:
        # MODO ROTA DO ÔNIBUS SELECIONADO: Desenha o trajeto completo, os ônibus ao vivo, embarque e desembarque!
        rota_sel, dir_sel, _ = linha_ativa_mapa
        sl_sel = 2 - dir_sel
        cor_sel = cor_da_linha(rota_sel)
        dest_str = G["destino"].get((rota_sel, dir_sel), "")
        p_emb = melhor_parada_por_linha[(rota_sel, dir_sel)]

        trajeto = gtfs_data.trajeto_da_linha(G, rota_sel, sl_sel, dest_str)
        if trajeto:
            desenhar_trajeto(mapa, trajeto, cor_sel)

        # Marca a parada de embarque (verde/laranja)
        folium.Marker(
            (p_emb["lat"], p_emb["lon"]),
            icon=icone_parada(cor_bg="#059669"),
            tooltip=f"🟢 Embarque: {p_emb['nome']} ({dist_txt(p_emb['dist_m'])} de você)",
        ).add_to(mapa)
        folium.PolyLine([user_pos, (p_emb["lat"], p_emb["lon"])], color="#2563EB", weight=3, dash_array="4 6").add_to(mapa)
        foco_mapa.append((p_emb["lat"], p_emb["lon"]))

        # Se tiver endereço pesquisado, destaca a parada de desembarque mais próxima do destino!
        if dest_pos and (rota_sel, dir_sel) in linhas_destino_map:
            p_desc = linhas_destino_map[(rota_sel, dir_sel)]
            folium.Marker(
                (p_desc["lat"], p_desc["lon"]),
                icon=icone_parada(cor_bg="#0F172A"),
                tooltip=f"🏁 Descer em: {p_desc['nome']} ({dist_txt(p_desc['dist_m'])} do destino)",
            ).add_to(mapa)
            folium.PolyLine([dest_pos, (p_desc["lat"], p_desc["lon"])], color="#EF4444", weight=3, dash_array="4 6").add_to(mapa)
            foco_mapa.extend([dest_pos, (p_desc["lat"], p_desc["lon"])])

        # Plota os ônibus ao vivo dessa linha no mapa
        info_rt = dados_linhas.get((rota_sel, dir_sel)) or {}
        vs_ativos = info_rt.get("vs")
        if not vs_ativos:
            _, vs_ativos, _ = obter_dados_tempo_real_linha(rota_sel, sl_sel, p_emb["lat"], p_emb["lon"])
        for v in (vs_ativos or []):
            folium.Marker(
                (v["py"], v["px"]),
                icon=icone_onibus(cor_sel),
                tooltip=f"🚌 Linha {rota_sel} • Prefixo {v['p']} ({hora_local(v.get('ta'))})",
            ).add_to(mapa)
            if not dest_pos:
                foco_mapa.append((v["py"], v["px"]))

        if not dest_pos and trajeto:
            foco_mapa.extend(trajeto[::max(1, len(trajeto) // 10)])
    else:
        # MODO RADAR PADRÃO: Mostra seu raio e paradas próximas
        folium.Circle(user_pos, radius=raio_atual, color=COR_MARCA, weight=1.5, fill=True, fill_opacity=0.06, dash_array="6").add_to(mapa)
        for p in proximas:
            selecionada = (cp_selecionado == p["cp"])
            if selecionada or len(proximas) <= 5:
                folium.Marker(
                    (p["lat"], p["lon"]),
                    icon=icone_parada(cor_bg="#0F172A" if selecionada else COR_MARCA),
                    tooltip=f"{p['nome']} ({dist_txt(p['dist_m'])})",
                ).add_to(mapa)
            else:
                folium.CircleMarker(
                    (p["lat"], p["lon"]), radius=7, color="#fff", weight=2,
                    fill=True, fill_color=COR_MARCA, fill_opacity=1,
                    tooltip=f"{p['nome']} ({dist_txt(p['dist_m'])})",
                ).add_to(mapa)
            if cp_selecionado is None or selecionada:
                foco_mapa.append((p["lat"], p["lon"]))

    folium.Marker(user_pos, icon=icone_usuario(), tooltip="Você está aqui").add_to(mapa)
    if dest_pos:
        folium.Marker(dest_pos, icon=icone_destino(), tooltip=f"Destino: {dest_nome}").add_to(mapa)
        foco_mapa.append(dest_pos)

    # Barra de status do mapa caso uma linha esteja desenhada nele
    if linha_ativa_mapa:
        c_m1, c_m2 = st.columns([4.0, 1.4], vertical_alignment="center")
        with c_m1:
            st.caption(f"🗺️ Exibindo no mapa o trajeto e frota da linha **{linha_ativa_mapa[0]}**")
        with c_m2:
            if st.button("✖ Ocultar rota", use_container_width=True):
                st.session_state["linha_mapa"] = None
                st.rerun()

    desenhar_mapa(
        mapa, foco_mapa,
        key=f"mapa_principal_{cp_selecionado}_{raio_atual}_{bool(dest_pos)}_{linha_ativa_mapa}",
        altura=330,
    )

    # ---------------- 6. ORDENAÇÃO E CARDS INTERATIVOS DAS LINHAS ----------------
    def _ordem_final(item):
        (rota, direcao), p = item
        info = dados_linhas.get((rota, direcao)) or {}
        mins = info.get("mins") or []
        eta_p = mins[0] if mins else 999
        # Se pesquisou endereço, prioriza o ônibus que passa MAIS PERTO do destino!
        if dest_pos and (rota, direcao) in linhas_destino_map:
            dist_dest = linhas_destino_map[(rota, direcao)]["dist_m"]
            return (0 if mins else 1, dist_dest, eta_p, p["dist_m"])
        return (eta_p, p["dist_m"], rota)

    linhas_ordenadas = sorted(candidatas, key=_ordem_final)

    titulo_sec = (
        f"🚌 Ônibus para {dest_nome} ({len(linhas_ordenadas)})"
        if dest_pos
        else f"🚌 Ônibus em {mapa_cp_parada[cp_selecionado]['nome']}"
        if cp_selecionado in mapa_cp_parada
        else f"🚌 Linhas próximas ({len(linhas_ordenadas)})"
    )
    st.markdown(f'<div class="sec"><span>{h(titulo_sec)}</span><span>Previsão</span></div>', unsafe_allow_html=True)

    for (rota, direcao), p in linhas_ordenadas[:15]:
        info = dados_linhas.get((rota, direcao)) or {}
        mins = info.get("mins") or []
        estimado = info.get("estimado", False)
        eta_html = texto_eta(mins[0], mins[1:], estimado=estimado) if mins else texto_eta(None)
        destino_letreiro = h(G["destino"].get((rota, direcao), "Terminal"))

        esta_no_mapa = bool(linha_ativa_mapa and linha_ativa_mapa[0] == rota and linha_ativa_mapa[1] == direcao)
        cls_selecionado = "selected" if esta_no_mapa else ""

        info_desembarque = ""
        if dest_pos and (rota, direcao) in linhas_destino_map:
            p_desc = linhas_destino_map[(rota, direcao)]
            info_desembarque = (
                f'<div class="card-sub" style="margin-top:4px;color:#059669">'
                f'🏁 <b>Descer a {dist_txt(p_desc["dist_m"])} do destino:</b> {h(p_desc["nome"])}</div>'
            )

        status_live = '<span class="live"></span>' if mins else ""
        col_card, col_btn = st.columns([4.5, 1.3], vertical_alignment="center")
        with col_card:
            card(
                f'<div class="card compact interactive {cls_selecionado}"><div class="row"><div>'
                f'{badge(rota)}<span class="card-title" style="font-size:0.91rem">➜ {destino_letreiro}</span>'
                f'<div class="card-sub" style="margin-top:5px">{status_live}🟢 <b>Embarque ({dist_txt(p["dist_m"])}):</b> {h(p["nome"])}</div>'
                f'{info_desembarque}'
                f'</div>{eta_html}</div></div>'
            )
        with col_btn:
            rotulo_btn = "✅ No mapa" if esta_no_mapa else "👁️ Ver rota"
            tipo_btn = "primary" if esta_no_mapa else "secondary"
            st.button(
                rotulo_btn,
                key=f"btn_rota_{rota}_{direcao}_{p['cp']}",
                on_click=alternar_linha_no_mapa,
                args=(rota, direcao, p["cp"]),
                type=tipo_btn,
                help="Desenha a rota deste ônibus no mapa acima para ver onde ele passa",
                use_container_width=True,
            )


painel_principal()