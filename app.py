import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

import gerenciador_dados
import motor_truco

# ==============================================================================
# 💾 1ª PARTE: INICIALIZAÇÃO DE DADOS PERSISTENTES E SINCRONIZAÇÃO SÓLIDA
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
            'Cronometro': {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False, 'TimestampInicio': None},
            'HistoricoCampeoes': []
        }
else:
    if dados_persistidos is not None and dados_persistidos != st.session_state.dados:
        st.session_state.dados = dados_persistidos

dados = st.session_state.dados

# Restaura integridade absoluta de chaves de controle
if 'TempoLimiteMinutos' not in dados: dados['TempoLimiteMinutos'] = 45
if 'Cronometro' not in dados: dados['Cronometro'] = {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False, 'TimestampInicio': None}
if 'tela_telao' not in st.session_state: st.session_state.tela_telao = "jogos"
if 'pagina_mesas' not in st.session_state: st.session_state.pagina_mesas = 0
if 'HistoricoCampeoes' not in dados: dados['HistoricoCampeoes'] = []

if 'perfil_usuario' not in st.session_state:
    st.session_state.perfil_usuario = "Público"

st.set_page_config(
    page_title="Central de Torneios de Truco - Arena",
    page_icon="🃏",
    layout="wide"
)

# Injeção Completa de Estilo CSS Premium e Responsivo
st.markdown("""
<style>
    .reportview-container { background: #0e1112; }
    .grade-telao-dinamica { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; padding: 2px; }
    .mesa-container { background-color: #1e2622; border: 1px solid #3d4f45; border-radius: 8px; padding: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 8px; }
    .mesa-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #3d4f45; padding-bottom: 6px; margin-bottom: 8px; font-weight: bold; color: #ffbf00; font-size: 0.95rem; }
    .mesa-status-pendente { background-color: #8a6d00; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; }
    .mesa-status-concluido { background-color: #1e5a34; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; }
    .mesa-corpo { display: flex; flex-direction: column; gap: 6px; }
    .jogador-linha { display: flex; justify-content: space-between; padding: 6px 8px; border-radius: 4px; background-color: #151b18; font-size: 0.9rem; }
    
    /* Destaques Visuais de Pós-Jogo (Verde para vencedor, Vermelho para perdedor) */
    .vencedor-destaque { background-color: #194d2b !important; border-left: 5px solid #28a745; font-weight: bold; }
    .perdedor-destaque { background-color: #4d1919 !important; border-left: 5px solid #dc3545; opacity: 0.85; }
    
    .jogador-nome { color: #e0e0e0; }
    .jogador-resultado { color: #a3cfb6; font-weight: bold; }

    /* Assinatura Corporativa na Sidebar */
    .dev-assinatura-container { background: linear-gradient(135deg, #1e2622 0%, #111513 100%); border: 1px solid #3d4f45; padding: 12px; border-radius: 6px; text-align: center; margin-bottom: 15px; }
    .dev-titulo { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .dev-nome { font-size: 1rem; color: #ffbf00; font-weight: bold; margin-top: 2px; }
    .dev-tag { font-size: 0.65rem; color: #28a745; margin-top: 1px; }

    /* FORMATADOR TÉRMICO DE IMPRESSÃO (ELGIN I9 - 80mm) */
    @media print {
        header, footer, nav, button, [data-testid="stSidebar"], 
        [data-testid="stHeader"], .stTabs, .stButton, div.element-container:has(button),
        div.element-container:has(input), div.element-container:has(select),
        div.element-container:has(textarea), .stRadio,
        .stExpander, .stAlert, h1, h2, h3, p { display: none !important; }
        @page { size: 76mm auto; margin: 0mm 2mm 0mm 2mm; }
        body { background-color: #ffffff !important; color: #000000 !important; margin: 0 !important; padding: 0 !important; }
        .secao-impressao-sumulas { display: block !important; width: 72mm !important; background-color: #ffffff !important; color: #000000 !important; }
        .cartao-sumula-print { background-color: #ffffff !important; color: #000000 !important; border-bottom: 2px dashed #000000 !important; padding: 5px 0px 25px 0px !important; page-break-inside: avoid !important; font-family: 'Courier New', Courier, Arial, sans-serif !important; width: 72mm !important; }
        .tabela-sumula-print { width: 100% !important; border-collapse: collapse !important; margin-top: 8px !important; }
        .tabela-sumula-print th, .tabela-sumula-print td { border: 1px solid #000000 !important; padding: 6px 3px !important; text-align: center !important; font-size: 10pt !important; }
        .texto-dupla-print { text-align: left !important; font-size: 9pt !important; font-weight: bold !important; word-break: break-all !important; }
    }
    .secao-impressao-sumulas { display: none; }
</style>
""", unsafe_allow_html=True)

# SIDEBAR CORPORATIVA ATUALIZADA
st.sidebar.markdown(f"""
    <div class="dev-assinatura-container">
        <div class="dev-titulo">Engenharia de Software</div>
        <div class="dev-nome">🚀 {gerenciador_dados.NOME_CRIADOR}</div>
        <div class="dev-tag">Direção e Gestão de Torneios</div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🔐 Nível de Acesso")
perfil_escolhido = st.sidebar.selectbox(
    "Mudar Perfil para:",
    ["Público", "📺 Modo Telão", "⚙️ Administrador"],
    index=0 if st.session_state.perfil_usuario == "Público" else (1 if st.session_state.perfil_usuario == "Telão" else 2)
)

if perfil_escolhido == "⚙️ Administrador":
    if st.session_state.perfil_usuario != "Administrador":
        senha_admin = st.sidebar.text_input("Chave de Segurança:", type="password")
        if st.sidebar.button("Autenticar 🔓", use_container_width=True):
            if senha_admin in ["admin123", "truco2026"]:
                st.session_state.perfil_usuario = "Administrador"
                st.sidebar.success("Acesso Autorizado!")
                st.rerun()
            else:
                st.sidebar.error("Senha Incorreta!")
    else:
        st.sidebar.info("⚡ Você está no Modo Diretor")
        if st.sidebar.button("Encerrar Sessão 🔒", use_container_width=True):
            st.session_state.perfil_usuario = "Público"
            st.rerun()
elif perfil_escolhido == "📺 Modo Telão":
    st.session_state.perfil_usuario = "Telão"
else:
    st.session_state.perfil_usuario = "Público"

modo_telao = (st.session_state.perfil_usuario == "Telão")


# ==============================================================================
# 🎛️ 2ª PARTE: MOTOR DE TEMPO EM JAVASCRIPT NATIVO (IMUNE A ABA ALTERNADA)
# ==============================================================================
def obter_tempo_restante_dinamico():
    c_dados = dados.get('Cronometro', {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False, 'TimestampInicio': None})
    if c_dados['Ativo'] and c_dados.get('TimestampInicio') is not None:
        decorrido = int(time.time() - c_dados['TimestampInicio'])
        restante = max(0, c_dados['TempoRestanteSegundos'] - decorrido)
        if restante <= 0:
            c_dados['Ativo'] = False
            c_dados['FimRodada'] = True
            c_dados['TempoRestanteSegundos'] = 0
            dados['Cronometro'] = c_dados
            gerenciador_dados.salvar_dados(dados)
            return 0, c_dados
        return restante, c_dados
    return c_dados['TempoRestanteSegundos'], c_dados

def injetar_cronometro_javascript(key_prefix="default"):
    segundos_totais, c_dados = obter_tempo_restante_dinamico()
    ativo_js = "true" if c_dados['Ativo'] else "false"
    
    html_cronometro = f"""
    <div id="{key_prefix}-js-cronometro-box" style="background-color: #121815; border: 2px solid #28a745; border-radius: 10px; padding: 6px; text-align: center; margin-bottom: 5px; box-shadow: 0 0 12px rgba(0,0,0,0.5);">
        <span id="{key_prefix}-js-cronometro-texto" style="font-size: 2.6rem; font-family: 'Courier New', monospace; font-weight: bold; color: #28a745; line-height: 1.1;">--:--</span>
    </div>
    <script>
        (function() {{
            var segundosRestantes = {segundos_totais};
            var ativo = {ativo_js};
            var elementoBox = document.getElementById('{key_prefix}-js-cronometro-box');
            var elementoTexto = document.getElementById('{key_prefix}-js-cronometro-texto');
            
            function atualizarDisplay() {{
                if (segundosRestantes <= 0) {{
                    elementoBox.style.borderColor = "#ff4b4b";
                    elementoTexto.style.color = "#ff4b4b";
                    elementoTexto.innerText = "00:00 - FIM DE TEMPO! 🔔";
                    return;
                }}
                var minutos = Math.floor(segundosRestantes / 60);
                var segundos = segundosRestantes % 60;
                var strMin = minutos < 10 ? "0" + minutos : minutos;
                var strSeg = segundos < 10 ? "0" + segundos : segundos;
                
                if (segundosRestantes < 300) {{
                    elementoBox.style.borderColor = "#ffaa00";
                    elementoTexto.style.color = "#ffaa00";
                    elementoTexto.innerText = strMin + ":" + strSeg + " - ÚLTIMOS MINUTOS! ⚠️";
                }} else {{
                    elementoBox.style.borderColor = "#28a745";
                    elementoTexto.style.color = "#28a745";
                    elementoTexto.innerText = strMin + ":" + strSeg;
                }}
            }}
            atualizarDisplay();
            if (ativo && segundosRestantes > 0) {{
                var intervalo = setInterval(function() {{
                    segundosRestantes--;
                    atualizarDisplay();
                    if (segundosRestantes <= 0) {{
                        clearInterval(intervalo);
                    }}
                }}, 1000);
            }}
        }})();
    </script>
    """
    st.components.v1.html(html_cronometro, height=80)

def exibir_podio_arena(lista_classificada):
    if not lista_classificada: return
    c1 = lista_classificada[0]['Nome'] if len(lista_classificada) > 0 else "---"
    c2 = lista_classificada[1]['Nome'] if len(lista_classificada) > 1 else "---"
    c3 = lista_classificada[2]['Nome'] if len(lista_classificada) > 2 else "---"
    st.markdown(f"""
        <div style='display: flex; justify-content: space-around; background-color: #151b18; padding: 10px; border-radius: 8px; border: 1px solid #3d4f45; text-align: center; margin-bottom: 10px;'>
            <div><span style='color: #d7d7d7; font-size: 0.85rem;'>🥈 2º Lugar</span><br><b style='font-size:1rem;'>{c2}</b></div>
            <div><span style='color: #ffbf00; font-size: 1.1rem;'>🥇 1º Lugar</span><br><b style='font-size:1.2rem; color: #ffbf00;'>{c1}</b></div>
            <div><span style='color: #cd7f32; font-size: 0.85rem;'>🥉 3º Lugar</span><br><b style='font-size:1rem;'>{c3}</b></div>
        </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 📺 3ª PARTE: MODO TELÃO - AUTOMATIZADO COM CONTROLE DE PÁGINAS SEM QUEBRAS
# ==============================================================================
if modo_telao:
    titulo_torneio_show = dados.get('NomeTorneio', 'Torneio de Truco')
    rodada_txt = f"• {dados['RodadaAtual']}ª Rodada" if dados['Status'] in ['Em Andamento', 'Mata-Mata'] else f"• {dados['Status']}"
    
    st.markdown(f"<div style='text-align: center;'><h1 style='color: #ffbf00; margin: 0; font-size: 1.9rem;'>🃏 {titulo_torneio_show} <span style='color:#a3cfb6; font-size: 1.4rem;'>{rodada_txt}</span></h1></div>", unsafe_allow_html=True)
    
    if dados['Status'] in ['Em Andamento', 'Mata-Mata']:
        injetar_cronometro_javascript(key_prefix="telao")
        
    if st.session_state.tela_telao == "jogos":
        if 'RodadaAtual' in dados and 'Rodadas' in dados and len(dados['Rodadas']) > 0:
            rodada_atual_num = dados['RodadaAtual']
            rodada_atual = next((r for r in dados['Rodadas'] if r.get('Numero') == rodada_atual_num), None)
            
            if rodada_atual and 'Mesas' in rodada_atual:
                mesas = rodada_atual.get('Mesas', [])
                MESAS_POR_PAGINA = 6
                total_paginas = (len(mesas) + MESAS_POR_PAGINA - 1) // MESAS_POR_PAGINA
                
                if st.session_state.pagina_mesas >= total_paginas:
                    st.session_state.pagina_mesas = 0
                    
                pag_atual = st.session_state.pagina_mesas
                mesas_visiveis = mesas[pag_atual * MESAS_POR_PAGINA : (pag_atual + 1) * MESAS_POR_PAGINA]
                
                # Exibição das Páginas na barra lateral para acompanhamento do diretor se estiver olhando o telão
                st.sidebar.markdown(f"### 📺 Monitor do Telão\nExibindo Página **{pag_atual+1} de {total_paginas}**")
                
                st.markdown(f"<h4 style='color: #ffbf00; margin: 5px 0; text-align:center;'>⚔️ PARTIDAS EM ANDAMENTO (PÁGINA {pag_atual+1}/{total_paginas})</h4>", unsafe_allow_html=True)
                
                col_t1, col_t2 = st.columns(2)
                for idx, m in enumerate(mesas_visiveis):
                    col_alvo = col_t1 if idx % 2 == 0 else col_t2
                    with col_alvo:
                        v1 = "vencedor-destaque" if m.get('Status') == 'Concluído' and int(m.get('SetsJ1', 0)) > int(m.get('SetsJ2', 0)) else ("perdedor-destaque" if m.get('Status') == 'Concluído' else "")
                        v2 = "vencedor-destaque" if m.get('Status') == 'Concluído' and int(m.get('SetsJ2', 0)) > int(m.get('SetsJ1', 0)) else ("perdedor-destaque" if m.get('Status') == 'Concluído' else "")
                        
                        st.markdown(f"""
                        <div class="mesa-container">
                            <div class="mesa-header"><span>Mesa {m.get('Mesa')}</span><span class="mesa-status-{'concluido' if m.get('Status')=='Concluído' else 'pendente'}">{m.get('Status').upper()}</span></div>
                            <div class="mesa-corpo">
                                <div class="jogador-linha {v1}"><span class="jogador-nome">👤 {m.get('Jogador1')}</span><span class="jogador-resultado">{m.get('SetsJ1', 0)}S ({m.get('TentosJ1', 0)}T)</span></div>
                                <div class="jogador-linha {v2}"><span class="jogador-nome">👤 {m.get('Jogador2')}</span><span class="jogador-resultado">{m.get('SetsJ2', 0)}S ({m.get('TentosJ2', 0)}T)</span></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                time.sleep(10)
                st.session_state.pagina_mesas += 1
                if st.session_state.pagina_mesas >= total_paginas:
                    st.session_state.tela_telao = "classificacao"
                st.rerun()
            else:
                st.info("Aguardando montagem das mesas...")
                time.sleep(3)
                st.rerun()
        else:
            st.info("Chaves da rodada ainda não geradas.")
            time.sleep(3)
            st.rerun()
    else:
        st.markdown("<h4 style='color: #ffbf00; margin: 5px 0; text-align:center;'>📊 CLASSIFICAÇÃO GERAL PARCIAL</h4>", unsafe_allow_html=True)
        if dados.get('Jogadores'):
            lista_classificada = motor_truco.processar_classificacao(dados)
            exibir_podio_arena(lista_classificada)
            
            df_class = pd.DataFrame(lista_classificada)
            df_class.index = [f"{i+1}º" for i in range(len(df_class))]
            st.dataframe(df_class.rename(columns={'Nome': 'Competidor', 'Pts': 'Pontos', 'Vit': 'Vitórias', 'SaldoSets': 'Saldo Sets', 'SaldoTent': 'Saldo Tentos'})[['Competidor', 'Pontos', 'Vitórias', 'Saldo Sets', 'Saldo Tentos']], use_container_width=True, height=210)
        
        time.sleep(8)
        st.session_state.tela_telao = "jogos"
        st.session_state.pagina_mesas = 0
        st.rerun()


# ==============================================================================
# 🏢 4ª PARTE: MODO OPERACIONAL CENTRAL INTERATIVO (ABAS)
# ==============================================================================
else:
    st.markdown("<h1 style='text-align: center; color: #ffbf00;'>🃏 Central de Torneios de Truco</h1>", unsafe_allow_html=True)
    
    # Montagem Dinâmica de Abas Baseada no Estado
    abas_lista = ["📊 Classificação Geral"]
    if dados['Status'] == 'Configuração': abas_lista.append("📝 Inscrição Online")
    if st.session_state.perfil_usuario == "Administrador" and dados['Status'] != 'Configuração': abas_lista.append("⚔️ Lançar Mesas & Comando")
    if st.session_state.perfil_usuario == "Administrador": abas_lista.append("⚙️ Configurações Gerais")
    abas_lista.append("🏆 Galeria de Campeões")
    
    abas_criadas = st.tabs(abas_lista)
    aba_index = 0
    
    # --- ABA 1: CLASSIFICAÇÃO GERAL ---
    with abas_criadas[aba_index]:
        st.markdown("<h2 style='color: #ffbf00;'>📊 Tabela Classificatória Estratégica</h2>", unsafe_allow_html=True)
        if dados['Status'] != 'Configuração' and dados.get('Jogadores'):
            lista_classificada = motor_truco.processar_classificacao(dados)
            exibir_podio_arena(lista_classificada)
            
            df_class = pd.DataFrame(lista_classificada)
            df_class.index = [f"{i+1}º" for i in range(len(df_class))]
            st.dataframe(df_class.rename(columns={
                'Nome': 'Competidor', 'Entidade': 'Equipe', 'Pts': 'Pontos', 'Vit': 'Vitórias',
                'SaldoSets': 'Saldo Sets', 'SetsPró': 'Sets Pró', 'SaldoTent': 'Saldo Tentos', 'TentPró': 'Tentos Pró', 'Bukes': 'Buchholz', 'Jogos': 'Partidas'
            })[['Competidor', 'Equipe', 'Pontos', 'Vitórias', 'Saldo Sets', 'Sets Pró', 'Saldo Tentos', 'Tentos Pró', 'Buchholz', 'Partidas']], use_container_width=True)
        else:
            st.info("O campeonato ainda não começou. Adicione jogadores na aba de configurações.")
            if dados.get('Jogadores'):
                st.markdown("### 👥 Competidores Já Confirmados:")
                st.dataframe(pd.DataFrame(dados['Jogadores']), use_container_width=True)
    aba_index += 1

    # --- ABA 2: INSCRIÇÃO ONLINE ---
    if "📝 Inscrição Online" in abas_lista:
        with abas_criadas[aba_index]:
            st.markdown("<h2 style='color: #ffbf00;'>📝 Formulário de Pré-Inscrição</h2>", unsafe_allow_html=True)
            with st.form("form_insc"):
                n = st.text_input("Nome da Dupla / Jogador:").strip().upper()
                e = st.text_input("Origem / Clube / Entidade:").strip().upper()
                if st.form_submit_button("Confirmar Minha Inscrição 🚀") and n:
                    if n not in [j['Nome'] for j in dados.get('Jogadores', [])]:
                        dados['Jogadores'].append({'Nome': n, 'Entidade': e if e else "AVULSO"})
                        gerenciador_dados.salvar_dados(dados)
                        st.success("Inscrição Registrada!")
                        st.rerun()
                    else: st.warning("Nome já cadastrado!")
        aba_index += 1


    # ==============================================================================
    # ⚔️ ABA CENTRALIZADA DE CONTROLES: CRONÔMETRO + GESTÃO DO MATA + LANÇAMENTO DE MESAS
    # ==============================================================================
    if "⚔️ Lançar Mesas & Comando" in abas_lista:
        with abas_criadas[aba_index]:
            rodada_atual_num = dados['RodadaAtual']
            rodada_atual = next((r for r in dados.get('Rodadas', []) if r['Numero'] == rodada_atual_num), None)
            
            st.markdown(f"## ⚔️ Painel Unificado — {rodada_atual_num}ª Rodada ({dados['Status']})")
            
            # --- CONTROLE CENTRALIZADO DO CRONÔMETRO ---
            c_col1, c_col2, c_col3 = st.columns([2, 2, 2])
            with c_col1:
                injetar_cronometro_javascript(key_prefix="central_comando")
            with c_col2:
                restante_real, c_dados = obter_tempo_restante_dinamico()
                c_ativo = c_dados.get('Ativo', False)
                st.markdown("<p style='margin-bottom:2px; font-weight:bold;'>Controle de Tempo:</p>", unsafe_allow_html=True)
                if st.button("⏸️ Pausar Cronômetro" if c_ativo else "▶️ Soltar Cronômetro", use_container_width=True):
                    dados['Cronometro']['TempoRestanteSegundos'] = restante_real
                    dados['Cronometro']['Ativo'] = not c_ativo
                    dados['Cronometro']['TimestampInicio'] = time.time() if not c_ativo else None
                    gerenciador_dados.salvar_dados(dados); st.rerun()
            with c_col3:
                st.markdown("<p style='margin-bottom:2px; font-weight:bold;'>Resetar:</p>", unsafe_allow_html=True)
                if st.button("🔄 Voltar Tempo Inicial Padrão", use_container_width=True):
                    dados['Cronometro']['TempoRestanteSegundos'] = dados['TempoLimiteMinutos'] * 60
                    dados['Cronometro']['FimRodada'] = False
                    if dados['Cronometro']['Ativo']: dados['Cronometro']['TimestampInicio'] = time.time()
                    gerenciador_dados.salvar_dados(dados); st.rerun()
            
            st.markdown("---")
            
            if rodada_atual:
                mesas = rodada_atual.get('Mesas', [])
                
                # --- BOTÃO DE IMPRESSÃO DE SÚMULAS PARALELO (ELGIN I9) ---
                col_t_mesa, col_btn_print = st.columns([3, 1])
                with col_t_mesa: st.markdown("### 🎴 Mesas de Lançamento Ativas")
                with col_btn_print:
                    if st.button("🖨️ IMPRIMIR TODAS AS SÚMULAS", use_container_width=True):
                        st.components.v1.html("<script>window.print();</script>", height=0, width=0)
                
                # Renderizador HTML da Elgin I9 invisível em tela
                html_impressao = f"<div class='secao-impressao-sumulas'>"
                for m in mesas:
                    if m['Jogador1'] == "CHAPÉU" or m['Jogador2'] == "CHAPÉU": continue 
                    html_impressao += f"""
                    <div class='cartao-sumula-print'>
                        <div style='text-align:center; font-weight:bold; font-size:11pt; border-bottom:1px solid #000;'>{dados.get('NomeTorneio', 'TORNEIO DE TRUCO')}</div>
                        <div style='display:flex; justify-content:space-between; margin-top:5px; font-weight:bold; font-size:11pt;'><span>🎴 MESA {m['Mesa']}</span><span>{rodada_atual_num}a RODADA</span></div>
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
                
                # --- VALIDAÇÃO DE COMPLETUDE DA RODADA ---
                todas_concluidas = True
                for m in mesas:
                    if m['Status'] != 'Concluído': todas_concluidas = False
                
                # --- TRAVA E GESTÃO DAS 5 RODADAS + ESTRUTURAÇÃO DO MATA-MATA ---
                if todas_concluidas and dados['Status'] == 'Em Andamento':
                    st.markdown("### 🏁 Gestão de Avanço do Torneio")
                    if rodada_atual_num < 5:
                        if st.button(f"🏁 CONCLUIR {rodada_atual_num}ª RODADA E SEGUIR CHAVEAMENTO SUÍÇO", type="primary", use_container_width=True):
                            dados['RodadaAtual'] += 1
                            nova_r = motor_truco.gerar_rodada_suica(dados, dados['RodadaAtual'])
                            if nova_r: dados['Rodadas'].append(nova_r)
                            dados['Cronometro']['TempoRestanteSegundos'] = dados['TempoLimiteMinutos'] * 60
                            if dados['Cronometro']['Ativo']: dados['Cronometro']['TimestampInicio'] = time.time()
                            gerenciador_dados.salvar_dados(dados); st.success("Próxima rodada gerada!"); st.rerun()
                    else:
                        # TRAVA DAS 5 RODADAS ACIONADA: Bloqueia fluxo normal e abre seletor customizado de Mata-Mata
                        st.warning("📊 A Fase Classificatória de 5 partidas foi concluída! Escolha a estrutura da fase eliminatória abaixo:")
                        tipo_mata = st.selectbox("Formato desejado para o Mata-Mata:", [
                            "Selecione o formato...",
                            "Oitavas de Final (Top 16 Classificados)",
                            "Quartas de Final (Top 8 Classificados)",
                            "Semifinal Direta (Top 4 Classificados)"
                        ])
                        
                        if tipo_mata != "Selecione o formato..." and st.button("🔥 FECHAR FASE SUÍÇA E ENTRAR NO MATA-MATA", type="primary", use_container_width=True):
                            dados['Status'] = 'Mata-Mata'
                            dados['RodadaAtual'] += 1
                            
                            tamanho_mata = 16 if "Oitavas" in tipo_mata else (8 if "Quartas" in tipo_mata else 4)
                            lista_ranking = motor_truco.processar_classificacao(dados)
                            top_classificados = lista_ranking[:tamanho_mata]
                            
                            # Casamento Olímpico Clássico: 1º x Último, 2º x Penúltimo
                            novas_mesas = []
                            for i in range(len(top_classificados) // 2):
                                novas_mesas.append({
                                    'Mesa': i + 1, 'Jogador1': top_classificados[i]['Nome'], 'Jogador2': top_classificados[-(i + 1)]['Nome'],
                                    'Status': 'Pendente', 'SetsJ1': 0, 'SetsJ2': 0, 'TentosJ1': 0, 'TentosJ2': 0, 'FloresJ1': 0, 'FloresJ2': 0
                                })
                            dados['Rodadas'].append({'Numero': dados['RodadaAtual'], 'Mesas': novas_mesas})
                            gerenciador_dados.salvar_dados(dados); st.rerun()
                            
                elif todas_concluidas and dados['Status'] == 'Mata-Mata':
                    st.markdown("### 🏆 Gestão das Chaves do Mata-Mata")
                    if st.button("🏆 CONCLUIR FASE ELIMINATÓRIA E AVANÇAR ETAPA", type="primary", use_container_width=True):
                        vencedores = []
                        for m in rodada_atual.get('Mesas', []):
                            if int(m['SetsJ1']) > int(m['SetsJ2']): vencedores.append(m['Jogador1'])
                            else: vencedores.append(m['Jogador2'])
                        
                        if len(vencedores) == 1:
                            dados['Status'] = 'Finalizado'
                            dados['HistoricoCampeoes'].append({
                                'Torneio': dados.get('NomeTorneio', 'Torneio Arena'), 'Campeao': vencedores[0], 'Data': datetime.now().strftime("%d/%m/%Y")
                            })
                        else:
                            dados['RodadaAtual'] += 1
                            novas_mesas = []
                            for i in range(0, len(vencedores), 2):
                                novas_mesas.append({
                                    'Mesa': (i // 2) + 1, 'Jogador1': vencedores[i], 'Jogador2': vencedores[i+1],
                                    'Status': 'Pendente', 'SetsJ1': 0, 'SetsJ2': 0, 'TentosJ1': 0, 'TentosJ2': 0, 'FloresJ1': 0, 'FloresJ2': 0
                                })
                            dados['Rodadas'].append({'Numero': dados['RodadaAtual'], 'Mesas': novas_mesas})
                        gerenciador_dados.salvar_dados(dados); st.rerun()
                else:
                    st.warning("🔒 **Mesas Pendentes:** Lance todos os placares da rodada corrente antes de avançar.")

                # --- RENDERIZADOR INTERATIVO DOS SÈTS E PLACARES ---
                col_mesa1, col_mesa2 = st.columns(2)
                for idx, m in enumerate(mesas):
                    col_alvo = col_mesa1 if idx % 2 == 0 else col_mesa2
                    with col_alvo:
                        v1 = "vencedor-destaque" if m['Status']=='Concluído' and int(m['SetsJ1']) > int(m['SetsJ2']) else ("perdedor-destaque" if m['Status']=='Concluído' else "")
                        v2 = "vencedor-destaque" if m['Status']=='Concluído' and int(m['SetsJ2']) > int(m['SetsJ1']) else ("perdedor-destaque" if m['Status']=='Concluído' else "")
                        
                        st.markdown(f"""
                            <div class="mesa-container">
                                <div class="mesa-header"><span>🎴 Mesa {m['Mesa']}</span><span class="mesa-status-{'concluido' if m['Status'] == 'Concluído' else 'pendente'}">{m['Status'].upper()}</span></div>
                                <div class="mesa-corpo">
                                    <div class="jogador-linha {v1}"><span class="jogador-nome">👤 {m['Jogador1']}</span><span class="jogador-resultado">{m['SetsJ1']} Set(s) ({m['TentosJ1']} T / {m['FloresJ1']} F)</span></div>
                                    <div class="jogador-linha {v2}"><span class="jogador-nome">👤 {m['Jogador2']}</span><span class="jogador-resultado">{m['SetsJ2']} Set(s) ({m['TentosJ2']} T / {m['FloresJ2']} F)</span></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if m['Jogador1'] == "CHAPÉU" or m['Jogador2'] == "CHAPÉU": continue
                        
                        with st.expander(f"📝 Lançar Placar - Mesa {m['Mesa']}"):
                            f_key = f"form_mesa_{m['Mesa']}_{rodada_atual_num}"
                            opcoes = ["Aguardando...", f"{m['Jogador1']} 2 x 0 (Ganha 3x0 - 72 Tentos)", f"{m['Jogador2']} 2 x 0 (Ganha 3x0 - 72 Tentos)", f"{m['Jogador1']} 2 x 1", f"{m['Jogador2']} 2 x 1"]
                            escolha_set = st.selectbox("Qual o placar em Sets?", opcoes, key=f"sel_{f_key}")
                            
                            t1_int, t2_int = 0, 0
                            if escolha_set != "Aguardando...":
                                if "2 x 0" in escolha_set:
                                    if escolha_set.startswith(m['Jogador1']):
                                        st.success(f"🏆 {m['Jogador1']} computa 3x0 (72 Tentos).")
                                        t1_int = 72
                                        t2_int = st.number_input(f"Tentos de {m['Jogador2']} (Máximo 46):", min_value=0, max_value=46, value=0, key=f"t2_{f_key}")
                                    else:
                                        st.success(f"🏆 {m['Jogador2']} computa 3x0 (72 Tentos).")
                                        t2_int = 72
                                        t1_int = st.number_input(f"Tentos de {m['Jogador1']} (Máximo 46):", min_value=0, max_value=46, value=0, key=f"t1_{f_key}")
                                else:
                                    col_tx1, col_tx2 = st.columns(2)
                                    with col_tx1: t1_raw = st.text_input(f"Tentos de {m['Jogador1']}", value=str(m.get('TentosJ1', 0)), key=f"t1_{f_key}")
                                    with col_tx2: t2_raw = st.text_input(f"Tentos de {m['Jogador2']}", value=str(m.get('TentosJ2', 0)), key=f"t2_{f_key}")
                                    try: t1_int, t2_int = int(t1_raw), int(t2_raw)
                                    except: t1_int, t2_int = 0, 0
                            
                            col_f1, col_f2 = st.columns(2)
                            with col_f1: f1_num = st.number_input(f"🌸 Flores de {m['Jogador1']}", min_value=0, value=int(m.get('FloresJ1',0)), step=1, key=f"f1_{f_key}")
                            with col_f2: f2_num = st.number_input(f"🌸 Flores de {m['Jogador2']}", min_value=0, value=int(m.get('FloresJ2',0)), step=1, key=f"f2_{f_key}")
                            
                            if st.button("Confirmar e Salvar Mesa", key=f"btn_{f_key}") and escolha_set != "Aguardando...":
                                alvo = dados['Rodadas'][dados['RodadaAtual'] - 1]['Mesas'][idx]
                                alvo['Status'] = 'Concluído'; alvo['FloresJ1'] = f1_num; alvo['FloresJ2'] = f2_num
                                
                                if escolha_set.startswith(alvo['Jogador1']):
                                    alvo['SetsJ1'] = 3 if "2 x 0" in escolha_set else 2
                                    alvo['SetsJ2'] = 0 if "2 x 0" in escolha_set else 1
                                else:
                                    alvo['SetsJ1'] = 0 if "2 x 0" in escolha_set else 1
                                    alvo['SetsJ2'] = 3 if "2 x 0" in escolha_set else 2
                                    
                                alvo['TentosJ1'], alvo['TentosJ2'] = t1_int, t2_int
                                segundos_restantes_agora, _ = obter_tempo_restante_dinamico()
                                dados['Cronometro']['TempoRestanteSegundos'] = segundos_restantes_agora
                                if dados['Cronometro']['Ativo']: dados['Cronometro']['TimestampInicio'] = time.time()
                                    
                                gerenciador_dados.salvar_dados(dados); st.success("Placar Gravado!"); st.rerun()
            else: st.info("Nenhuma mesa ativa encontrada para esta rodada.")
        aba_index += 1


    # --- ABA 3: CONFIGURAÇÕES GERAIS COMPLETA ---
    if "⚙️ Configurações Gerais" in abas_lista:
        with abas_criadas[aba_index]:
            st.markdown("<h2 style='color: #ffbf00;'>⚙️ Painel de Controle Operacional</h2>", unsafe_allow_html=True)
            if dados['Status'] == 'Configuração':
                st.markdown("### 🏷️ Definições do Torneio")
                nome_torneio_input = st.text_input("Nome da Competição:", value=dados.get('NomeTorneio', ''))
                tempo_limite = st.number_input("Minutos por rodada:", min_value=5, max_value=120, value=int(dados.get('TempoLimiteMinutos', 45)))
                
                st.markdown("---")
                st.markdown("### 👥 Cadastro de Competidores")
                opcao_cadastro = st.radio("Método de entrada:", ["Individual Manual", "🚀 Importação Rápida em Lote (Copia e Cola)"], horizontal=True)
                
                if opcao_cadastro == "Individual Manual":
                    col_cad1, col_cad2 = st.columns(2)
                    with col_cad1: novo_nome = st.text_input("Nome do Competidor / Dupla:", key="cad_nome").strip().upper()
                    with col_cad2: nova_ent = st.text_input("Entidade / Origem:", key="cad_ent").strip().upper()
                    if st.button("📥 Cadastrar Competidor"):
                        if novo_nome and novo_nome not in [j['Nome'] for j in dados.get('Jogadores', [])]:
                            dados['Jogadores'].append({'Nome': novo_nome, 'Entidade': nova_ent if nova_ent else "MESA"})
                            gerenciador_dados.salvar_dados(dados); st.success("Cadastrado!"); st.rerun()
                else:
                    st.markdown("> **Instruções:** Cole **um competidor por linha**.")
                    entidade_lote = st.text_input("Entidade padrão do lote:", value="MESA").strip().upper()
                    texto_lote = st.text_area("Lista de competidores:")
                    if st.button("⚡ Executar Carga em Massa"):
                        if texto_lote.strip():
                            linhas = [l.strip().upper() for l in texto_lote.split("\n") if l.strip()]
                            c_novos = 0
                            existentes = [j['Nome'] for j in dados.get('Jogadores', [])]
                            for linha in linhas:
                                if linha not in existentes:
                                    dados['Jogadores'].append({'Nome': linha, 'Entidade': entidade_lote})
                                    existentes.append(linha); c_novos += 1
                            if c_novos > 0: gerenciador_dados.salvar_dados(dados); st.success(f"Carregados {c_novos} competidores!"); st.rerun()

                st.markdown("---")
                if st.button("🚀 INICIAR CAMPEONATO OFICIAL (START)"):
                    if len(dados.get('Jogadores', [])) >= 2:
                        for j in dados['Jogadores']:
                            j.update({'Pts': 0, 'Vit': 0, 'SaldoSets': 0, 'SetsPró': 0, 'SaldoTent': 0, 'TentPró': 0, 'SaldoFlor': 0, 'FlorPró': 0, 'Bukes': 0, 'Jogos': 0})
                        dados['NomeTorneio'] = nome_torneio_input if nome_torneio_input else "Torneio de Truco"
                        dados['TempoLimiteMinutos'] = tempo_limite
                        dados['Status'] = 'Em Andamento'; dados['RodadaAtual'] = 1
                        dados['Cronometro'] = {'TempoRestanteSegundos': tempo_limite * 60, 'Ativo': True, 'FimRodada': False, 'TimestampInicio': time.time()}
                        dados['Rodadas'] = []
                        try:
                            primeira_r = motor_truco.gerar_rodada_suica(dados, 1)
                            if primeira_r: dados['Rodadas'].append(primeira_r); gerenciador_dados.salvar_dados(dados); st.success("Torneio Iniciado!"); st.rerun()
                        except Exception as e: st.error(f"Erro ao gerar chave: {e}")
                
                if dados.get('Jogadores'):
                    st.markdown("### 👥 Remover Inscritos")
                    for idx_j, jog in enumerate(dados['Jogadores']):
                        col_j1, col_j2 = st.columns([3, 1])
                        with col_j1: st.write(f"👤 {jog['Nome']} — {jog['Entidade']}")
                        with col_j2:
                            if st.button("❌ Remover", key=f"rem_{idx_j}"): dados['Jogadores'].pop(idx_j); gerenciador_dados.salvar_dados(dados); st.rerun()
            else: st.info("🔒 Torneio em andamento. Inscrições bloqueadas.")
            
            if st.button("🚨 ZERAR SISTEMA (LIMPAR TODO O BANCO)"):
                gerenciador_dados.limpar_banco_dados()
                if 'dados' in st.session_state: del st.session_state.dados
                st.rerun()
        aba_index += 1

    # --- ABA 4: GALERIA DE CAMPEÕES ---
    with abas_criadas[aba_index]:
        st.markdown("<h2 style='color: #ffbf00;'>🏆 Galeria Permanente de Campeões</h2>", unsafe_allow_html=True)
        if dados.get('HistoricoCampeoes'):
            for h in dados['HistoricoCampeoes']: st.write(f"🏅 **{h['Torneio']}** | Campeão: `{h['Campeao']}` — 🗓️ {h['Data']}")
        else: st.info("Nenhum registro encontrado no arquivo definitivo.")
