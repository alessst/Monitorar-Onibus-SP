import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh
import math

# --- FUNÇÃO PARA CALCULAR DISTÂNCIA (Haversine) ---
def calcula_distancia(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c 

# Configuração da página
st.set_page_config(page_title="Monitor Olho Vivo", layout="centered")
st.title("🚌 Monitor de Ônibus - SPTrans")

# --- ATUALIZAÇÃO AUTOMÁTICA ---
st_autorefresh(interval=30000, limit=200, key="atualizacao_onibus")

token = "5d81de1f333bad7ee7f68e15e56e1164e44092202579ad7028e017dde4568e4b"
BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"

# --- PEGAR LOCALIZAÇÃO DO USUÁRIO ---
st.write("📍 **Clique no botão abaixo para permitir ver sua localização:**")
localizacao = streamlit_geolocation()

user_lat = localizacao['latitude']
user_lon = localizacao['longitude']

linha_busca = st.text_input("Digite o número da linha (Ex: 5300)")

# --- RESOLVENDO O BUG DO MAPA SUMINDO ---
if 'buscar' not in st.session_state:
    st.session_state.buscar = False

if st.button("Buscar Ônibus"):
    st.session_state.buscar = True

if st.session_state.buscar:
    if not token or not linha_busca:
        st.warning("⚠️ Preencha a linha para buscar.")
    else:
        with st.spinner("Buscando informações em tempo real..."):
            session = requests.Session()
            auth_url = f"{BASE_URL}/Login/Autenticar?token={token}"
            auth_response = session.post(auth_url)
            
            if auth_response.text == 'true':
                busca_url = f"{BASE_URL}/Linha/Buscar?termosBusca={linha_busca}"
                linhas = session.get(busca_url).json()
                
                if linhas:
                    linha_selecionada = linhas[0]
                    codigo_linha = linha_selecionada['cl']
                    nome_linha = f"{linha_selecionada['lt']}-{linha_selecionada['tl']} ({linha_selecionada['tp']} -> {linha_selecionada['ts']})"
                    
                    st.subheader(f"Monitorando: {nome_linha}")
                    
                    pos_url = f"{BASE_URL}/Posicao/Linha?codigoLinha={codigo_linha}"
                    dados_posicao = session.get(pos_url).json()
                    
                    if 'vs' in dados_posicao and dados_posicao['vs']:
                        veiculos = dados_posicao['vs']
                        
                        lista_veiculos = []
                        for v in veiculos:
                            onibus_info = {
                                'lat': v['py'], 
                                'lon': v['px'], 
                                'Prefixo': v['p'], 
                                'Horário Atualização': v['ta'],
                                'Distancia_km': 9999 
                            }
                            
                            if user_lat is not None and user_lon is not None:
                                onibus_info['Distancia_km'] = calcula_distancia(user_lat, user_lon, v['py'], v['px'])
                                
                            lista_veiculos.append(onibus_info)
                        
                        prefixo_mais_perto = None
                        if user_lat is not None and user_lon is not None:
                            onibus_mais_perto = min(lista_veiculos, key=lambda x: x['Distancia_km'])
                            prefixo_mais_perto = onibus_mais_perto['Prefixo']
                            distancia = onibus_mais_perto['Distancia_km']
                            
                            velocidade_media_kmh = 15.0 
                            tempo_minutos = int((distancia / velocidade_media_kmh) * 60)
                            
                            if tempo_minutos < 1:
                                tempo_texto = "Chegando (menos de 1 min)"
                            else:
                                tempo_texto = f"Aproximadamente {tempo_minutos} min"
                            
                            st.success(
                                f"🚌 **{len(veiculos)}** ônibus operando.\n\n"
                                f"📍 Mais próximo: **{prefixo_mais_perto}** a {distancia:.2f} km.\n\n"
                                f"⏳ **Tempo estimado:** {tempo_texto}."
                            )
                        else:
                            st.success(f"🚌 **{len(veiculos)}** ônibus operando neste momento.")

                        df_veiculos = pd.DataFrame(lista_veiculos)
                        
                        if user_lat is not None:
                            mapa = folium.Map(location=[user_lat, user_lon], zoom_start=14)
                            folium.Marker(
                                location=[user_lat, user_lon],
                                popup="Você está aqui",
                                tooltip="Sua Localização",
                                icon=folium.Icon(color="red", icon="user", prefix="fa")
                            ).add_to(mapa)
                        else:
                            mapa = folium.Map(location=[df_veiculos['lat'].mean(), df_veiculos['lon'].mean()], zoom_start=13)
                        
                        for _, onibus in df_veiculos.iterrows():
                            cor_icone = "green" if onibus['Prefixo'] == prefixo_mais_perto else "blue"
                            icone_tipo = "star" if onibus['Prefixo'] == prefixo_mais_perto else "bus"
                            
                            texto_popup = f"<b>Prefixo:</b> {onibus['Prefixo']}<br><b>Atualizado:</b> {onibus['Horário Atualização']}"
                            if onibus['Distancia_km'] != 9999:
                                tempo_popup = int((onibus['Distancia_km'] / 15.0) * 60)
                                texto_popup += f"<br><b>Distância:</b> {onibus['Distancia_km']:.2f} km"
                                texto_popup += f"<br><b>Tempo Estimado:</b> ~{tempo_popup} min"
                            
                            folium.Marker(
                                location=[onibus['lat'], onibus['lon']],
                                popup=folium.Popup(texto_popup, max_width=200),
                                tooltip=f"Ônibus {onibus['Prefixo']}",
                                icon=folium.Icon(color=cor_icone, icon=icone_tipo, prefix="fa")
                            ).add_to(mapa)
                        
                        st_folium(mapa, width=700, height=500, returned_objects=[])
                        
                    else:
                        st.warning("Nenhum ônibus desta linha está transmitindo sinal de GPS agora.")
            else:
                st.error("Falha na autenticação com a SPTrans.")