import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

import gerenciador_dados
import motor_truco

# ==============================================================================
# 💾 INICIALIZAÇÃO DE DADOS PERSISTENTES (ANTI-RESET)
# ==============================================================================
if 'dados' not in st.session_state:
    # 🔒 Só lê do arquivo UMA VEZ quando a página carrega do zero
    dados_carregados = gerenciador_dados.carregar_dados()

    # BLINDAGEM: Se o arquivo vier vazio ou der erro, usa um dicionário padrão
    if not dados_carregados or not isinstance(dados_carregados, dict):
        dados_carregados = {'Mesas': {}, 'Status': 'Em Andamento', 'RodadaAtual': 1}

    st.session_state['dados'] = dados_carregados

# Puxa sempre da memória estável do navegador para não sobrecarregar o arquivo
dados = st.session_state['dados']

# Garante que o dicionário do Cronômetro exista com segurança dentro de dados
if 'Cronometro' not in dados:
    dados['Cronometro'] = {
        'TempoRestanteSegundos': 3300,  # 55 minutos padrão
        'Ativo': False,
        'FimRodada': False
    }
# 🃏 CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Central de Torneios de Truco - Planta Baixa",
    page_icon="🃏",
    layout="wide"
)
@st.cache_data
def carregar_estilo_premium():
    """Lê o CSS apenas uma vez e guarda na memória para evitar que a tela pisque"""
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

# =========================================================
# 🔒 ARQUITETURA DE PERSISTÊNCIA INQUEBRÁVEL (FIM DOS RESETS)
# =========================================================
# Sempre tenta ler o arquivo físico primeiro. Se existir, ignora o reset de memória.
dados_persistidos = gerenciador_dados.carregar_dados()

if 'dados' not in st.session_state:
    if dados_persistidos is not None:
        st.session_state.dados = dados_persistidos
    else:
        st.session_state.dados = {
            'NomeTorneio': '', 'Status': 'Configuração',
            'Jogadores': [], 'RodadaAtual': 0, 'Rodadas': [],
            'TempoLimiteMinutos': 45,  
            'Cronometro': {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False}
        }
else:
    # Se a sessão existe mas o arquivo em disco foi atualizado por fora, sincroniza
    if dados_persistidos is not None and dados_persistidos != st.session_state.dados:
        st.session_state.dados = dados_persistidos

dados = st.session_state.dados

# Garante chaves essenciais
if 'TempoLimiteMinutos' not in dados: dados['TempoLimiteMinutos'] = 45
if 'Cronometro' not in dados: dados['Cronometro'] = {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False}
if 'tela_telao' not in st.session_state: st.session_state.tela_telao = "jogos"

# =========================================================
# 👑 PAINEL DE ASSINATURA DO DESENVOLVEDOR (SIDEBAR)
# =========================================================
st.sidebar.markdown(f"""
    <div class="dev-assinatura-container">
        <div class="dev-titulo">Engenharia de Software</div>
        <div class="dev-nome">🚀 {gerenciador_dados.NOME_CRIADOR}</div>
        <div class="dev-tag">Plataforma Oficial de Competições</div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🖥️ Controle de Exibição")
modo_telao = st.sidebar.checkbox("📺 ATIVAR MODO TELÃO (TV / PROJETOR)", value=False)

# Injeção das regras de estilo CSS
if os.path.exists("estilo.css"):
    with open("estilo.css", "r", encoding="utf-8") as f:
        estilos_css = f.read()
    
    # Adiciona classe para travar tela se o modo telão estiver ativo
    classe_telao = "class='modo-telao-ativo'" if modo_telao else ""
    st.markdown(f"""
    <style>
        {estilos_css}
        @media print {{
            header, footer, nav, button, [data-testid="stSidebar"], 
            [data-testid="stHeader"], .stTabs, .stButton, div.element-container:has(button),
            div.element-container:has(input), div.element-container:has(select),
            .stExpander, .stAlert, h1, p {{ display: none !important; }}
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


# =========================================================
# FUNÇÃO AUXILIAR: RENDERIZAR PODIO DOS REIS DO TRUCO
# =========================================================
def exibir_podio_arena(lista_classificada):
    if not lista_classificada: return
    
    # Captura os 4 primeiros colocados
    c1 = lista_classificada[0]['Nome'] if len(lista_classificada) > 0 else "---"
    c2 = lista_classificada[1]['Nome'] if len(lista_classificada) > 1 else "---"
    c3 = lista_classificada[2]['Nome'] if len(lista_classificada) > 2 else "---"
    c4 = lista_classificada[3]['Nome'] if len(lista_classificada) > 3 else "---"
    
    # Calcula o Rei da Flor (Maior FlorPró)
    rei_flor_nome = "N/A"
    maior_flor_pontos = -1
    for jogador in lista_classificada:
        if jogador['FlorPró'] > maior_flor_pontos:
            maior_flor_pontos = joker = jogador['FlorPró']
            rei_flor_nome = jogador['Nome']
            
    col_podio, col_flor = st.columns([3, 1])
    
    with col_podio:
        st.markdown(f"""
            <div class="podio-container">
                <div class="podio-card podio-1">
                    <div class="podio-posicao">🥇 1º Lugar</div>
                    <div class="podio-nome">{c1}</div>
                </div>
                <div class="podio-card podio-2">
                    <div class="podio-posicao">🥈 2º Lugar</div>
                    <div class="podio-nome">{c2}</div>
                </div>
                <div class="podio-card podio-3">
                    <div class="podio-posicao">🥉 3º Lugar</div>
                    <div class="podio-nome">{c3}</div>
                </div>
                <div class="podio-card podio-4">
                    <div class="podio-posicao">🏅 4º Lugar</div>
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


# =========================================================
# ⏱️ CRONÔMETRO
# =========================================================
@st.fragment(run_every=1)
def renderizar_cronometro():
    c_dados = dados.get('Cronometro', {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False})
    
    # Se o cronômetro estiver ativo, reduz 1 segundo a cada passada automática do fragmento
    if c_dados['Ativo'] and c_dados['TempoRestanteSegundos'] > 0:
        c_dados['TempoRestanteSegundos'] -= 1
        
    if c_dados['TempoRestanteSegundos'] == 0:
            c_dados['Ativo'] = False
            c_dados['FimRodada'] = True
            dados['Cronometro'] = c_dados
            gerenciador_dados.salvar_dados(dados)
            st.rerun()
        
    segundos_totais = c_dados['TempoRestanteSegundos']
    minutos = segundos_totais // 60
    segundos = segundos_totais % 60
    
    if c_dados['FimRodada'] or segundos_totais == 0:
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
# 📺 RENDERIZAÇÃO: MODO TELÃO (100% VISUAL INTERATIVO ANTI-ROLAGEM)
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
        rodada_atual_num = dados['RodadaAtual']
        rodada_atual = next((r for r in dados['Rodadas'] if r['Numero'] == rodada_atual_num), None)
        
        if rodada_atual:
            mesas = rodada_atual.get('Mesas', [])
            html_grade = "<div class='grade-telao-dinamica'>"
            
            for m in mesas:
                status_txt = "EM ANDAMENTO" if m['Status'] == 'Pendente' else "CONCLUÍDO"
                status_classe = "mesa-status-concluido" if m['Status'] == 'Concluído' else "mesa-status-pendente"
                vencedor_j1 = "vencedor-destaque" if (m['Status'] == 'Concluído' and int(m['SetsJ1']) > int(m['SetsJ2'])) else ""
                vencedor_j2 = "vencedor-destaque" if (m['Status'] == 'Concluído' and int(m['SetsJ2']) > int(m['SetsJ1'])) else ""
                
                html_grade += f"""
                <div class="mesa-container">
                    <div class="mesa-header">
                        <span>🚨 Mesa {m['Mesa']}</span>
                        <span class="{status_classe}">{status_txt}</span>
                    </div>
                    <div class="mesa-corpo">
                        <div class="jogador-linha {vencedor_j1}">
                            <span class="jogador-nome">👤 {m['Jogador1']}</span>
                            <span class="jogador-resultado">{m['SetsJ1']}S ({m['TentosJ1']}T)</span>
                        </div>
                        <div class="jogador-linha {vencedor_j2}">
                            <span class="jogador-nome">👤 {m['Jogador2']}</span>
                            <span class="jogador-resultado">{m['SetsJ2']}S ({m['TentosJ2']}T)</span>
                        </div>
                    </div>
                </div>
                """
            
            html_grade += "</div>"
            st.markdown(html_grade, unsafe_allow_html=True)
        else:
            st.info("Nenhum jogo ativo nesta rodada.")
            
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
# 🛠️ RENDERIZAÇÃO: MODO ADMINISTRADOR TRADICIONAL
# ==============================================================================
else:
    st.markdown("<h1 style='text-align: center; color: #ffbf00 !important;'>🃏 Central de Torneios de Truco</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 1rem; color: #a3cfb6 !important;'>Engine de Torneio Desenvolvida por <b>{gerenciador_dados.NOME_CRIADOR}</b></p>", unsafe_allow_html=True)

    ip_local = gerenciador_dados.obter_ip_da_rede()
    if dados['Status'] == 'Configuração': st.info(f"📢 **Inscrições Abertas!** Link das inscrições: `http://{ip_local}:8501`")
    else: st.info(f"🌐 **Rede Local Ativa:** Endereço do telão da arena: `http://{ip_local}:8501`")

    if dados['Status'] == 'Configuração': abas = ["📝 Inscrição Online", "📊 Classificação Geral", "⚙️ Painel de Controle", "🏆 Galeria de Campeões"]
    else: abas = ["📊 Classificação Geral", "⚔️ Mesas & Lançamento", "⚙️ Painel de Controle", "🏆 Galeria de Campeões"]

    abas_criadas = st.tabs(abas)

    if dados['Status'] == 'Configuração':
        aba_inscricao, aba1, aba3, aba4 = abas_criadas
        aba2 = None
    else:
        aba_inscricao = None
        aba1, aba2, aba3, aba4 = abas_criadas

    # --- ABA: INSCRIÇÃO PÚBLICA ---
    if aba_inscricao is not None:
        with aba_inscricao:
            st.markdown("<h2 style='color: #ffbf00 !important;'>📝 Formulário de Inscrição Oficial</h2>", unsafe_allow_html=True)
            with st.form("form_auto_inscricao", clear_on_submit=True):
                nome_atleta = st.text_input("Nome do Atleta ou da Dupla:").strip().upper()
                entidade_atleta = st.text_input("Sua Entidade / Equipe / Clube:").strip().upper()
                botao_enviar = st.form_submit_button("Enviar Minha Inscrição 🚀")
                if botao_enviar:
                    if not nome_atleta: st.error("Preencha o campo do Nome.")
                    else:
                        nomes_existentes = [j['Nome'] for j in dados.get('Jogadores', [])]
                        if nome_atleta in nomes_existentes: st.warning("Jogador já inscrito!")
                        else:
                            entidade_final = entidade_atleta if entidade_atleta else "SEM ENTIDADE"
                            dados['Jogadores'].append({'Nome': nome_atleta, 'Entidade': entidade_final})
                            gerenciador_dados.salvar_dados(dados)
                            st.success("Inscrito com sucesso!")
                            st.rerun()

    # --- ABA 1: CLASSIFICAÇÃO GERAL ---
    with aba1:
        st.markdown("<h2 style='color: #ffbf00 !important;'>📊 Classificação Estratégica</h2>", unsafe_allow_html=True)
        if dados['Status'] != 'Configuração' and dados.get('Jogadores'):
            lista_classificada = motor_truco.processar_classificacao(dados)
            
            # Pódio ativo na aba administrativa também
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
            st.warning("Aguardando início do torneio.")
            if dados.get('Jogadores'):
                df_previa = pd.DataFrame(dados['Jogadores']).rename(columns={'Nome': 'Jogador / Dupla', 'Entidade': 'Entidade / Clube'})
                st.dataframe(df_previa, use_container_width=True)

    # --- ABA 2: MESAS & LANÇAMENTO ---
    if aba2 is not None:
        with aba2:
            renderizar_cronometro()
            rodada_atual_num = dados['RodadaAtual']
            
            # 🚨 BLINDAGEM CONTRA KEYERROR AQUI:
            rodadas_lista = dados.get('Rodadas', [])
            rodada_atual = next((r for r in rodadas_lista if r['Numero'] == rodada_atual_num), None)
            
            if rodada_atual:
                col_tit, col_imp = st.columns([3, 1])
                with col_tit: st.markdown(f"<h2 style='color: #ffbf00 !important;'>⚔️ {rodada_atual_num}ª Rodada Oficial</h2>", unsafe_allow_html=True)
                with col_imp:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🖨️ IMPRIMIR NA ELGIN I9", use_container_width=True):
                        st.components.v1.html("<script>window.print();</script>", height=0, width=0)
                
                mesas = rodada_atual.get('Mesas', [])
                
                # --- SISTEMA DE IMPRESSÃO ---
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
                            
                        with st.expandable(f"📝 Lançar Placar - Mesa {m['Mesa']}") if hasattr(st, "expandable") else st.expander(f"📝 Lançar Placar - Mesa {m['Mesa']}"):
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
                                    # 🚨 ACESSO PROTEGIDO À MESA:
                                    alvo = dados['Rodadas'][dados['RodadaAtual'] - 1]['Mesas'][idx]
                                    alvo['Status'] = 'Concluído'
                                    alvo['FloresJ1'] = f1_num
                                    alvo['FloresJ2'] = f2_num
                                    try: t1_int, t2_int = int(t1_raw), int(t2_raw)
                                    except Exception: t1_int, t2_int = 0, 0
                                    
                                    if escolha_set.startswith(alvo['Jogador1']):
                                        alvo['SetsJ1'], alvo['SetsJ2'] = 2, (1 if "2 x 1" in escolha_set else 0)
                                        if "2 x 0" in escolha_set: alvo['TentosJ1'], alvo['TentosJ2'] = 72, 0
                                        else: alvo['TentosJ1'], alvo['TentosJ2'] = t1_int, t2_int
                                    else:
                                        alvo['SetsJ1'], alvo
