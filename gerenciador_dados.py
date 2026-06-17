import json
import os
import socket
from datetime import datetime

NOME_CRIADOR = "Eduardo Engenharia"
PASTA_DADOS = "banco_torneio"
ARQUIVO_ATIVO = os.path.join(PASTA_DADOS, "torneio_atual.json")
ARQUIVO_HISTORICO = os.path.join(PASTA_DADOS, "historico_torneios.json")

# Garante que a pasta física de armazenamento exista no servidor/máquina
if not os.path.exists(PASTA_DADOS):
    os.makedirs(PASTA_DADOS)

def obter_ip_da_rede():
    """Retorna o IP local da máquina para acesso na rede."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def carregar_dados():
    """Carrega o estado do torneio atual de forma segura."""
    if os.path.exists(ARQUIVO_ATIVO):
        try:
            with open(ARQUIVO_ATIVO, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if conteudo:
                    return json.loads(conteudo)
        except Exception as e:
            print(f"Erro ao ler torneio ativo, tentando backup: {e}")
            
    # Se falhar ou não existir, busca o último estado padrão
    return {
        'NomeTorneio': '', 
        'Status': 'Configuração',
        'Jogadores': [], 
        'RodadaAtual': 0, 
        'Rodadas': [],
        'TempoLimiteMinutos': 45,  
        'Cronometro': {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False, 'TimestampInicio': None},
        'HistoricoCampeoes': carregar_historico_campeoes()
    }

def salvar_dados(dados):
    """Salva os dados do torneio atual e faz um backup preventivo se estiver em andamento."""
    if not dados:
        return
        
    try:
        # 1. Garante que o histórico não suma da memória antes de salvar
        if 'HistoricoCampeoes' not in dados or not dados['HistoricoCampeoes']:
            dados['HistoricoCampeoes'] = carregar_historico_campeoes()

        # 2. Salva o arquivo principal de trabalho
        with open(ARQUIVO_ATIVO, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
            
        # 3. PENSANDO FORA DA CAIXA: Se o torneio está em andamento, faz cópia de segurança física datada
        if dados.get('Status') == 'Em Andamento':
            arquivo_backup = os.path.join(PASTA_DADOS, f"backup_rodada_{dados.get('RodadaAtual', 1)}.json")
            with open(arquivo_backup, "w", encoding="utf-8") as f_b:
                json.dump(dados, f_b, ensure_ascii=False, indent=4)
                
        # 4. Se o torneio foi Finalizado, joga ele em definitivo para o histórico permanente
        if dados.get('Status') == 'Finalizado':
            salvar_no_historico_permanente(dados)
            
    except Exception as e:
        print(f"Erro crítico ao salvar dados: {e}")

def carregar_historico_campeoes():
    """Carrega a galeria de campeões do arquivo permanente."""
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def salvar_no_historico_permanente(dados):
    """Guarda o resultado final do torneio em um arquivo separado que NUNCA é zerado."""
    historico = carregar_historico_campeoes()
    
    # Evita duplicar o mesmo torneio no histórico
    ja_existe = any(h.get('Torneio') == dados.get('NomeTorneio') for h in historico)
    
    if not ja_existe and dados.get('HistoricoCampeoes'):
        # Pega o último campeão adicionado
        novo_registro = dados['HistoricoCampeoes'][-1]
        historico.append(novo_registro)
        
        try:
            with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
                json.dump(historico, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erro ao atualizar histórico permanente: {e}")

def limpar_banco_dados():
    """Reseta o torneio atual para nova configuração, mas PRESERVA o histórico de campeões."""
    historico_salvo = carregar_historico_campeoes()
    
    # Apaga o arquivo ativo atual
    if os.path.exists(ARQUIVO_ATIVO):
        try:
            os.remove(ARQUIVO_ATIVO)
        except Exception:
            pass
            
    # Cria um novo esqueleto limpo, mantendo a história viva
    dados_limpos = {
        'NomeTorneio': '', 
        'Status': 'Configuração',
        'Jogadores': [], 
        'RodadaAtual': 0, 
        'Rodadas': [],
        'TempoLimiteMinutos': 45,  
        'Cronometro': {'TempoRestanteSegundos': 2700, 'Ativo': False, 'FimRodada': False, 'TimestampInicio': None},
        'HistoricoCampeoes': historico_salvo
    }
    
    salvar_dados(dados_limpos)
