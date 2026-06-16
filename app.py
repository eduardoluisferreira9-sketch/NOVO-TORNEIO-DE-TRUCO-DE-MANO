import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

import gerenciador_dados
import motor_truco

# =======================================================
# 💾 INICIALIZAÇÃO DE DADOS PERSISTENTES (ANTI-RESET)
# =======================================================
# Lemos direto do arquivo em todo recarregamento para manter o relógio vivo
dados_carregados = gerenciador_dados.carregar_dados()

# BLINDAGEM: Se o arquivo vier vazio ou der erro, usa um dicionário padrão
if not dados_carregados or not isinstance(dados_carregados, dict):
    dados_carregados = {'Mesas': {}, 'Status': 'Em Andamento', 'RodadaAtual': 1}

# Sincroniza tanto o session_state quanto a variável global com o disco
st.session_state['dados'] = dados_carregados
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
            
            # Mostra o pódio dinâmico e o cantador de flor direto na TV
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
            rodada_atual = next((r for r in dados['Rodadas'] if r['Numero'] == rodada_atual_num), None)
            
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
                                        if "2 x 0" in escolha_set: alvo['TentosJ1'], alvo['TentosJ2'] = 72, 0
                                        else: alvo['TentosJ1'], alvo['TentosJ2'] = t1_int, t2_int
                                    else:
                                        alvo['SetsJ1'], alvo['SetsJ2'] = (1 if "2 x 1" in escolha_set else 0), 2
                                        if "2 x 0" in escolha_set: alvo['TentosJ1'], alvo['TentosJ2'] = 0, 72
                                        else: alvo['TentosJ1'], alvo['TentosJ2'] = t1_int, t2_int
                                            
                                    gerenciador_dados.salvar_dados(dados)
                                    st.success("Placar salvo com sucesso!")
                                    st.rerun()

    # --- ABA 3: PAINEL DE CONTROLE ---
    with aba3:
        st.markdown("<h2 style='color: #ffbf00 !important;'>⚙️ Painel de Controle Estratégico</h2>", unsafe_allow_html=True)
        autenticado = False
        senha_inserida = st.text_input("Insira a chave mestra de administrador:", type="password")
        if senha_inserida == gerenciador_dados.CHAVE_ADMINISTRADOR:
            autenticado = True
            st.success("Acesso liberado.")
        elif senha_inserida != "": st.error("Chave incorreta.")
            
        if autenticado:
            if dados['Status'] == 'Configuração':
                st.markdown("### 🛠️ Configurações Iniciais do Torneio")
                nome_torneio_input = st.text_input("Nome Oficial do Torneio:", value=dados.get('NomeTorneio', ''))
                tempo_minutos_input = st.number_input("Tempo de Duração de cada Rodada (Minutos):", min_value=5, max_value=180, value=int(dados.get('TempoLimiteMinutos', 45)), step=5)
                
                jogadores_salvos = dados.get('Jogadores', [])
                df_inicial = pd.DataFrame(jogadores_salvos) if jogadores_salvos else pd.DataFrame(columns=['Nome', 'Entidade'])
                
                df_editado = st.data_editor(
                    df_inicial, column_config={
                        "Nome": st.column_config.TextColumn("Nome do Atleta / Dupla", width="large", required=True),
                        "Entidade": st.column_config.TextColumn("Entidade / Equipe / Clube", width="large", default="SEM ENTIDADE")
                    }, num_rows="dynamic", use_container_width=True, key="editor_inscritos"
                )
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("💾 Salvar Revisão da Lista"):
                        lista_limpa = []
                        for _, row in df_editado.dropna(subset=['Nome']).iterrows():
                            lista_limpa.append({'Nome': str(row['Nome']).strip().upper(), 'Entidade': str(row['Entidade']).strip().upper() if pd.notna(row['Entidade']) else "SEM ENTIDADE"})
                        dados['NomeTorneio'] = nome_torneio_input if nome_torneio_input else "Torneio de Truco"
                        dados['TempoLimiteMinutos'] = tempo_minutos_input
                        dados['Cronometro']['TempoRestanteSegundos'] = tempo_minutos_input * 60
                        dados['Jogadores'] = lista_limpa
                        gerenciador_dados.salvar_dados(dados)
                        st.success("Configurações salvas e arquivadas!")
                        st.rerun()
                with col_b2:
                    if st.button("🚀 FECHAR INSCRIÇÕES E GERAR 1ª RODADA"):
                        lista_limpa = []
                        for _, row in df_editado.dropna(subset=['Nome']).iterrows():
                            lista_limpa.append({'Nome': str(row['Nome']).strip().upper(), 'Entidade': str(row['Entidade']).strip().upper() if pd.notna(row['Entidade']) else "SEM ENTIDADE"})
                        if len(lista_limpa) < 2: st.error("Mínimo de 2 competidores.")
                        else:
                            dados['NomeTorneio'] = nome_torneio_input if nome_torneio_input else "Torneio de Truco"
                            dados['TempoLimiteMinutos'] = tempo_minutos_input
                            dados['Cronometro']['TempoRestanteSegundos'] = tempo_minutos_input * 60
                            dados['Cronometro']['Ativo'] = False
                            dados['Cronometro']['FimRodada'] = False
                            dados['Jogadores'] = lista_limpa
                            dados['Status'] = 'Em Andamento'
                            dados['RodadaAtual'] = 0
                            dados['Rodadas'] = []
                            motor_truco.gerar_proxima_rodada(dados)
                            st.rerun()
                        
            elif dados['Status'] == 'Em Andamento':
                st.markdown(f"### 🛡️ Gestão da {dados['RodadaAtual']}ª Rodada")
                novo_tempo_manual = st.number_input("Ajustar minutos da rodada agora:", min_value=1, max_value=180, value=int(dados['TempoLimiteMinutos']))
                if st.button("🔄 Aplicar Novo Tempo Manual"):
                    dados['TempoLimiteMinutos'] = novo_tempo_manual
                    dados['Cronometro']['TempoRestanteSegundos'] = novo_tempo_manual * 60
                    dados['Cronometro']['FimRodada'] = False
                    gerenciador_dados.salvar_dados(dados)
                    st.success("Tempo reajustado!")
                    st.rerun()
                    
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1:
                    if st.button("▶️ Iniciar / Retomar Tempo", use_container_width=True):
                        dados['Cronometro']['Ativo'] = True
                        gerenciador_dados.salvar_dados(dados)
                        st.rerun()
                with col_c2:
                    if st.button("⏸️ Pausar Tempo", use_container_width=True):
                        dados['Cronometro']['Ativo'] = False
                        gerenciador_dados.salvar_dados(dados)
                        st.rerun()
                with col_c3:
                    if st.button("🔄 Resetar Tempo", use_container_width=True):
                        dados['Cronometro']['TempoRestanteSegundos'] = dados['TempoLimiteMinutos'] * 60
                        dados['Cronometro']['Ativo'] = False
                        dados['Cronometro']['FimRodada'] = False
                        gerenciador_dados.salvar_dados(dados)
                        st.rerun()
                
                st.markdown("---")
                rodada_atual_obj = dados['Rodadas'][dados['RodadaAtual'] - 1]
                todas_concluidas = all(m['Status'] == 'Concluído' for m in rodada_atual_obj['Mesas'])
                
                if todas_concluidas:
                    st.success("✅ Todas as mesas concluídas.")
                    if st.button("⏭️ Sortear e Gerar Próxima Rodada"):
                        dados['Cronometro']['TempoRestanteSegundos'] = dados['TempoLimiteMinutos'] * 60
                        dados['Cronometro']['Ativo'] = False
                        dados['Cronometro']['FimRodada'] = False
                        motor_truco.gerar_proxima_rodada(dados)
                        st.rerun()
                else: st.warning("⚠️ Existem mesas pendentes.")
                    
                st.markdown("---")
                st.markdown("### 🏆 Encerramento de Torneio")
                if st.button("🏁 Encerrar Torneio e Salvar Histórico"):
                    dados['Status'] = 'Encerrado'
                    gerenciador_dados.salvar_dados(dados)
                    classif_final = motor_truco.processar_classificacao(dados)
                    rei_flor, maior_flor = "N/A", -1
                    for j_f in classif_final:
                        if j_f['FlorPró'] > maior_flor:
                            maior_flor = j_f['FlorPró']
                            rei_flor = j_f['Nome']
                    
                    novo_registro = {
                        'Torneio': dados['NomeTorneio'], 'Data': datetime.now().strftime("%d/%m/%Y"),
                        'Campeao': classif_final[0]['Nome'] if len(classif_final) > 0 else "N/A",
                        'Vice': classif_final[1]['Nome'] if len(classif_final) > 1 else "N/A",
                        'Terceiro': classif_final[2]['Nome'] if len(classif_final) > 2 else "N/A",
                        'Quarto': classif_final[3]['Nome'] if len(classif_final) > 3 else "N/A",
                        'ReiDaFlor': f"{rei_flor} ({maior_flor} Flores)" if maior_flor > 0 else "N/A"
                    }
                    galeria = gerenciador_dados.carregar_galeria()
                    galeria.insert(0, novo_registro)
                    gerenciador_dados.salvar_galeria(galeria)
                    st.rerun()

            elif dados['Status'] == 'Encerrado':
                st.markdown("### 🏆 Torneio Finalizado")
                classif_final = motor_truco.processar_classificacao(dados)
                st.balloons()
                
                # Exibe o pódio triunfal de encerramento
                exibir_podio_arena(classif_final)
                
                if st.button("🔄 Reiniciar Sistema para Novo Torneio"):
                    if os.path.exists(gerenciador_dados.ARQUIVO_BACKUP): os.remove(gerenciador_dados.ARQUIVO_BACKUP)
                    st.session_state.dados = {
                        'NomeTorneio': '', 'Status': 'Configuração', 'Jogadores': [], 'RodadaAtual': 0, 'Rodadas': [],
                        'TempoLimiteMinutos': 45, 'Cronometro': {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False}
                    }
                    st.rerun()

    # --- ABA 4: HISTÓRICO DE CAMPEÕES ---
    with aba4:
        st.markdown("<h2 style='color: #ffbf00 !important;'>🏆 Galeria de Campeões Imortais</h2>", unsafe_allow_html=True)
        historico_galeria = gerenciador_dados.carregar_galeria()
        if historico_galeria:
            for registro in historico_galeria:
                st.markdown(f"""
                    <div class="galeria-card">
                        <div class="galeria-header">
                            <span class="galeria-titulo-evento">🏆 {registro.get('Torneio', 'Torneio sem Nome')}</span>
                            <span class="galeria-data">📅 Data: {registro.get('Data', 'N/A')}</span>
                        </div>
                        <div class="galeria-corpo">
                            <div class="galeria-linha-campeao">🥇 1º Lugar (Campeão): <span class="galeria-ouro">{registro.get('Campeao', 'N/A')}</span></div>
                            <div class="galeria-linha-secundaria">🥈 2º Lugar (Vice): {registro.get('Vice', 'N/A')}</div>
                            <div class="galeria-linha-secundaria">🥉 3º Lugar: {registro.get('Terceiro', 'N/A')} &nbsp;|&nbsp; 🏅 4º Lugar: {registro.get('Quarto', 'N/A')}</div>
                            <div class="galeria-linha-secundaria" style="margin-top: 5px; color: #ff4da6 !important;\">🌸 Rei da Flor: {registro.get('ReiDaFlor', 'N/A')}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else: st.info("Nenhum torneio registrado em histórico físico ainda.")

    # Rodada Operacional de Rodapé (Crédito de Engenharia)
    st.markdown(f"""
        <hr style='border-color: #222;'>
        <p style='text-align: center; color: #555; font-size: 0.85rem;'>Sistema de Engenharia de Torneios de Alta Performance • Desenvolvido e Licenciado por {gerenciador_dados.NOME_CRIADOR}</p>
    """, unsafe_allow_html=True)
