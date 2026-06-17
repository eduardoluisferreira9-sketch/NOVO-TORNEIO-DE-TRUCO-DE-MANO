import streamlit as st
import pandas as pd
import numpy as np
import time
import json
import os
from datetime import datetime

# ==============================================================================
# 🗄️ 1. GERENCIADOR DE BANCO DE DADOS (JSON PERSISTENTE)
# ==============================================================================
class GerenciadorDados:
    def __init__(self, caminho_arquivo="banco_truco.json"):
        self.caminho_arquivo = caminho_arquivo

    def carregar_dados(self):
        if not os.path.exists(self.caminho_arquivo):
            return self.obter_estrutura_inicial()
        try:
            with open(self.caminho_arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return self.obter_estrutura_inicial()

    def salvar_dados(self, dados):
        with open(self.caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)

    def limpar_banco_dados(self):
        dados_iniciais = self.obter_estrutura_inicial()
        # Preserva a galeria histórica ao purgar o campeonato atual
        atual = self.carregar_dados()
        dados_iniciais["HistoricoCampeoes"] = atual.get("HistoricoCampeoes", [])
        self.salvar_dados(dados_iniciais)
        return dados_iniciais

    def obter_estrutura_inicial(self):
        return {
            "NomeTorneio": "Torneio de Truco",
            "Status": "Configuração",  # Configuração, Em Andamento, Mata-Mata, Encerrado
            "Fase": "Suíço",
            "RodadaAtual": 0,
            "TempoLimiteMinutos": 45,
            "Jogadores": [],
            "Rodadas": [],
            "FasesMataMata": {
                "FaseAtual": "",
                "Mesas": [],
                "HistoricoFases": []
            },
            "PodioFinal": {},
            "HistoricoCampeoes": [],
            "FloresAcumuladasMata": {},
            "Cronometro": {
                "TempoRestanteSegundos": 2700,
                "Ativo": False,
                "FimRodada": False,
                "TimestampInicio": None
            }
        }

gerenciador_dados = GerenciadorDados()

# ==============================================================================
# ⚙️ 2. MOTOR MATEMÁTICO E LOGÍSTICO DO TRUCO (SISTEMA SUÍÇO & PLAYOFFS)
# ==============================================================================
class MotorTruco:
    def processar_classificacao(self, dados):
        """Calcula e ordena a tabela do Suíço baseando-se nos critérios oficiais."""
        jogadores = dados.get("Jogadores", [])
        if not jogadores:
            return []
            
        # Recalcula os Buchholz (Soma dos pontos dos adversários enfrentados)
        # Criação de um mapa rápido de pontuação por jogador
        mapa_pts = {j["Nome"]: j.get("Pts", 0) for j in jogadores}
        mapa_confrontos = {j["Nome"]: [] for j in jogadores}
        
        # Escaneia rodadas concluídas para mapear adversários
        for r in dados.get("Rodadas", []):
            for m in r.get("Mesas", []):
                if m.get("Status") == "Concluído":
                    j1, j2 = m["Jogador1"], m["Jogador2"]
                    if j1 in mapa_confrontos and j2 != "CHAPÉU": mapa_confrontos[j1].append(j2)
                    if j2 in mapa_confrontos and j1 != "CHAPÉU": mapa_confrontos[j2].append(j1)
                    
        for j in jogadores:
            advs = mapa_confrontos.get(j["Nome"], [])
            j["Bukes"] = sum(mapa_pts.get(adv, 0) for adv in advs)
            
        df = pd.DataFrame(jogadores)
        # Ordenação oficial: Pontos -> Vitórias -> Saldo de Sets -> Saldo de Tentos -> Saldo de Flores -> Buchholz
        df = df.sort_values(
            by=["Pts", "Vit", "SaldoSets", "SaldoTent", "SaldoFlor", "Bukes"],
            ascending=[False, False, False, False, False, False]
        ).reset_index(drop=True)
        return df.to_dict(orient="records")

    def gerar_rodada_suica(self, dados, num_rodada):
        """Gera emparceiramento via Sistema Suíço puro evitando repetição de confrontos."""
        jogadores = self.processar_classificacao(dados)
        num_jogadores = len(jogadores)
        
        if num_jogadores == 0:
            return None
            
        # Histórico de confrontos para checagem de repetição
        confrontos_passados = set()
        for r in dados.get("Rodadas", []):
            for m in r.get("Mesas", []):
                j1, j2 = m["Jogador1"], m["Jogador2"]
                confrontos_passados.add((j1, j2))
                confrontos_passados.add((j2, j1))

        # Tratamento de Chapéu (Bye) se número de jogadores for ímpar
        chapeu_atribuido = None
        if num_jogadores % 2 != 0:
            # Encontra o último colocado que ainda não pegou Chapéu
            jogadores_com_chapeu = set()
            for r in dados.get("Rodadas", []):
                for m in r.get("Mesas", []):
                    if m["Jogador1"] == "CHAPÉU": jogadores_com_chapeu.add(m["Jogador2"])
                    if m["Jogador2"] == "CHAPÉU": jogadores_com_chapeu.add(m["Jogador1"])
            
            for j in reversed(jogadores):
                if j["Nome"] not in jogadores_com_chapeu:
                    chapeu_atribuido = j["Nome"]
                    break
            if not chapeu_atribuido:
                chapeu_atribuido = jogadores[-1]["Nome"]

        # Filtragem ativa para pareamento
        lista_pareamento = [j["Nome"] for j in jogadores if j["Nome"] != chapeu_atribuido]
        mesas = []
        contador_mesa = 1
        
        # Se houver Chapéu, aloca-o na Mesa 1 de forma imediata e automatizada
        if chapeu_atribuido:
            mesas.append({
                "Mesa": contador_mesa,
                "Jogador1": chapeu_atribuido,
                "Jogador2": "CHAPÉU",
                "Status": "Concluído",
                "SetsJ1": 3, "SetsJ2": 0,
                "TentosJ1": 72, "TentosJ2": 0,
                "FloresJ1": 0, "FloresJ2": 0
            })
            # Atualiza os dados do jogador beneficiado pelo Chapéu imediatamente
            for j in dados["Jogadores"]:
                if j["Nome"] == chapeu_atribuido:
                    j["Pts"] += 3; j["Vit"] += 1; j["SetsPró"] += 3
                    j["SaldoSets"] += 3; j["TentPró"] += 72; j["SaldoTent"] += 72
                    j["Jogos"] += 1
            contador_mesa += 1

        # Algoritmo de emparelhamento por proximidade de pontos (Greedy Matching)
        while len(lista_pareamento) > 1:
            j1 = lista_pareamento.pop(0)
            par_encontrado = False
            
            for i, j2 in enumerate(lista_pareamento):
                if (j1, j2) not in confrontos_passados:
                    lista_pareamento.pop(i)
                    mesas.append({
                        "Mesa": contador_mesa,
                        "Jogador1": j1,
                        "Jogador2": j2,
                        "Status": "Pendente",
                        "SetsJ1": 0, "SetsJ2": 0,
                        "TentosJ1": 0, "TentosJ2": 0,
                        "FloresJ1": 0, "FloresJ2": 0
                    })
                    contador_mesa += 1
                    par_encontrado = True
                    break
            
            # Se não houver par inédito viável, força o casamento com o competidor mais próximo
            if not par_encontrado:
                j2 = lista_pareamento.pop(0)
                mesas.append({
                    "Mesa": contador_mesa,
                    "Jogador1": j1,
                    "Jogador2": j2,
                    "Status": "Pendente",
                    "SetsJ1": 0, "SetsJ2": 0,
                    "TentosJ1": 0, "TentosJ2": 0,
                    "FloresJ1": 0, "FloresJ2": 0
                })
                contador_mesa += 1

        return {"Rodada": num_rodada, "Mesas": mesas}

    def atualizar_estatisticas_suico(self, dados):
        """Zera e recalcula os dados do zero com base em todas as rodadas jogadas."""
        for j in dados["Jogadores"]:
            j["Pts"] = 0; j["Vit"] = 0; j["SaldoSets"] = 0; j["SetsPró"] = 0
            j["SaldoTent"] = 0; j["TentPró"] = 0; j["SaldoFlor"] = 0; j["FlorPró"] = 0
            j["Jogos"] = 0

        mapa = {j["Nome"]: j for j in dados["Jogadores"]}
        
        for r in dados.get("Rodadas", []):
            for m in r.get("Mesas", []):
                if m.get("Status") == "Concluído":
                    j1, j2 = m["Jogador1"], m["Jogador2"]
                    s1, s2 = int(m.get("SetsJ1", 0)), int(m.get("SetsJ2", 0))
                    t1, t2 = int(m.get("TentosJ1", 0)), int(m.get("TentosJ2", 0))
                    f1, f2 = int(m.get("FloresJ1", 0)), int(m.get("FloresJ2", 0))
                    
                    if j1 in mapa:
                        mapa[j1]["SetsPró"] += s1; mapa[j1]["TentPró"] += t1; mapa[j1]["FlorPró"] += f1
                        mapa[j1]["SaldoSets"] += (s1 - s2); mapa[j1]["SaldoTent"] += (t1 - t2)
                        mapa[j1]["SaldoFlor"] += (f1 - f2); mapa[j1]["Jogos"] += 1
                        if s1 > s2:
                            mapa[j1]["Pts"] += 3; mapa[j1]["Vit"] += 1
                            
                    if j2 in mapa:
                        mapa[j2]["SetsPró"] += s2; mapa[j2]["TentPró"] += t2; mapa[j2]["FlorPró"] += f2
                        mapa[j2]["SaldoSets"] += (s2 - s1); mapa[j2]["SaldoTent"] += (t2 - t1)
                        mapa[j2]["SaldoFlor"] += (f2 - f1); mapa[j2]["Jogos"] += 1
                        if s2 > s1:
                            mapa[j2]["Pts"] += 3; mapa[j2]["Vit"] += 1

    def gerar_fase_eliminatoria(self, dados, tamanho_corte):
        """Monta a primeira fase do Mata-Mata baseado no Rank do Suíço (1º x Último)."""
        classificados = self.processar_classificacao(dados)[:tamanho_corte]
        # Preenche com FOLGA_WO se não houver classificados suficientes para preencher a chave
        while len(classificados) < tamanho_corte:
            classificados.append({"Nome": "FOLGA_WO", "Entidade": "WO"})
            
        nome_fase = self.obter_nome_fase_mata(tamanho_corte)
        mesas = []
        
        for i in range(tamanho_corte // 2):
            j1 = classificados[i]["Nome"]
            j2 = classificados[-(i + 1)]["Nome"]
            
            status = "Pendente"
            s1, s2, t1, t2 = 0, 0, 0, 0
            if j1 == "FOLGA_WO" or j2 == "FOLGA_WO":
                status = "Concluído"
                if j1 != "FOLGA_WO": s1, t1 = 3, 72
                else: s2, t2 = 3, 72
                
            mesas.append({
                "Mesa": i + 1,
                "Jogador1": j1,
                "Jogador2": j2,
                "Status": status,
                "SetsJ1": s1, "SetsJ2": s2,
                "TentosJ1": t1, "TentosJ2": t2,
                "FloresJ1": 0, "FloresJ2": 0
            })
            
        dados["FasesMataMata"] = {
            "FaseAtual": nome_fase,
            "Mesas": mesas,
            "HistoricoFases": []
        }
        return dados

    def avancar_estagio_eliminatorio(self, dados):
        """Processa os vencedores da rodada eliminatória e gera a árvore seguinte."""
        eliminatoria = dados.get("FasesMataMata", {})
        fase_velha = eliminatoria.get("FaseAtual", "")
        mesas_velhas = eliminatoria.get("Mesas", [])
        
        # Salva o estado atual no histórico antes do avanço
        eliminatoria["HistoricoFases"].append({
            "Fase": fase_velha,
            "Mesas": list(mesas_velhas)
        })
        
        vencedores = []
        for m in mesas_velhas:
            if int(m["SetsJ1"]) > int(m["SetsJ2"]): vencedores.append(m["Jogador1"])
            else: vencedores.append(m["Jogador2"])
            
        if fase_velha == "Grande Final & 3º Lugar":
            # Torneio encerrado. Define o pódio final
            m_final = mesas_velhas[0]
            m_terceiro = mesas_velhas[1] if len(mesas_velhas) > 1 else None
            
            campeao = m_final["Jogador1"] if m_final["SetsJ1"] > m_final["SetsJ2"] else m_final["Jogador2"]
            vice = m_final["Jogador2"] if m_final["SetsJ1"] > m_final["SetsJ2"] else m_final["Jogador1"]
            
            terceiro = "N/A"
            if m_terceiro:
                terceiro = m_terceiro["Jogador1"] if m_terceiro["SetsJ1"] > m_terceiro["SetsJ2"] else m_terceiro["Jogador2"]
                
            dados["PodioFinal"] = {"Campeao": campeao, "Vice": vice, "Terceiro": terceiro}
            dados["Status"] = "Encerrado"
            return dados
            
        if fase_velha == "Semifinal":
            # Cria simultaneamente a disputa de 1º e de 3º lugar
            perdedores = []
            for m in mesas_velhas:
                if int(m["SetsJ1"]) > int(m["SetsJ2"]): perdedores.append(m["Jogador2"])
                else: perdedores.append(m["Jogador1"])
                
            mesas_novas = [
                {
                    "Mesa": 1, "Jogador1": vencedores[0], "Jogador2": vencedores[1],
                    "Status": "Pendente", "SetsJ1": 0, "SetsJ2": 0, "TentosJ1": 0, "TentosJ2": 0, "FloresJ1": 0, "FloresJ2": 0
                },
                {
                    "Mesa": 2, "Jogador1": perdedores[0], "Jogador2": perdedores[1],
                    "Status": "Pendente", "SetsJ1": 0, "SetsJ2": 0, "TentosJ1": 0, "TentosJ2": 0, "FloresJ1": 0, "FloresJ2": 0
                }
            ]
            eliminatoria["FaseAtual"] = "Grande Final & 3º Lugar"
            eliminatoria["Mesas"] = mesas_novas
            return dados

        # Chaveamento lógico padrão (Quartas, Oitavas, etc.)
        mesas_novas = []
        tamanho_proximo = len(vencedores) // 2
        for i in range(tamanho_proximo):
            j1 = vencedores[i * 2]
            j2 = vencedores[i * 2 + 1]
            status = "Pendente"
            s1, s2, t1, t2 = 0, 0, 0, 0
            if j1 == "FOLGA_WO" and j2 == "FOLGA_WO":
                status = "Concluído"; j1 = "FOLGA_WO"
            elif j1 == "FOLGA_WO":
                status = "Concluído"; s2, t2 = 3, 72
            elif j2 == "FOLGA_WO":
                status = "Concluído"; s1, t1 = 3, 72
                
            mesas_novas.append({
                "Mesa": i + 1, "Jogador1": j1, "Jogador2": j2,
                "Status": status, "SetsJ1": s1, "SetsJ2": s2, "TentosJ1": t1, "TentosJ2": t2, "FloresJ1": 0, "FloresJ2": 0
            })
            
        eliminatoria["FaseAtual"] = self.obter_nome_fase_mata(len(vencedores))
        eliminatoria["Mesas"] = mesas_novas
        return dados

    def obter_nome_fase_mata(self, n):
        if n == 64: return "32-Avos de Final (Top 64)"
        if n == 32: return "Dezesseis-Avos de Final (Top 32)"
        if n == 16: return "Oitavas de Final"
        if n == 8: return "Quartas de Final"
        if n == 4: return "Semifinal"
        return "Mata-Mata"

motor_truco = MotorTruco()

# ==============================================================================
# ⏱️ 3. ENGINE DE SINCRO-CRONÔMETRO HÍBRIDO PERSISTENTE (JS + PYTHON)
# ==============================================================================
def obter_tempo_restante_dinamico():
    """Calcula e retorna com precisão matemática em segundos o tempo de jogo restante."""
    dados = gerenciador_dados.carregar_dados()
    c = dados.get("Cronometro", {})
    if not c.get("Ativo", False) or c.get("TimestampInicio") is None:
        return c.get("TempoRestanteSegundos", 2700), c
        
    tempo_decorrido = time.time() - c["TimestampInicio"]
    restante = int(c["TempoRestanteSegundos"] - tempo_decorrido)
    
    if restante <= 0:
        restante = 0
        c["Ativo"] = False
        c["FimRodada"] = True
        c["TempoRestanteSegundos"] = 0
        c["TimestampInicio"] = None
        gerenciador_dados.salvar_dados(dados)
    return restante, c

def injetar_cronometro_javascript(key_prefix="global"):
    """Injeta a interface gráfica animada do cronômetro acionada por JavaScript."""
    segundos_restantes, c_dados = obter_tempo_restante_dinamico()
    minutos = segundos_restantes // 60
    segundos = segundos_restantes % 60
    cor_alerta = "#ff4b4b" if segundos_restantes < 300 else ("#ffbf00" if segundos_restantes < 900 else "#00e676")
    
    label_status = "⏱️ CRONÔMETRO ATIVO" if c_dados.get("Ativo") else "⏸️ TEMPO CONGELADO"
    if c_dados.get("FimRodada"): label_status = "🚨 FIM DE RODADA COMPUTAÇÃO!"

    card_html = f"""
    <div id='cronometro-container-{key_prefix}' style='background: #111a24; border: 2px solid {cor_alerta}; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 20px;'>
        <div style='font-size: 10pt; color: #8892b0; letter-spacing: 2px; font-weight: bold;'>{label_status}</div>
        <div id='display-timer-{key_prefix}' style='font-size: 34pt; font-weight: 900; color: {cor_alerta}; font-family: "Courier New", monospace;'>
            {minutos:02d}:{segundos:02d}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    if c_dados.get("Ativo") and segundos_restantes > 0:
        js_code = f"""
        <script>
            (function() {{
                var totalSegundos = {segundos_restantes};
                var displayId = 'display-timer-{key_prefix}';
                var intervalId = setInterval(function() {{
                    if (totalSegundos <= 0) {{
                        clearInterval(intervalId);
                        return;
                    }}
                    totalSegundos--;
                    var mins = Math.floor(totalSegundos / 60);
                    var secs = totalSegundos % 60;
                    var strMins = mins < 10 ? '0' + mins : mins;
                    var strSecs = secs < 10 ? '0' + secs : secs;
                    var element = document.getElementById(displayId);
                    if (element) {{
                        element.innerText = strMins + ':' + strSecs;
                        if (totalSegundos < 300) {{
                            element.style.color = '#ff4b4b';
                        }} else if (totalSegundos < 900) {{
                            element.style.color = '#ffbf00';
                        }}
                    }}
                }}, 1000);
            }})();
        </script>
        """
        st.components.v1.html(js_code, height=0, width=0)

def obter_mesas_fase_atual(dados):
    if dados.get("Status") == "Mata-Mata" or dados.get("Fase") == "Mata-Mata":
        return dados.get("FasesMataMata", {}).get("Mesas", [])
    else:
        rodada_atual = dados.get("RodadaAtual", 1)
        if dados.get("Rodadas") and len(dados["Rodadas"]) >= rodada_atual:
            return dados["Rodadas"][rodada_atual - 1].get("Mesas", [])
    return []

# ==============================================================================
# 🎨 4. CSS INJETADO - ESTILIZAÇÃO E DESIGN RESPONSIVO (DARK MODE)
# ==============================================================================
st.set_page_config(page_title="Sistema de Gestão - Truco Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0d1117 !important;
        font-family: 'Inter', sans-serif;
        color: #c9d1d9;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #161b22;
        padding: 8px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        border-radius: 6px;
        background-color: #21262d;
        color: #8b949e !important;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #30363d;
        color: #ffffff !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffbf00 !important;
        color: #0d1117 !important;
    }
    
    /* Componentes de Mesas */
    .mesa-container {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        margin-bottom: 15px;
        overflow: hidden;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .mesa-header {
        background: #21262d;
        padding: 10px 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #30363d;
        font-weight: bold;
    }
    .mesa-status-concluido {
        background: #238636;
        color: white;
        font-size: 8pt;
        padding: 3px 8px;
        border-radius: 20px;
    }
    .mesa-status-pendente {
        background: #d29922;
        color: black;
        font-size: 8pt;
        padding: 3px 8px;
        border-radius: 20px;
    }
    .mesa-corpo { padding: 15px; }
    .jogador-linha {
        display: flex;
        justify-content: space-between;
        padding: 8px 10px;
        border-radius: 6px;
        margin-bottom: 6px;
    }
    .vencedor-destaque { background: rgba(35, 134, 54, 0.2) !important; border-left: 4px solid #238636; font-weight: bold; color: #58a6ff;}
    .perdedor-destaque { background: rgba(240, 128, 128, 0.05); opacity: 0.6; }
    .jogador-nome { font-size: 11pt; }
    .jogador-resultado { font-size: 10pt; color: #8b949e; }
    
    /* Configuração de Súmulas Térmicas */
    @media print {
        body * { visibility: hidden; background: white !important; color: black !important; }
        .secao-impressao-sumulas, .secao-impressao-sumulas * { visibility: visible; }
        .secao-impressao-sumulas { position: absolute; left: 0; top: 0; width: 80mm; }
        .cartao-sumula-print { width: 76mm; padding: 4mm 2mm; page-break-after: always; border-bottom: 1px dashed #000; font-family: 'Courier New', monospace; }
        .tabela-sumula-print { width: 100%; border-collapse: collapse; margin-top: 5px; }
        .tabela-sumula-print th, .tabela-sumula-print td { border: 1px solid #000; font-size: 9pt; text-align: center; padding: 3px; }
        .texto-dupla-print { font-size: 8pt !important; text-align: left !important; overflow: hidden; }
    }
    .secao-impressao-sumulas { visibility: hidden; position: absolute; height: 0; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🎮 5. AUTENTICAÇÃO E BARRA LATERAL (SIDEBAR DE CONTROLE)
# ==============================================================================
dados = gerenciador_dados.carregar_dados()

with st.sidebar:
    st.markdown("<h1 style='text-align:center; color:#ffbf00; font-size:18pt;'>🎴 TRUCO TOURNAMENT</h1>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 🔐 Controle de Acesso")
    perfil = st.radio("Perfil de Usuário:", ["Mesa de Operação (Público)", "Administrador"], horizontal=True)
    st.session_state.perfil_usuario = perfil
    
    st.markdown("---")
    st.markdown("### 📊 Status Operacional")
    st.info(f"**Competição:** {dados.get('NomeTorneio')}\n\n**Estado:** {dados.get('Status')}\n\n**Fase:** {dados.get('Fase')} (Rodada {dados.get('RodadaAtual', 0)})")
    st.markdown("<div style='text-align:center; color:#58a6ff; font-size:9pt;'>Truco Manager v2026.1</div>", unsafe_allow_html=True)

# Definição dinâmica das abas visíveis baseadas no estado atual do campeonato
status_atual = dados.get("Status", "Configuração")

if status_atual == "Configuração":
    abas_lista = ["⚙️ Painel Inicial", "📝 Inscrição Online", "🏆 Galeria de Campeões"]
elif status_atual == "Em Andamento" or status_atual == "Mata-Mata":
    if st.session_state.perfil_usuario == "Administrador":
        abas_lista = ["⚔️ Lançar Mesas", "📊 Classificação", "🌳 Árvore Playoffs", "🏆 Galeria de Campeões"]
    else:
        abas_lista = ["📊 Classificação", "🌳 Árvore Playoffs", "🏆 Galeria de Campeões"]
else:  # Encerrado
    abas_lista = ["🏆 Galeria de Campeões", "📊 Classificação", "🌳 Árvore Playoffs"]

abas_criadas = st.tabs(abas_lista)
aba_index = 0

# ==============================================================================
# # --- 2. ABA: INSCRIÇÃO ONLINE (SÓ APARECE EM CONFIGURAÇÃO) ---
# ==============================================================================
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
# # --- 3. ABA: PAINEL INICIAL DE CONFIGURAÇÃO (SÓ ATIVA ANTES DO START) ---
# ==============================================================================
if "⚙️ Painel Inicial" in abas_lista:
    with abas_criadas[aba_index]:
        st.markdown("<h2 style='color: #ffbf00 !important;'>⚙️ Configuração Primária do Campeonato</h2>", unsafe_allow_html=True)
        nome_torneio_input = st.text_input("Nome Principal da Competição:", value=dados.get('NomeTorneio', ''))
        tempo_limite = st.number_input("Tempo do Cronômetro por Rodada (minutos):", min_value=5, max_value=120, value=int(dados.get('TempoLimiteMinutos', 45)))
         
        st.markdown("---")
        st.markdown("### 👥 Gerenciador Ativo de Inscrições")
        opcao_cadastro = st.radio("Selecione o método operacional de cadastro:", ["Individual Manual", "🚀 Importação Rápida em Lote (Copia e Cola)"], horizontal=True)
         
        if opcao_cadastro == "Individual Manual":
            col_cad1, col_cad2 = st.columns(2)
            with col_cad1: novo_nome = st.text_input("Nome do Competidor / Identificação da Dupla:", key="cad_nome").strip().upper()
            with col_cad2: nova_ent = st.text_input("Entidade / Clube / Cidade de Origem:", key="cad_ent").strip().upper()
                 
            if st.button("📥 Cadastrar Competidor Individual"):
                if not novo_nome: st.error("Erro: O campo de nome não pode ficar em branco.")
                else:
                    nomes_existentes = [j['Nome'] for j in dados.get('Jogadores', [])]
                    if novo_nome in nomes_existentes: st.warning(f"Aviso: '{novo_nome}' já se encontra cadastrado.")
                    else:
                        ent_f = nova_ent if nova_ent else "MESA"
                        dados['Jogadores'].append({'Nome': novo_nome, 'Entidade': ent_f})
                        gerenciador_dados.salvar_dados(dados)
                        st.success(f"🎉 '{novo_nome}' integrated!")
                        st.rerun()
        else:
            st.markdown("> **Instruções do Lote:** Insira **um competidor por linha**.")
            entidade_lote = st.text_input("Entidade / Cidade padrão atribuída a este lote:", value="MESA", key="ent_lote").strip().upper()
            texto_lote = st.text_area("Cole as linhas com os nomes dos competidores aqui:", height=180)
             
            if st.button("⚡ Executar Processamento e Cadastro em Massa"):
                if not texto_lote.strip(): st.error("Erro: Caixa vazia.")
                else:
                    linhas = [l.strip().upper() for l in texto_lote.split("\n") if l.strip()]
                    cadastrados_agora = 0
                    nomes_existentes = [j['Nome'] for j in dados.get('Jogadores', [])]
                    for linha in linhas:
                        if linha not in nomes_existentes:
                            dados['Jogadores'].append({'Nome': linha, 'Entidade': entidade_lote})
                            nomes_existentes.append(linha)
                            cadastrados_agora += 1
                    if cadastrados_agora > 0:
                        gerenciador_dados.salvar_dados(dados)
                        st.success(f"🔥 Carga Executada! {cadastrados_agora} novos competidores!")
                        time.sleep(0.5)
                        st.rerun()

        st.markdown("---")
        if st.button("🚀 BLOQUEAR INSCRIÇÕES E GERAR CHAVE (START)"):
            if len(dados.get('Jogadores', [])) < 2:
                st.error("Erro Crítico: Mínimo de 2 competidores.")
            else:
                for j in dados['Jogadores']:
                    j['Pts'] = 0; j['Vit'] = 0; j['SaldoSets'] = 0; j['SetsPró'] = 0
                    j['SaldoTent'] = 0; j['TentPró'] = 0; j['SaldoFlor'] = 0; j['FlorPró'] = 0
                    j['Bukes'] = 0; j['Jogos'] = 0

                dados['NomeTorneio'] = nome_torneio_input if nome_torneio_input else "Torneio de Truco"
                dados['TempoLimiteMinutos'] = tempo_limite
                dados['Status'] = 'Em Andamento'
                dados['RodadaAtual'] = 1
                dados['Cronometro'] = {
                    'TempoRestanteSegundos': tempo_limite * 60,
                    'Ativo': True,
                    'FimRodada': False,
                    'TimestampInicio': time.time()
                }
                dados['Rodadas'] = []
                 
                try:
                    primeira_rodada = motor_truco.gerar_rodada_suica(dados, 1)
                    if primeira_rodada is not None:
                        dados['Rodadas'].append(primeira_rodada)
                        gerenciador_dados.salvar_dados(dados)
                        st.success("Campeonato Oficial Iniciado com Sucesso!")
                        st.rerun()
                except Exception as ex:
                    st.error(f"❌ Erro ao processar chaveamento: {str(ex)}")
                     
        st.markdown("### 👥 Gerenciador Analítico de Inscritos (Exclusão)")
        if dados.get('Jogadores'):
            for idx_j, jog in enumerate(dados['Jogadores']):
                col_j1, col_j2 = st.columns([3, 1])
                with col_j1: st.write(f"👤 {jog['Nome']} — 🏢 {jog['Entidade']}")
                with col_j2:
                    if st.button("❌ Remover", key=f"config_rem_{idx_j}"):
                        dados['Jogadores'].pop(idx_j)
                        gerenciador_dados.salvar_dados(dados)
                        st.rerun()
    aba_index += 1


# ==============================================================================
# ⚔️ 5ª e 6ª PARTE UNIFICADAS: CENTRAL DE LANÇAMENTO E CONTROLE GERAL
# ==============================================================================
if "⚔️ Lançar Mesas" in abas_lista:
    with abas_criadas[aba_index]:
        # TOPO: CRONÔMETRO DO TORNEIO (Sempre Visível)
        injetar_cronometro_javascript(key_prefix="lancador")
         
        # CORREÇÃO DA BUSCA: Decide se renderiza mesas do Mata-Mata ou do Suíço clássico
        if dados.get('Status') == 'Mata-Mata' or dados.get('Fase') == 'Mata-Mata':
            st.markdown(f"<h2 style='color: #ffbf00 !important;'>⚔️ Gerenciamento da Fase Eliminatória (Mata-Mata)</h2>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h2 style='color: #ffbf00 !important;'>⚔️ Gerenciamento da {dados.get('RodadaAtual', 1)}ª Rodada</h2>", unsafe_allow_html=True)
         
        # CHAMA A FUNÇÃO AUXILIAR UNIFICADA PARA CAPTURAR AS MESAS ATIVAS
        mesas = obter_mesas_fase_atual(dados)
         
        if mesas:
            col_tit, col_imp = st.columns([3, 1])
            with col_imp:
                if st.button("🖨️ IMPRIMIR SÚMULAS (ELGIN I9)", use_container_width=True):
                    st.components.v1.html("<script>window.print();</script>", height=0, width=0)
             
            # Renderizador estruturado Oculto para Impressora Térmica de 80mm
            html_impressao = f"<div class='secao-impressao-sumulas'>"
            for m in mesas:
                if m.get('Jogador1') == "CHAPÉU" or m.get('Jogador2') == "CHAPÉU": continue 
                html_impressao += f"""
                <div class='cartao-sumula-print'>
                    <div style='text-align:center; font-weight:bold; font-size:11pt; border-bottom:1px solid #000;'>{dados.get('NomeTorneio', 'TORNEIO DE TRUCO')}</div>
                    <div style='display:flex; justify-content:space-between; margin-top:5px; font-weight:bold; font-size:11pt;'>
                        <span>🎴 MESA {m.get('Mesa')}</span><span>RODADA ATUAL</span>
                    </div>
                    <table class='tabela-sumula-print'>
                        <thead><tr><th style='width: 50%; text-align:left;'>COMPETIDOR</th><th style='width:16%;'>SET</th><th style='width:16%;'>TT</th><th style='width:18%;'>FLOR</th></tr></thead>
                        <tbody>
                            <tr><td class='texto-dupla-print'>{m.get('Jogador1')}</td><td>[ &nbsp;]</td><td>[ &nbsp; ]</td><td>[ &nbsp; ]</td></tr>
                            <tr><td class='texto-dupla-print'>{m.get('Jogador2')}</td><td>[ &nbsp;]</td><td>[ &nbsp; ]</td><td>[ &nbsp; ]</td></tr>
                        </tbody>
                    </table>
                    <div style='margin-top:12px; font-size:8pt; font-weight:bold; text-align:left; line-height:1.4;'>✍️ Ass: _______________________________<br>Juiz: _________________</div>
                </div>
                """
            html_impressao += "</div>"
            st.markdown(html_impressao, unsafe_allow_html=True)
             
            # CORREÇÃO CENTRAL: LISTAGEM E RENDERIZAÇÃO DAS MESAS ATIVAS
            col_mesa1, col_mesa2 = st.columns(2)
            for idx, m in enumerate(mesas):
                col_alvo = col_mesa1 if idx % 2 == 0 else col_mesa2
                with col_alvo:
                    status_classe = "mesa-status-concluido" if m.get('Status') == 'Concluído' else "mesa-status-pendente"
                     
                    vencedor_j1 = ""
                    vencedor_j2 = ""
                    if m.get('Status') == 'Concluído':
                        if int(m.get('SetsJ1', 0)) > int(m.get('SetsJ2', 0)):
                            vencedor_j1 = "vencedor-destaque"
                            vencedor_j2 = "perdedor-destaque"
                        else:
                            vencedor_j1 = "perdedor-destaque"
                            vencedor_j2 = "vencedor-destaque"
                    
                    st.markdown(f"""
                        <div class="mesa-container">
                            <div class="mesa-header">
                                <span>🎴 Mesa {m.get('Mesa')}</span>
                                <span class="{status_classe}">{m.get('Status', '').upper()}</span>
                            </div>
                            <div class="mesa-corpo">
                                <div class="jogador-linha {vencedor_j1}">
                                    <span class="jogador-nome">👤 {m.get('Jogador1')}</span>
                                    <span class="jogador-resultado">{m.get('SetsJ1', 0)} Set(s) ({m.get('TentosJ1', 0)} T / {m.get('FloresJ1', 0)} F)</span>
                                </div>
                                <div class="jogador-linha {vencedor_j2}">
                                    <span class="jogador-nome">👤 {m.get('Jogador2')}</span>
                                    <span class="jogador-resultado">{m.get('SetsJ2', 0)} Set(s) ({m.get('TentosJ2', 0)} T / {m.get('FloresJ2', 0)} F)</span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                     
                    if m.get('Jogador1') == "CHAPÉU" or m.get('Jogador2') == "CHAPÉU": 
                        continue
                         
                    # FORMULÁRIO OPERACIONAL DE CADA MESA
                    with st.expander(f"📝 Lançar Placar - Mesa {m.get('Mesa')}"):
                        rodada_id = "mata" if (dados.get('Status') == 'Mata-Mata' or dados.get('Fase') == 'Mata-Mata') else dados.get('RodadaAtual', 1)
                        form_key = f"form_mesa_{m.get('Mesa')}_{rodada_id}"
                         
                        opcoes_sets = [
                            "Aguardando...", 
                            f"{m.get('Jogador1')} 2 x 0 (Ganha 3x0 - 72 Tentos)", 
                            f"{m.get('Jogador2')} 2 x 0 (Ganha 3x0 - 72 Tentos)", 
                            f"{m.get('Jogador1')} 2 x 1", 
                            f"{m.get('Jogador2')} 2 x 1"
                        ]
                        escolha_set = st.selectbox("Qual o placar em Sets?", opcoes_sets, key=f"sel_{form_key}")
                         
                        t1_int, t2_int = 0, 0
                         
                        if escolha_set != "Aguardando...":
                            if "2 x 0" in escolha_set:
                                if escolha_set.startswith(m.get('Jogador1')):
                                    st.success(f"🏆 {m.get('Jogador1')} ganha por 3x0 (72 Tentos fixos).")
                                    t1_int = 72
                                    t2_int = st.number_input(f"Tentos feitos por {m.get('Jogador2')} (Máximo 46):", min_value=0, max_value=46, value=0, key=f"t2_{form_key}")
                                else:
                                    st.success(f"🏆 {m.get('Jogador2')} ganha por 3x0 (72 Tentos fixos).")
                                    t2_int = 72
                                    t1_int = st.number_input(f"Tentos feitos por {m.get('Jogador1')} (Máximo 46):", min_value=0, max_value=46, value=0, key=f"t1_{form_key}")
                                     
                            elif "2 x 1" in escolha_set:
                                col_t1, col_t2 = st.columns(2)
                                with col_t1: t1_raw = st.text_input(f"Tentos de {m.get('Jogador1')}", value=str(m.get('TentosJ1', 0)), key=f"t1_{form_key}")
                                with col_t2: t2_raw = st.text_input(f"Tentos de {m.get('Jogador2')}", value=str(m.get('TentosJ2', 0)), key=f"t2_{form_key}")
                                try:
                                    t1_int, t2_int = int(t1_raw), int(t2_raw)
                                except:
                                    t1_int, t2_int = 0, 0
                         
                        col_f1, col_f2 = st.columns(2)
                        with col_f1: f1_num = st.number_input(f"🌸 Flores de {m.get('Jogador1')}", min_value=0, value=int(m.get('FloresJ1', 0)), step=1, key=f"f1_{form_key}")
                        with col_f2: f2_num = st.number_input(f"🌸 Flores de {m.get('Jogador2')}", min_value=0, value=int(m.get('FloresJ2', 0)), step=1, key=f"f2_{form_key}")
                         
                        if st.button("Confirmar e Salvar Mesa", key=f"btn_{form_key}"):
                            if escolha_set != "Aguardando...":
                                # CORREÇÃO SALVAMENTO: Grava de forma segura no nó estrutural correto
                                if dados.get('Status') == 'Mata-Mata' or dados.get('Fase') == 'Mata-Mata':
                                    alvo = dados['FasesMataMata']['Mesas'][idx]
                                else:
                                    alvo = dados['Rodadas'][dados['RodadaAtual'] - 1]['Mesas'][idx]
                                     
                                alvo['Status'] = 'Concluído'
                                alvo['FloresJ1'] = f1_num
                                alvo['FloresJ2'] = f2_num
                                 
                                if escolha_set.startswith(alvo['Jogador1']):
                                    alvo['SetsJ1'] = 3 if "2 x 0" in escolha_set else 2
                                    alvo['SetsJ2'] = 0 if "2 x 0" in escolha_set else 1
                                    alvo['TentosJ1'] = t1_int
                                    alvo['TentosJ2'] = t2_int
                                else:
                                    alvo['SetsJ1'] = 0 if "2 x 0" in escolha_set else 1
                                    alvo['SetsJ2'] = 3 if "2 x 0" in escolha_set else 2
                                    alvo['TentosJ1'] = t1_int
                                    alvo['TentosJ2'] = t2_int
                                     
                                segundos_restantes_agora, _ = obter_tempo_restante_dinamico()
                                dados['Cronometro']['TempoRestanteSegundos'] = segundos_restantes_agora
                                if dados['Cronometro']['Ativo']:
                                    dados['Cronometro']['TimestampInicio'] = time.time()
                                     
                                gerenciador_dados.salvar_dados(dados)
                                st.success(f"Mesa {m.get('Mesa')} Lançada com Sucesso!")
                                st.rerun()
        else:
            st.info("Nenhum jogo ativo cadastrado no sistema para esta fase.")

        # ==================================================================
        # ⚙️ RODAPÉ: PAINEL DO DIRETOR INTEGRADO (EXCLUSIVO ADMINISTRADOR)
        # ==================================================================
        if st.session_state.perfil_usuario == "Administrador":
            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.markdown("### ⚙️ Painel de Controle de Mesa do Diretor")
             
            restante_real, c_dados = obter_tempo_restante_dinamico()
            c_ativo = c_dados.get('Ativo', False)
             
            # CONTROLES DO CRONÔMETRO HÍBRIDO
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("⏸️ Congelar Cronômetro" if c_ativo else "▶️ Ativar Cronômetro", use_container_width=True):
                    if c_ativo:
                        dados['Cronometro']['TempoRestanteSegundos'] = restante_real
                        dados['Cronometro']['Ativo'] = False
                        dados['Cronometro']['TimestampInicio'] = None
                    else:
                        dados['Cronometro']['TempoRestanteSegundos'] = restante_real
                        dados['Cronometro']['Ativo'] = True
                        dados['Cronometro']['TimestampInicio'] = time.time()
                    gerenciador_dados.salvar_dados(dados)
                    st.rerun()
            with col_btn2:
                if st.button("🔄 Reiniciar Tempo Padrão", use_container_width=True):
                    dados['Cronometro']['TempoRestanteSegundos'] = dados['TempoLimiteMinutos'] * 60
                    dados['Cronometro']['FimRodada'] = False
                    if dados['Cronometro']['Ativo']:
                        dados['Cronometro']['TimestampInicio'] = time.time()
                    gerenciador_dados.salvar_dados(dados)
                    st.rerun()
             
            st.markdown("---")
            
            # VERIFICAÇÃO DE CONCLUSÃO DE TODAS AS MESAS
            todas_concluidas = True
            if mesas:
                for m in mesas:
                    if m.get('Status') != 'Concluído': 
                        todas_concluidas = False
             
            # LÓGICA DE TRANSIÇÃO E CONTROLE DAS RODADAS
            # --- FASE 1: SISTEMA SUÍÇO (Fase Classificatória) ---
            if dados.get('Status') != 'Mata-Mata' and dados.get('Fase') != 'Mata-Mata':
                if todas_concluidas and mesas:
                    # REGRA COMUM: Avanço de rodadas normais do suíço até a Rodada 5
                    rod_atual = dados.get('RodadaAtual', 1)
                    if rod_atual < 5:
                        if st.button(f"🎲 Fechar Rodada {rod_atual} e Emparceirar Rodada {rod_atual + 1} ⏭️", type="primary", use_container_width=True):
                            motor_truco.atualizar_estatisticas_suico(dados)
                            proxima_r = motor_truco.gerar_rodada_suica(dados, rod_atual + 1)
                            if proxima_r:
                                dados['Rodadas'].append(proxima_r)
                                dados['RodadaAtual'] = rod_atual + 1
                                # Reseta cronômetro para a nova rodada automaticamente
                                dados['Cronometro']['TempoRestanteSegundos'] = dados['TempoLimiteMinutos'] * 60
                                dados['Cronometro']['FimRodada'] = False
                                if dados['Cronometro']['Ativo']:
                                    dados['Cronometro']['TimestampInicio'] = time.time()
                                gerenciador_dados.salvar_dados(dados)
                                st.success(f"Rodada {rod_atual + 1} emparceirada!")
                                st.rerun()
                    
                    # REGRA EXTRA: SE CHEGOU NA ÚLTIMA RODADA DO SUÍÇO (RODADA 5)
                    else:
                        st.success("🏁 **Rodada 5 do Sistema Suíço Concluída!** O corte para o Mata-Mata está liberado.")
                         
                        tamanho_mata_mata = st.selectbox(
                            "Escolha o tamanho do chaveamento eliminatório:",
                            ["32-Avos de Final (Top 64)", "Dezesseis-Avos de Final (Top 32)", "Oitavas de Final (Top 16)", "Quartas de Final (Top 8)", "Semifinal (Top 4)"],
                            key="sel_tamanho_playoffs"
                        )
                         
                        if st.button("🏆 Iniciar Fase Eliminatória (Mata-Mata) 🔥", type="primary", use_container_width=True):
                            motor_truco.atualizar_estatisticas_suico(dados)
                            dados['Status'] = 'Mata-Mata'
                            dados['Fase'] = 'Mata-Mata'
                             
                            tamanho_map = {
                                "32-Avos de Final (Top 64)": 64,
                                "Dezesseis-Avos de Final (Top 32)": 32,
                                "Oitavas de Final (Top 16)": 16,
                                "Quartas de Final (Top 8)": 8,
                                "Semifinal (Top 4)": 4
                            }
                            v_tamanho = tamanho_map.get(tamanho_mata_mata, 16)
                             
                            try:
                                retorno_dados = motor_truco.gerar_fase_eliminatoria(dados, v_tamanho)
                                if retorno_dados is not None:
                                    dados = retorno_dados
                                 
                                dados['Status'] = 'Mata-Mata'
                                dados['Fase'] = 'Mata-Mata'
                                 
                                st.session_state.dados = dados
                                gerenciador_dados.salvar_dados(dados)
                                 
                                st.success("Playoffs Gerados com Sucesso!")
                                st.rerun()
                                 
                            except Exception as e:
                                st.error(f"Erro Crítico ao acionar o motor de chaves: {str(e)}")

            # --- FASE 2: MATA-MATA (Independente do Suíço) ---
            elif dados.get('Status') == 'Mata-Mata' or dados.get('Fase') == 'Mata-Mata':
                fase_atual_nome = dados.get('FasesMataMata', {}).get('FaseAtual', '')
                mesas_mata = dados.get('FasesMataMata', {}).get('Mesas', [])
                 
                # --- CASO A: ESTAMOS NA GRANDE FINAL & 3º LUGAR ---
                if fase_atual_nome == 'Grande Final & 3º Lugar':
                    st.success("🏆 **A Grande Final e a disputa de 3º Lugar terminaram!** O torneio está pronto para ser encerrado.")
                     
                    if st.button("🏁 ENCERRAR CAMPEONATO E SALVAR HISTÓRICO", type="primary", use_container_width=True):
                        try:
                            dados = motor_truco.avancar_estagio_eliminatorio(dados)
                            podio = dados.get('PodioFinal', {})
                             
                            if 'HistoricoCampeoes' not in dados:
                                dados['HistoricoCampeoes'] = []
                                 
                            # AJUSTE DE COMPATIBILIDADE: Mapeamento individualizado de chaves para a Galeria
                            dados['HistoricoCampeoes'].append({
                                'Torneio': dados.get('NomeTorneio', 'Torneio de Truco'),
                                'Campeao': podio.get('Campeao', 'N/A'),
                                'Vice': podio.get('Vice', 'N/A'),
                                'Terceiro': podio.get('Terceiro', 'N/A'),
                                'Data': datetime.now().strftime("%d/%m/%Y")
                            })
                             
                            st.session_state.dados = dados
                            gerenciador_dados.salvar_dados(dados)
                            st.success("Campeonato Encerrado! Dados enviados para a Galeria.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Erro ao encerrar o campeonato: {str(ex)}")
                             
                # --- CASO B: OUTRA FASE QUALQUER (Oitavas, Quartas, Semifinal...) ---
                else:
                    st.success(f"🏆 Todas as mesas da fase '{fase_atual_nome}' foram concluídas!")
                     
                    if st.button("⏭️ AVANÇAR ETAPA DO MATA-MATA", type="primary", use_container_width=True):
                        try:
                            if 'FloresAcumuladasMata' not in dados:
                                dados['FloresAcumuladasMata'] = {}
                                 
                            for m in mesas_mata:
                                j1, j2 = m['Jogador1'], m['Jogador2']
                                if j1 != "FOLGA_WO":
                                    dados['FloresAcumuladasMata'][j1] = dados['FloresAcumuladasMata'].get(j1, 0) + int(m.get('FloresJ1', 0))
                                if j2 != "FOLGA_WO":
                                    dados['FloresAcumuladasMata'][j2] = dados['FloresAcumuladasMata'].get(j2, 0) + int(m.get('FloresJ2', 0))
                             
                            dados = motor_truco.avancar_estagio_eliminatorio(dados)
                            st.session_state.dados = dados
                            gerenciador_dados.salvar_dados(dados)
                            st.toast("Playoffs avançados!", icon="⚔️")
                            time.sleep(0.5)
                            rerun_sucesso = True
                        except Exception as ex:
                            st.error(f"Erro ao computar avanço dos playoffs: {str(ex)}")
                             
                if 'rerun_sucesso' in locals():
                    st.rerun()

            # ==========================================================================
            # 🔥 ZONA DE GERENCIAMENTO GERAL (Abaixo das condicionais e sempre visível)
            # ==========================================================================
            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.markdown("### 🛠️ Painel de Controle e Manutenção Geral")
             
            col_adm1, col_adm2 = st.columns(2)
             
            with col_adm1:
                # --- BOTÃO: LANÇAR MANUALLY NO HISTÓRICO ---
                if st.button("🏆 Forçar Gravação do Pódio na Galeria", use_container_width=True, help="Registra os líderes atuais diretamente no histórico/galeria de forma manual"):
                    try:
                        podio = dados.get('PodioFinal', {})
                        lista_classificada = motor_truco.processar_classificacao(dados)
                         
                        # Define quem são as 3 duplas/jogadores de forma isolada
                        if podio and podio.get('Campeao'):
                            c1 = podio.get('Campeao')
                            c2 = podio.get('Vice')
                            c3 = podio.get('Terceiro')
                        elif lista_classificada:
                            c1 = lista_classificada[0]['Nome'] if len(lista_classificada) > 0 else "N/A"
                            c2 = lista_classificada[1]['Nome'] if len(lista_classificada) > 1 else "N/A"
                            c3 = lista_classificada[2]['Nome'] if len(lista_classificada) > 2 else "N/A"
                        else:
                            c1, c2, c3 = "N/A", "N/A", "N/A"
                             
                        if 'HistoricoCampeoes' not in dados:
                            dados['HistoricoCampeoes'] = []
                             
                        # 🔥 SALVAMENTO COMPATÍVEL: Chaves mapeadas individualmente para a Aba Galeria ler
                        dados['HistoricoCampeoes'].append({
                            'Torneio': dados.get('NomeTorneio', 'Torneio de Truco'),
                            'Campeao': c1,
                            'Vice': c2,
                            'Terceiro': c3,
                            'Data': datetime.now().strftime("%d/%m/%Y")
                        })
                         
                        st.session_state.dados = dados
                        gerenciador_dados.salvar_dados(dados)
                        st.success("🏆 Pódio estruturado e gravado na galeria com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar pódio: {str(e)}")

                # --- BOTÃO: LIMPAR HISTÓRICO DE CAMPEÕES ---
                if st.button("🗑️ Limpar Galeria de Histórico", use_container_width=True, help="Apaga permanentemente todos os registros salvos na galeria"):
                    try:
                        dados['HistoricoCampeoes'] = []
                        st.session_state.dados = dados
                        gerenciador_dados.salvar_dados(dados)
                        st.success("A galeria de campeões foi zerada!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao limpar histórico: {str(e)}")

            with col_adm2:
                # --- BOTÃO: PURGAR BANCO DE DADOS ---
                st.markdown("<p style='color:#ff4b4b; font-weight:bold; margin-bottom:5px;'>⚠️ Ação Crítica:</p>", unsafe_allow_html=True)
                if st.button("❌ PURGAR BANCO DE DADOS (Zerar Sistema)", type="primary", use_container_width=True, help="Apaga o torneio atual e redefine o banco de dados completamente"):
                    try:
                        gerenciador_dados.limpar_banco_dados()
                         
                        if 'dados' in st.session_state: 
                            del st.session_state.dados
                             
                        st.success("O sistema foi totalmente resetado!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao zerar o sistema: {str(e)}")
        
        aba_index += 1

# ==============================================================================
# 📊 ABA: CLASSIFICAÇÃO / RANKING GERAL DOS COMPETIDORES
# ==============================================================================
if "📊 Classificação" in abas_lista:
    with abas_criadas[aba_index]:
        st.markdown("<h2 style='color: #ffbf00 !important;'>📊 Classificação Oficial do Torneio</h2>", unsafe_allow_html=True)
        
        # Mostra o Cronômetro na visualização de classificação também
        injetar_cronometro_javascript(key_prefix="ranking")
        
        lista_rank = motor_truco.processar_classificacao(dados)
        
        if lista_rank:
            df_exibicao = pd.DataFrame(lista_rank)
            
            # Renomeia as colunas para o usuário final de forma amigável
            df_exibicao = df_exibicao.rename(columns={
                "Nome": "Competidor/Dupla",
                "Entidade": "Entidade/Cidade",
                "Pts": "Pontos (V=3)",
                "Vit": "Vitórias",
                "SaldoSets": "Saldo Sets",
                "SetsPró": "Sets Pró",
                "SaldoTent": "Saldo Tentos",
                "TentPró": "Tentos Pró",
                "SaldoFlor": "Saldo Flores",
                "FlorPró": "Flores Pró",
                "Bukes": "Soma Buchholz",
                "Jogos": "Partidas"
            })
            
            # Adiciona coluna de Posição (Index + 1)
            df_exibicao.index = df_exibicao.index + 1
            df_exibicao.index.name = "Pos"
            
            # Exibe o dataframe estilizado na interface
            st.dataframe(df_exibicao[[
                "Competidor/Dupla", "Entidade/Cidade", "Pontos (V=3)", "Vitórias", 
                "Saldo Sets", "Sets Pró", "Saldo Tentos", "Tentos Pró", 
                "Saldo Flores", "Flores Pró", "Soma Buchholz", "Partidas"
            ]], use_container_width=True)
        else:
            st.info("Nenhum competidor classificado ou registrado no momento.")
    aba_index += 1

# ==============================================================================
# 🌳 ABA: ÁRVORE DO CHAVEAMENTO ELIMINATÓRIO (MATA-MATA)
# ==============================================================================
if "🌳 Árvore Playoffs" in abas_lista:
    with abas_criadas[aba_index]:
        st.markdown("<h2 style='color: #ffbf00 !important;'>🌳 Chaveamento Geral dos Playoffs</h2>", unsafe_allow_html=True)
        
        eliminatoria = dados.get("FasesMataMata", {})
        fase_atual = eliminatoria.get("FaseAtual", "")
        mesas_mata = eliminatoria.get("Mesas", [])
        historico_fases = eliminatoria.get("HistoricoFases", [])
        
        if not fase_atual and not historico_fases:
            st.info("A fase eliminatória (Mata-Mata) ainda não foi inicializada. Aguarde a conclusão da fase suíça.")
        else:
            # Renderiza as fases passadas salvas no histórico
            for fase_passada in historico_fases:
                st.markdown(f"### 📍 Estágio: {fase_passada.get('Fase')}")
                col1, col2 = st.columns(2)
                for idx_p, m_p in enumerate(fase_passada.get("Mesas", [])):
                    col_alvo = col1 if idx_p % 2 == 0 else col2
                    with col_alvo:
                        st.markdown(f"""
                        <div style='background:#1f242c; padding:10px; border-radius:8px; border-left:4px solid #ffbf00; margin-bottom:8px;'>
                            <b style='color:#ffbf00;'>Mesa {m_p.get('Mesa')}</b><br>
                            👤 {m_p.get('Jogador1')} ({m_p.get('SetsJ1')} Sets) x 
                            👤 {m_p.get('Jogador2')} ({m_p.get('SetsJ2')} Sets) <br>
                            <small style='color:#8b949e;'>Resultado Final (Concluído)</small>
                        </div>
                        """, unsafe_allow_html=True)
                st.markdown("---")
            
            # Renderiza a fase ativa/atual dos Playoffs
            st.markdown(f"### 🔥 Estágio Ativo: {fase_atual}")
            if mesas_mata:
                col1, col2 = st.columns(2)
                for idx_m, m_m in enumerate(mesas_mata):
                    col_alvo = col1 if idx_m % 2 == 0 else col2
                    with col_alvo:
                        status_txt = "CONCLUÍDO" if m_m.get("Status") == "Concluído" else "EM JOGO"
                        borda_cor = "#238636" if m_m.get("Status") == "Concluído" else "#d29922"
                        st.markdown(f"""
                        <div style='background:#161b22; padding:12px; border-radius:8px; border:1px solid #30363d; border-left:4px solid {borda_cor}; margin-bottom:10px;'>
                            <span style='float:right; font-size:8pt; background:{borda_cor}; color:white; padding:2px 6px; border-radius:10px;'>{status_txt}</span>
                            <b style='color:#58a6ff;'>Mesa {m_m.get('Mesa')}</b><br>
                            👤 {m_m.get('Jogador1')} <span style='color:#ffbf00;'>({m_m.get('SetsJ1')})</span> x 
                            👤 {m_m.get('Jogador2')} <span style='color:#ffbf00;'>({m_m.get('SetsJ2')})</span>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Mostra o Pódio se o campeonato estiver formalmente encerrado
            if dados.get("Status") == "Encerrado" and dados.get("PodioFinal"):
                st.markdown("---")
                st.markdown("<h2 style='text-align:center; color:#ffbf00;'>🏆 PÓDIO QUADRO DE HONRA 🏆</h2>", unsafe_allow_html=True)
                podio = dados.get("PodioFinal", {})
                
                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    st.markdown(f"<div style='background:rgba(212,175,55,0.1); border:2px solid #d4af37; padding:20px; border-radius:12px; text-align:center;'><h3>🥇 1º LUGAR</h3><b>{podio.get('Campeao')}</b></div>", unsafe_allow_html=True)
                with col_p2:
                    st.markdown(f"<div style='background:rgba(192,192,192,0.1); border:2px solid #c0c0c0; padding:20px; border-radius:12px; text-align:center;'><h3>🥈 2º LUGAR</h3><b>{podio.get('Vice')}</b></div>", unsafe_allow_html=True)
                with col_p3:
                    st.markdown(f"<div style='background:rgba(205,127,50,0.1); border:2px solid #cd7f32; padding:20px; border-radius:12px; text-align:center;'><h3>🥉 3º LUGAR</h3><b>{podio.get('Terceiro')}</b></div>", unsafe_allow_html=True)
    aba_index += 1

# ==============================================================================
# 🏆 ABA: GALERIA HISTÓRICA DE CAMPEÕES (MANTÉM MEMÓRIA ATIVA)
# ==============================================================================
if "🏆 Galeria de Campeões" in abas_lista:
    with abas_criadas[aba_index]:
        st.markdown("<h2 style='color: #ffbf00 !important;'>🏆 Galeria de Campeões & Histórico de Pódios</h2>", unsafe_allow_html=True)
        st.markdown("> Memória histórica dos pódios gravados e competições encerradas.")
        
        historico = dados.get("HistoricoCampeoes", [])
        
        if historico:
            df_hist = pd.DataFrame(historico)
            
            # Renomeia colunas para a tabela de exibição final ficar limpa
            df_hist = df_hist.rename(columns={
                'Torneio': 'Nome da Competição',
                'Campeao': '🥇 Campeão',
                'Vice': '🥈 Vice-Campeão',
                'Terceiro': '🥉 3º Colocado',
                'Data': '📅 Data de Encerramento'
            })
            
            # Inverte para mostrar os campeonatos mais recentes no topo
            df_hist = df_hist.iloc[::-1].reset_index(drop=True)
            df_hist.index = df_hist.index + 1
            
            st.table(df_hist[['Nome da Competição', '🥇 Campeão', '🥈 Vice-Campeão', '🥉 3º Colocado', '📅 Data de Encerramento']])
        else:
            st.info("Nenhum registro encontrado na galeria histórica até o momento.")
    aba_index += 1
