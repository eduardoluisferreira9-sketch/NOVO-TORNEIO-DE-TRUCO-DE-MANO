import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

import gerenciador_dados
import motor_truco

# ==============================================================================
# 💾 1ª PARTE: INICIALIZAÇÃO DE DADOS PERSISTENTES (ANTI-RESET DE PÁGINA)
# ==============================================================================
dados_persistidos = gerenciador_dados.carregar_dados()

if 'dados' not in st.session_state:
    if dados_persistidos is not None and isinstance(dados_persistidos, dict):
        st.session_state.dados = dados_persistidos
    else:
        st.session_state.dados = {
            'NomeTorneio': '', 'Status': 'Configuração',
            'Jogadores': [], 'RodadaAtual': 0, 'Rodadas': [],
            'TempoLimiteMinutos': 45,  
            'Cronometro': {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False},
            'HistoricoCampeoes': []
        }
else:
    if dados_persistidos is not None and dados_persistidos != st.session_state.dados:
        st.session_state.dados = dados_persistidos

dados = st.session_state.dados

# Validação e consistência de chaves estruturais
if 'TempoLimiteMinutos' not in dados: dados['TempoLimiteMinutos'] = 45
if 'Cronometro' not in dados: dados['Cronometro'] = {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False}
if 'tela_telao' not in st.session_state: st.session_state.tela_telao = "jogos"
if 'HistoricoCampeoes' not in dados: dados['HistoricoCampeoes'] = []

# 🔐 CONTROLE DE ACESSO CORPORATIVO
if 'perfil_usuario' not in st.session_state:
    st.session_state.perfil_usuario = "Público"

# 🃏 CONFIGURAÇÃO E TEMA DA INTERFACE
st.set_page_config(
    page_title="Central de Torneios de Truco - Planta Baixa",
    page_icon="🃏",
    layout="wide"
)

@st.cache_data
def carregar_estilo_premium():
    base_dir = os.path.dirname(__file__)
    if os.path.basename(base_dir) == "pages":
        css_path = os.path.join(os.path.dirname(base_dir), "estilo.css")
    else:
        css_path = os.path.join(base_dir, "estilo.css")
        
    if os.path.exists(css_path):
        with open(css_path, encoding="utf-8") as f:
            return f"<style>{f.read()}</style>"
    return ""

st.markdown(carregar_estilo_premium(), unsafe_allow_html=True)

# Injeção global de CSS com as classes necessárias para renderização correta do Telão e Impressão
estilos_css = ""
if os.path.exists("estilo.css"):
    with open("estilo.css", "r", encoding="utf-8") as f:
        estilos_css = f.read()
    
st.markdown(f"""
<style>
    {estilos_css}
    
    /* Classes de Fallback para Garantir Renderização Visual do Telão no Streamlit */
    .grade-telao-dinamica {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 15px;
        padding: 10px;
    }}
    .mesa-container {{
        background-color: #1e2622;
        border: 1px solid #3d4f45;
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    .mesa-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #3d4f45;
        padding-bottom: 6px;
        margin-bottom: 8px;
        font-weight: bold;
        color: #ffbf00;
    }}
    .mesa-status-pendente {{
        background-color: #8a6d00;
        color: #ffffff;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
    }}
    .mesa-status-concluido {{
        background-color: #1e5a34;
        color: #ffffff;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
    }}
    .mesa-corpo {{
        display: flex;
        flex-direction: column;
        gap: 6px;
    }}
    .jogador-linha {{
        display: flex;
        justify-content: space-between;
        padding: 4px 6px;
        border-radius: 4px;
        background-color: #151b18;
    }}
    .vencedor-destaque {{
        background-color: #244b33 !important;
        border-left: 4px solid #28a745;
        font-weight: bold;
    }}
    .jogador-nome {{
        color: #e0e0e0;
    }}
    .jogador-resultado {{
        color: #a3cfb6;
    }}

    @media print {{
        header, footer, nav, button, [data-testid="stSidebar"], 
        [data-testid="stHeader"], .stTabs, .stButton, div.element-container:has(button),
        div.element-container:has(input), div.element-container:has(select),
        div.element-container:has(textarea), .stRadio,
        .stExpander, .stAlert, h1, h2, h3, p {{ display: none !important; }}
        @page {{ size: 76mm auto; margin: 0mm 2mm 0mm 2mm; }}
        body {{ background-color: #ffffff !important; color: #000000 !important; margin: 0 !important; padding: 0 !important; }}
        .secao-impressao-sumulas {{ display: block !important; width: 72mm !important; background-color: #ffffff !important; color: #000000 !important; }}
        .cartao-sumula-print {{ background-color: #ffffff !important; color: #000000 !important; border-bottom: 2px dashed #000000 !important; padding: 5px 0px 25px 0px !important; page-break-inside: avoid !important; font-family: 'Courier New', Courier, Arial, sans-serif !important; width: 72mm !important; }}
        .tabela-sumula-print {{ width: 100% !important; border-collapse: collapse !important; margin-top: 8px !important; }}
        .tabela-sumula-print th, .tabela-sumula-print td {{ border: 1px solid #000000 !important; padding: 6px 3px !important; text-align: center !important; font-size: 10pt !important; }}
        .texto-dupla-print {{ text-align: left !important; font-size: 9pt !important; font-weight: bold !important; word-break: break-all !important; }}
    }}
    .secao-impressao-sumulas {{ display: none; }}
</style>
""", unsafe_allow_html=True)

# 👑 PAINEL DE AUTENTICAÇÃO E ASSINATURA (SIDEBAR)
st.sidebar.markdown(f"""
    <div class="dev-assinatura-container">
        <div class="dev-titulo">Engenharia de Software</div>
        <div class="dev-nome">🚀 {gerenciador_dados.NOME_CRIADOR}</div>
        <div class="dev-tag">Plataforma Oficial de Competições</div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔐 Controle de Acesso")

perfil_escolhido = st.sidebar.selectbox(
    "Selecione seu Perfil:",
    ["Público", "📺 Modo Telão", "⚙️ Administrador"],
    index=0 if st.session_state.perfil_usuario == "Público" else (1 if st.session_state.perfil_usuario == "Telão" else 2)
)

if perfil_escolhido == "⚙️ Administrador":
    if st.session_state.perfil_usuario != "Administrador":
        senha_admin = st.sidebar.text_input("Senha de Acesso:", type="password")
        if st.sidebar.button("Efetuar Login 🔓"):
            if senha_admin in ["admin123", "truco2026"]:
                st.session_state.perfil_usuario = "Administrador"
                st.sidebar.success("Acesso Concedido!")
                st.rerun()
            else:
                st.sidebar.error("Senha Incorreta!")
    else:
        st.sidebar.success("⚡ Modo Administrador Ativo")
        if st.sidebar.button("Logoff / Sair 🔒"):
            st.session_state.perfil_usuario = "Público"
            st.rerun()
            
elif perfil_escolhido == "📺 Modo Telão":
    st.session_state.perfil_usuario = "Telão"
else:
    st.session_state.perfil_usuario = "Público"

modo_telao = (st.session_state.perfil_usuario == "Telão")


# ==============================================================================
# 🎛️ 2ª PARTE: FUNÇÕES INTERNAS DE RENDERIZAÇÃO E AUDIO
# ==============================================================================
def exibir_podio_arena(lista_classificada):
    if not lista_classificada: return
    
    c1 = lista_classificada[0]['Nome'] if len(lista_classificada) > 0 else "---"
    c2 = lista_classificada[1]['Nome'] if len(lista_classificada) > 1 else "---"
    c3 = lista_classificada[2]['Nome'] if len(lista_classificada) > 2 else "---"
    c4 = lista_classificada[3]['Nome'] if len(lista_classificada) > 3 else "---"
    
    rei_flor_nome = "N/A"
    maior_flor_pontos = -1
    for jogador in lista_classificada:
        if jogador.get('FlorPró', 0) > maior_flor_pontos:
            maior_flor_pontos = jogador.get('FlorPró', 0)
            rei_flor_nome = jogador['Nome']
            
    col_podio, col_flor = st.columns([3, 1])
    
    with col_podio:
        st.markdown(f"""
            <div class="podio-container">
                <div class="podio-card podio-2">
                    <div class="podio-posicao">🥈 2º Lugar</div>
                    <div class="podio-nome">{c2}</div>
                </div>
                <div class="podio-card podio-1">
                    <div class="podio-posicao">🥇 1º Lugar</div>
                    <div class="podio-nome">{c1}</div>
                </div>
                <div class="podio-card podio-3">
                    <div class="podio-posicao">🥉 3º Lugar</div>
                    <div class="podio-nome">{c3}</div>
                </div>
                <div class="podio-card podio-4">
                    <div class="podio-posicao">% 4º Lugar</div>
                    <div class="podio-nome">{c4}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    with col_flor:
        if maior_flor_pontos > 0:
            st.markdown(f"""
                <div class="card-rei-flor">
                    <div class="rei-flor-titulo">🌸 CANTADOR DE FLOR</div>
                    <div class="rei-flor-nome">{rei_flor_nome}</div>
                    <div style="color: #ff4da6; font-size: 0.9rem; font-weight: bold; margin-top:3px;">{maior_flor_pontos} Flores Cantadas</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="card-rei-flor" style="border-color: #555;">
                    <div class="rei-flor-titulo" style="color: #888;">🌸 CANTADOR DE FLOR</div>
                    <div class="rei-flor-nome" style="color: #666;">Nenhuma Lançada</div>
                </div>
            """, unsafe_allow_html=True)

@st.fragment(run_every=1)
def renderizar_cronometro():
    c_dados = dados.get('Cronometro', {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False})
    
    if c_dados['Ativo'] and c_dados['TempoRestanteSegundos'] > 0:
        c_dados['TempoRestanteSegundos'] -= 1
        
    if c_dados['TempoRestanteSegundos'] == 0 and c_dados['Ativo']:
        c_dados['Ativo'] = False
        c_dados['FimRodada'] = True
        dados['Cronometro'] = c_dados
        gerenciador_dados.salvar_dados(dados)
        st.rerun()
        
    segundos_totais = c_dados['TempoRestanteSegundos']
    minutos = segundos_totais // 60
    segundos = segundos_totais % 60
    
    if c_dados.get('FimRodada') or segundos_totais == 0:
        cor_relogio = "#ff4b4b"
        texto_tempo = "00:00 - TUDO É FALTA! 🔔"
        if os.path.exists("alerta.mp3"):
            with open("alerta.mp3", "rb") as f:
                audio_bytes = f.read()
            st.audio(audio_bytes, format="audio/mp3", autoplay=True)
    elif segundos_totais < 300: 
        cor_relogio = "#ffaa00"
        texto_tempo = f"{minutos:02d}:{segundos:02d} - ÚLTIMOS MINUTOS! ⚠️"
    else:
        cor_relogio = "#28a745"
        texto_tempo = f"{minutos:02d}:{segundos:02d}"
        
    tamanho_fonte = "3.8rem" if modo_telao else "3.2rem"
    
    st.markdown(f"""
        <div style="background-color: #121815; border: 2px solid {cor_relogio}; border-radius: 10px; padding: 10px; text-align: center; margin-bottom: 15px; box-shadow: 0 0 15px rgba(0,0,0,0.5);">
            <span style="font-size: {tamanho_fonte}; font-family: 'Courier New', monospace; font-weight: bold; color: {cor_relogio}; line-height: 1.1;">{texto_tempo}</span>
        </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 📺 3ª PARTE: RENDERIZAÇÃO: MODO TELÃO (ROTATIVO DINÂMICO)
# ==============================================================================
if modo_telao:
    titulo_torneio_show = dados.get('NomeTorneio', 'Torneio de Truco')
    rodada_txt = f"• {dados['RodadaAtual']}ª Rodada" if dados['Status'] == 'Em Andamento' else f"• {dados['Status']}"
    
    st.markdown(f"""
        <div style='text-align: center; margin-bottom: 5px;'>
            <h1 style='color: #ffbf00 !important; margin: 0; font-size: 2.2rem;'>🃏 {titulo_torneio_show} <span style='color:#a3cfb6; font-size: 1.6rem;'>{rodada_txt}</span></h1>
        </div>
    """, unsafe_allow_html=True)
    
    if dados['Status'] == 'Em Andamento':
        renderizar_cronometro()
        
    if st.session_state.tela_telao == "jogos":
        st.markdown("<h3 style='color: #ffbf00; margin-top:0; margin-bottom:10px; text-align:center;'>⚔️ CONFRONTOS DA RODADA AO VIVO</h3>", unsafe_allow_html=True)
        if 'RodadaAtual' in dados and 'Rodadas' in dados and len(dados['Rodadas']) > 0:
            rodada_atual_num = dados['RodadaAtual']
            rodada_atual = next((r for r in dados['Rodadas'] if r.get('Numero') == rodada_atual_num), None)
            
            if rodada_atual and 'Mesas' in rodada_atual:
                mesas = rodada_atual.get('Mesas', [])
                html_grade = "<div class='grade-telao-dinamica'>"
                
                for m in mesas:
                    status_txt = "EM ANDAMENTO" if m.get('Status') == 'Pendente' else "CONCLUÍDO"
                    status_classe = "mesa-status-concluido" if m.get('Status') == 'Concluído' else "mesa-status-pendente"
                    vencedor_j1 = "vencedor-destaque" if (m.get('Status') == 'Concluído' and int(m.get('SetsJ1', 0)) > int(m.get('SetsJ2', 0))) else ""
                    vencedor_j2 = "vencedor-destaque" if (m.get('Status') == 'Concluído' and int(m.get('SetsJ2', 0)) > int(m.get('SetsJ1', 0))) else ""
                    
                    html_grade += f"""
                    <div class="mesa-container">
                        <div class="mesa-header">
                            <span>🚨 Mesa {m.get('Mesa')}</span>
                            <span class="{status_classe}">{status_txt}</span>
                        </div>
                        <div class="mesa-corpo">
                            <div class="jogador-linha {vencedor_j1}">
                                <span class="jogador-nome">👤 {m.get('Jogador1')}</span>
                                <span class="jogador-resultado">{m.get('SetsJ1')}S ({m.get('TentosJ1')}T)</span>
                            </div>
                            <div class="jogador-linha {vencedor_j2}">
                                <span class="jogador-nome">👤 {m.get('Jogador2')}</span>
                                <span class="jogador-resultado">{m.get('SetsJ2')}S ({m.get('TentosJ2')}T)</span>
                            </div>
                        </div>
                    </div>
                    """
                html_grade += "</div>"
                st.markdown(html_grade, unsafe_allow_html=True)
            else:
                st.info("Nenhum jogo ativo nesta rodada.")
        else:
            st.info("Aguardando definição das rodadas.")
            
        time.sleep(12)
        st.session_state.tela_telao = "classificacao"
        st.rerun()
        
    else:
        st.markdown("<h3 style='color: #ffbf00; margin-top:0; margin-bottom:10px; text-align:center;'>📊 CLASSIFICAÇÃO GERAL E EM DESTAQUE</h3>", unsafe_allow_html=True)
        if dados.get('Jogadores'):
            lista_classificada = motor_truco.processar_classificacao(dados)
            exibir_podio_arena(lista_classificada)
            
            df_class = pd.DataFrame(lista_classificada)
            df_class.index = [f"{i+1}º" for i in range(len(df_class))]
            df_visual = df_class.rename(columns={
                'Nome': 'Dupla / Competidor', 'Pts': 'Pontos', 'Vit': 'Vitórias',
                'SaldoSets': 'Saldo Sets', 'SaldoTent': 'Saldo Tentos', 'FlorPró': 'Flores', 'Bukes': 'Buchholz'
            })
            st.dataframe(df_visual[['Dupla / Competidor', 'Pontos', 'Vitórias', 'Saldo Sets', 'Saldo Tentos', 'Flores', 'Buchholz']], use_container_width=True, height=280)
        else:
            st.warning("Nenhum competidor cadastrado.")
            
        time.sleep(8)
        st.session_state.tela_telao = "jogos"
        st.rerun()

# ==============================================================================
# 🏢 4ª PARTE: RENDERIZAÇÃO: MODO INTERATIVO (PÚBLICO E OPERACIONAL)
# ==============================================================================
else:
    st.markdown("<h1 style='text-align: center; color: #ffbf00 !important;'>🃏 Central de Torneios de Truco</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 1rem; color: #a3cfb6 !important;'>Engine de Torneio Desenvolvida por <b>{gerenciador_dados.NOME_CRIADOR}</b></p>", unsafe_allow_html=True)

    ip_local = gerenciador_dados.obter_ip_da_rede()
    st.info(f"🌐 **Rede Local Ativa:** Acesse por outros dispositivos usando: `http://{ip_local}:8501`")

    # CONSTRUÇÃO DINÂMICA E SEGURA DAS ABAS
    abas_lista = ["📊 Classificação Geral"]
    
    if dados['Status'] == 'Configuração':
        abas_lista.append("📝 Inscrição Online")
        
    if st.session_state.perfil_usuario == "Administrador":
        # Lançar mesas só aparece se o torneio já saiu da fase de configuração
        if dados['Status'] != 'Configuração' and len(dados.get('Rodadas', [])) > 0:
            abas_lista.append("⚔️ Lançar Mesas")
        abas_lista.append("⚙️ Painel de Controle Admin")
        
    abas_lista.append("🏆 Galeria de Campeões")
    abas_criadas = st.tabs(abas_lista)
    aba_index = 0
    
    # --- 1. ABA: CLASSIFICAÇÃO GERAL ---
    with abas_criadas[aba_index]:
        st.markdown("<h2 style='color: #ffbf00 !important;'>📊 Classificação Estratégica</h2>", unsafe_allow_html=True)
        if dados['Status'] != 'Configuração' and dados.get('Jogadores'):
            lista_classificada = motor_truco.processar_classificacao(dados)
            st.markdown("### 🏆 Liderança Atual e Destaques")
            exibir_podio_arena(lista_classificada)
            
            df_class = pd.DataFrame(lista_classificada)
            df_class.index = [f"{i+1}º" for i in range(len(df_class))]
            df_visual = df_class.rename(columns={
                'Nome': 'Jogador/Dupla', 'Entidade': 'Entidade/Equipe', 'Pts': 'Pontos', 'Vit': 'Vitórias',
                'SaldoSets': 'Saldo Sets', 'SetsPró': 'Sets Pró', 'SaldoTent': 'Saldo Tentos', 'TentPró': 'Tentos Pró',
                'SaldoFlor': 'Saldo Flores', 'FlorPró': 'Flores Pró', 'Bukes': 'Buchholz', 'Jogos': 'Partidas'
            })
            st.dataframe(df_visual[['Jogador/Dupla', 'Entidade/Equipe', 'Pontos', 'Vitórias', 'Saldo Sets', 'Sets Pró', 'Saldo Tentos', 'Tentos Pró', 'Saldo Flores', 'Flores Pró', 'Buchholz', 'Partidas']], use_container_width=True)
        else:
            st.warning("Torneio em fase de montagem de chaves. Veja a lista dos competidores já confirmados:")
            if dados.get('Jogadores'):
                df_previa = pd.DataFrame(dados['Jogadores']).rename(columns={'Nome': 'Jogador / Dupla', 'Entidade': 'Entidade / Clube'})
                st.dataframe(df_previa, use_container_width=True)
            else:
                st.info("Nenhum competidor inscrito até o momento.")
    aba_index += 1

    # --- 2. ABA: INSCRIÇÃO ONLINE (PÚBLICA) ---
    if "📝 Inscrição Online" in abas_lista:
        with abas_criadas[aba_index]:
            st.markdown("<h2 style='color: #ffbf00 !important;'>📝 Formulário de Inscrição Oficial</h2>", unsafe_allow_html=True)
            with st.form("form_auto_inscricao", clear_on_submit=True):
                name_atleta = st.text_input("Nome do Atleta ou da Dupla:").strip().upper()
                entidade_atleta = st.text_input("Sua Entidade / Equipe / Clube:").strip().upper()
                botao_enviar = st.form_submit_button("Enviar Minha Inscrição 🚀")
                if botao_enviar:
                    if not name_atleta: 
                        st.error("Preencha o campo do Nome.")
                    else:
                        nomes_existentes = [j['Nome'] for j in dados.get('Jogadores', [])]
                        if name_atleta in nomes_existentes: 
                            st.warning("Jogador/Dupla já está na lista!")
                        else:
                            entidade_final = entidade_atleta if entidade_atleta else "SEM ENTIDADE"
                            dados['Jogadores'].append({'Nome': name_atleta, 'Entidade': entidade_final})
                            gerenciador_dados.salvar_dados(dados)
                            st.success("Inscrição efetuada com sucesso!")
                            st.rerun()
        aba_index += 1


# ==============================================================================
# 🖨️ 5ª PARTE: ABA: LANÇAR MESAS & IMPRESSÃO TÉRMICA (EXCLUSIVA ADMIN)
# ==============================================================================
    if "⚔️ Lançar Mesas" in abas_lista:
        with abas_criadas[aba_index]:
            renderizar_cronometro()
            rodada_atual_num = dados['RodadaAtual']
            rodadas_lista = dados.get('Rodadas', [])
            rodada_atual = next((r for r in rodadas_lista if r['Numero'] == rodada_atual_num), None)
            
            if rodada_atual:
                col_tit, col_imp = st.columns([3, 1])
                with col_tit: 
                    st.markdown(f"<h2 style='color: #ffbf00 !important;'>⚔️ Gerenciamento da {rodada_atual_num}ª Rodada</h2>", unsafe_allow_html=True)
                with col_imp:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🖨️ IMPRIMIR SÚMULAS (ELGIN I9)", use_container_width=True):
                        st.components.v1.html("<script>window.print();</script>", height=0, width=0)
                
                mesas = rodada_atual.get('Mesas', [])
                
                html_impressao = f"<div class='secao-impressao-sumulas'>"
                for m in mesas:
                    if m['Jogador1'] == "CHAPÉU" or m['Jogador2'] == "CHAPÉU": continue 
                    html_impressao += f"""
                    <div class='cartao-sumula-print'>
                        <div style='text-align:center; font-weight:bold; font-size:11pt; border-bottom:1px solid #000;'>{dados.get('NomeTorneio', 'TORNEIO DE TRUCO')}</div>
                        <div style='display:flex; justify-content:space-between; margin-top:5px; font-weight:bold; font-size:11pt;'>
                            <span>🎴 MESA {m['Mesa']}</span><span>{rodada_atual_num}a RODADA</span>
                        </div>
                        <table class='tabela-sumula-print'>
                            <thead><tr><th style='width: 50%; text-align:left;'>COMPETIDOR</th><th style='width:16%;'>SET</th><th style='width:16%;'>TT</th><th style='width:18%;'>FLOR</th></tr></thead>
                            <tbody>
                                <tr><td class='texto-dupla-print'>{m['Jogador1']}</td><td>[ &nbsp;]</td><td>[ &nbsp; ]</td><td>[ &nbsp; ]</td></tr>
                                <tr><td class='texto-dupla-print'>{m['Jogador2']}</td><td>[ &nbsp;]</td><td>[ &nbsp; ]</td><td>[ &nbsp; ]</td></tr>
                            </tbody>
                        </table>
                        <div style='margin-top:12px; font-size:8pt; font-weight:bold; text-align:left; line-height:1.4;'>✍️ Ass: _______________________________<br>Juiz: _________________</div>
                    </div>
                    """
                html_impressao += "</div>"
                st.markdown(html_impressao, unsafe_allow_html=True)
                
                col_mesa1, col_mesa2 = st.columns(2)
                for idx, m in enumerate(mesas):
                    col_alvo = col_mesa1 if idx % 2 == 0 else col_mesa2
                    with col_alvo:
                        status_classe = "mesa-status-concluido" if m['Status'] == 'Concluído' else "mesa-status-pendente"
                        vencedor_j1 = "vencedor-destaque" if (m['Status'] == 'Concluído' and int(m['SetsJ1']) > int(m['SetsJ2'])) else ""
                        vencedor_j2 = "vencedor-destaque" if (m['Status'] == 'Concluído' and int(m['SetsJ2']) > int(m['SetsJ1'])) else ""
                        
                        st.markdown(f"""
                            <div class="mesa-container">
                                <div class="mesa-header">
                                    <span>🎴 Mesa {m['Mesa']}</span>
                                    <span class="{status_classe}">{m['Status'].upper()}</span>
                                </div>
                                <div class="mesa-corpo">
                                    <div class="jogador-linha {vencedor_j1}">
                                        <span class="jogador-nome">👤 {m['Jogador1']}</span>
                                        <span class="jogador-resultado">{m['SetsJ1']} Set(s) ({m['TentosJ1']} T / {m['FloresJ1']} F)</span>
                                    </div>
                                    <div class="jogador-linha {vencedor_j2}">
                                        <span class="jogador-nome">👤 {m['Jogador2']}</span>
                                        <span class="jogador-resultado">{m['SetsJ2']} Set(s) ({m['TentosJ2']} T / {m['FloresJ2']} F)</span>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if m['Jogador1'] == "CHAPÉU" or m['Jogador2'] == "CHAPÉU": continue
                            
                        with st.expander(f"📝 Lançar Placar - Mesa {m['Mesa']}"):
                            form_key = f"form_mesa_{m['Mesa']}_{rodada_atual_num}"
                            opcoes_sets = ["Aguardando...", f"{m['Jogador1']} 2 x 0", f"{m['Jogador2']} 2 x 0", f"{m['Jogador1']} 2 x 1", f"{m['Jogador2']} 2 x 1"]
                            escolha_set = st.selectbox("Qual o placar em Sets?", opcoes_sets, key=f"sel_{form_key}")
                            
                            t1_raw, t2_raw = "0", "0"
                            if "2 x 1" in escolha_set:
                                col_t1, col_t2 = st.columns(2)
                                with col_t1: t1_raw = st.text_input(f"Tentos de {m['Jogador1']}", value=str(m.get('TentosJ1', 0)), key=f"t1_{form_key}")
                                with col_t2: t2_raw = st.text_input(f"Tentos de {m['Jogador2']}", value=str(m.get('TentosJ2', 0)), key=f"t2_{form_key}")
                            
                            col_f1, col_f2 = st.columns(2)
                            with col_f1: f1_num = st.number_input(f"🌸 Flores de {m['Jogador1']}", min_value=0, value=int(m.get('FloresJ1', 0)), step=1, key=f"f1_{form_key}")
                            with col_f2: f2_num = st.number_input(f"🌸 Flores de {m['Jogador2']}", min_value=0, value=int(m.get('FloresJ2', 0)), step=1, key=f"f2_{form_key}")
                            
                            if st.button("Confirmar e Salvar Mesa", key=f"btn_{form_key}"):
                                if escolha_set != "Aguardando...":
                                    alvo = dados['Rodadas'][dados['RodadaAtual'] - 1]['Mesas'][idx]
                                    alvo['Status'] = 'Concluído'
                                    alvo['FloresJ1'] = f1_num
                                    alvo['FloresJ2'] = f2_num
                                    try: t1_int, t2_int = int(t1_raw), int(t2_raw)
                                    except Exception: t1_int, t2_int = 0, 0
                                    
                                    if escolha_set.startswith(alvo['Jogador1']):
                                        alvo['SetsJ1'], alvo['SetsJ2'] = 2, (1 if "2 x 1" in escolha_set else 0)
                                        if "2 x 0" in escolha_set: alvo['TentosJ1'], alvo['TentosJ2'] = 24, 0
                                        else: alvo['TentosJ1'], alvo['TentosJ2'] = t1_int, t2_int
                                    else:
                                        alvo['SetsJ1'], alvo['SetsJ2'] = (1 if "2 x 1" in escolha_set else 0), 2
                                        if "2 x 0" in escolha_set: alvo['TentosJ1'], alvo['TentosJ2'] = 0, 24
                                        else: alvo['TentosJ1'], alvo['TentosJ2'] = t1_int, t2_int
                                        
                                    gerenciador_dados.salvar_dados(dados)
                                    st.success(f"Mesa {m['Mesa']} Lançada com Sucesso!")
                                    st.rerun()
            else:
                st.info("Nenhuma rodada gerada até o momento.")
        aba_index += 1


# ==============================================================================
# ⚙️ 6ª PARTE: PAINEL DE CONTROLE ADMIN & VIRADA DE RODADA DO SISTEMA SUÍÇO
# ==============================================================================
    if "⚙️ Painel de Controle Admin" in abas_lista:
        with abas_criadas[aba_index]:
            st.markdown("<h2 style='color: #ffbf00 !important;'>⚙️ Painel do Diretor do Torneio</h2>", unsafe_allow_html=True)
            
            if dados['Status'] == 'Configuração':
                st.markdown("### 🏷️ Definições Gerais do Campeonato")
                nome_torneio_input = st.text_input("Nome Principal da Competição:", value=dados.get('NomeTorneio', ''))
                tempo_limite = st.number_input("Tempo do Cronômetro por Rodada (minutos):", min_value=5, max_value=120, value=int(dados.get('TempoLimiteMinutos', 45)))
                
                st.markdown("---")
                st.markdown("### 👥 Gerenciador Ativo de Inscrições")
                
                opcao_cadastro = st.radio("Selecione o método operacional de cadastro:", ["Individual Manual", "🚀 Importação Rápida em Lote (Copia e Cola)"], horizontal=True)
                
                if opcao_cadastro == "Individual Manual":
                    col_cad1, col_cad2 = st.columns(2)
                    with col_cad1:
                        novo_nome = st.text_input("Nome do Competidor / Identificação da Dupla:", key="cad_nome").strip().upper()
                    with col_cad2:
                        nova_ent = st.text_input("Entidade / Clube / Cidade de Origem:", key="cad_ent").strip().upper()
                        
                    if st.button("📥 Cadastrar Competidor Individual"):
                        if not novo_nome:
                            st.error("Erro: O campo de nome não pode ficar em branco.")
                        else:
                            nomes_existentes = [j['Nome'] for j in dados.get('Jogadores', [])]
                            if novo_nome in nomes_existentes:
                                st.warning(f"Aviso: '{novo_nome}' já se encontra cadastrado no banco.")
                            else:
                                ent_f = nova_ent if nova_ent else "MESA"
                                dados['Jogadores'].append({'Nome': novo_nome, 'Entidade': ent_f})
                                gerenciador_dados.salvar_dados(dados)
                                st.success(f"🎉 '{novo_nome}' integrado à lista oficial!")
                                st.rerun()
                                
                else:
                    st.markdown("> **Instruções do Lote:** Copie uma lista inteira de nomes (do Bloco de Notas ou WhatsApp) e cole no campo abaixo. Insira **um competidor por linha**.")
                    entidade_lote = st.text_input("Entidade / Cidade padrão atribuída a este lote:", value="MESA", key="ent_lote").strip().upper()
                    texto_lote = st.text_area("Cole as linhas com os nomes dos competidores aqui:", height=180, placeholder="DUPLA ALVES & GOMES\nMARCOS SOUZA\nTRUQUEIROS DA COSTA")
                    
                    if st.button("⚡ Executar Processamento e Cadastro em Massa"):
                        if not texto_lote.strip():
                            st.error("Erro: Nenhuma informação foi detectada na caixa de texto.")
                        else:
                            linhas = [l.strip().upper() for l in texto_lote.split("\n") if l.strip()]
                            cadastrados_agora = 0
                            duplicados_pulados = 0
                            nomes_existentes = [j['Nome'] for j in dados.get('Jogadores', [])]
                            
                            for linha in linhas:
                                if linha in nomes_existentes:
                                    duplicados_pulados += 1
                                else:
                                    dados['Jogadores'].append({'Nome': linha, 'Entidade': entidade_lote})
                                    nomes_existentes.append(linha)
                                    cadastrados_agora += 1
                                    
                            if cadastrados_agora > 0:
                                gerenciador_dados.salvar_dados(dados)
                                st.success(f"🔥 Carga Executada! {cadastrados_agora} novos competidores foram inseridos!")
                            if duplicados_pulados > 0:
                                st.warning(f"⚠️ {duplicados_pulados} registros ignorados por duplicidade estrutural.")
                            if cadastrados_agora > 0:
                                time.sleep(1)
                                st.rerun()

                st.markdown("---")
                if st.button("🚀 BLOQUEAR INSCRIÇÕES E GERAR CHAVE (START)"):
                    if len(dados.get('Jogadores', [])) < 2:
                        st.error("Erro Crítico: É obrigatório ter no mínimo 2 competidores para iniciar o chaveamento.")
                    else:
                        # Inicialização analítica preventiva para o Motor Suíço
                        for j in dados['Jogadores']:
                            j['Pts'] = j.get('Pts', 0)
                            j['Vit'] = j.get('Vit', 0)
                            j['SaldoSets'] = j.get('SaldoSets', 0)
                            j['SetsPró'] = j.get('SetsPró', 0)
                            j['SaldoTent'] = j.get('SaldoTent', 0)
                            j['TentPró'] = j.get('TentPró', 0)
                            j['SaldoFlor'] = j.get('SaldoFlor', 0)
                            j['FlorPró'] = j.get('FlorPró', 0)
                            j['Bukes'] = j.get('Bukes', 0)
                            j['Jogos'] = j.get('Jogos', 0)

                        dados['NomeTorneio'] = nome_torneio_input if nome_torneio_input else "Torneio de Truco"
                        dados['TempoLimiteMinutos'] = tempo_limite
                        dados['Status'] = 'Em Andamento'
                        dados['RodadaAtual'] = 1
                        dados['Cronometro'] = {
                            'TempoRestanteSegundos': tempo_limite * 60,
                            'Ativo': True,
                            'FimRodada': False
                        }
                        
                        dados['Rodadas'] = []
                        primeira_rodada = motor_truco.gerar_rodada_suica(dados, 1)
                        dados['Rodadas'].append(primeira_rodada)
                        
                        gerenciador_dados.salvar_dados(dados)
                        st.success("Campeonato Oficial Iniciado! Chaves do Sistema Suíço Geradas.")
                        st.rerun()
                        
                st.markdown("### 👥 Gerenciador Analítico de Inscritos (Exclusão)")
                if dados.get('Jogadores'):
                    for idx_j, jog in enumerate(dados['Jogadores']):
                        col_j1, col_j2 = st.columns([3, 1])
                        with col_j1: st.write(f"👤 {jog['Nome']} — 🏢 {jog['Entidade']}")
                        with col_j2:
                            if st.button("❌ Remover", key=f"rem_{idx_j}"):
                                dados['Jogadores'].pop(idx_j)
                                gerenciador_dados.salvar_dados(dados)
                                st.rerun()
                                
            elif dados['Status'] == 'Em Andamento':
                st.info("🔒 **Inscrições Trancadas:** O torneio está ativo. O quadro de jogadores não pode receber alterações para não comprometer as somas do cálculo do Buchholz.")
                st.markdown(f"### 🛡️ Cronômetro da Arena — Rodada {dados['RodadaAtual']}")
                c_ativo = dados['Cronometro'].get('Ativo', False)
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("⏸️ Congelar Cronômetro" if c_ativo else "▶️ Ativar Cronômetro"):
                        dados['Cronometro']['Ativo'] = not c_ativo
                        gerenciador_dados.salvar_dados(dados)
                        st.rerun()
                with col_btn2:
                    if st.button("🔄 Reiniciar Tempo Padrão"):
                        dados['Cronometro']['TempoRestanteSegundos'] = dados['TempoLimiteMinutos'] * 60
                        dados['Cronometro']['FimRodada'] = False
                        gerenciador_dados.salvar_dados(dados)
                        st.rerun()
                
                st.markdown("---")
                rodadas_lista = dados.get('Rodadas', [])
                rodada_atual = next((r for r in rodadas_lista if r['Numero'] == dados['RodadaAtual']), None)
                todas_concluidas = True
                if rodada_atual:
                    for m in rodada_atual.get('Mesas', []):
                        if m['Status'] != 'Concluído': todas_concluidas = False
                
                if todas_concluidas:
                    if st.button("🏁 CONCLUIR RODADA E RODAR NOVO EMPARELHAMENTO"):
                        dados['RodadaAtual'] += 1
                        nova_rodada = motor_truco.gerar_rodada_suica(dados, dados['RodadaAtual'])
                        if nova_rodada is None:
                            dados['Status'] = 'Finalizado'
                            classificacao = motor_truco.processar_classificacao(dados)
                            if classificacao:
                                dados['HistoricoCampeoes'].append({
                                    'Torneio': dados['NomeTorneio'],
                                    'Campeao': classificacao[0]['Nome'],
                                    'Data': datetime.now().strftime("%d/%m/%Y")
                                })
                        else:
                            dados['Rodadas'].append(nova_rodada)
                            dados['Cronometro'] = {
                                'TempoRestanteSegundos': dados['TempoLimiteMinutos'] * 60,
                                'Ativo': True,
                                'FimRodada': False
                            }
                        gerenciador_dados.salvar_dados(dados)
                        st.rerun()
                else:
                    st.warning("🔒 Bloqueio de Próxima Fase: There are pending tables in this round that need to be filled before advancing.")
                    
            if st.button("🚨 PURGAR BANCO DE DADOS (Zerar Todo o Sistema)"):
                gerenciador_dados.limpar_banco_dados()
                if 'dados' in st.session_state: del st.session_state.dados
                st.rerun()
        aba_index += 1

    # --- 5. ABA: GALERIA DE CAMPEÕES ---
    with abas_criadas[aba_index]:
        st.markdown("<h2 style='color: #ffbf00 !important;'>🏆 Histórico de Grandes Campeões</h2>", unsafe_allow_html=True)
        historico = dados.get('HistoricoCampeoes', [])
        if historico:
            for h in historico:
                st.markdown(f"🏅 **{h['Torneio']}** | Campeão Invicto: `{h['Campeao']}` — 🗓️ Data de Conclusão: {h['Data']}", unsafe_allow_html=True)
        else:
            st.info("Nenhum torneio arquivado no banco de dados local.")
