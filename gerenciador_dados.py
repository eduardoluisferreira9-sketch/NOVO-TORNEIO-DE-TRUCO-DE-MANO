import json
import os
import socket

# Configuração dos arquivos de banco de dados locais (.json)
ARQUIVO_BACKUP = "banco_torneio.json"
ARQUIVO_GALERIA = "galeria_campeoes.json"

# 👑 SUA ASSINATURA DE DESENVOLVEDOR
NOME_CRIADOR = "Eduardo Luis Ferreira" 

# 🔐 CHAVE MESTRA DO ADMINISTRADOR (A senha para liberar o painel)
CHAVE_ADMINISTRADOR = "truco123"  

def salvar_dados(dados):
    """Salva o estado atual do torneio no disco para evitar perda de dados."""
    with open(ARQUIVO_BACKUP, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_dados():
    """Carrega o torneio salvo. Se o servidor cair, volta de onde parou."""
    if os.path.exists(ARQUIVO_BACKUP):
        try:
            with open(ARQUIVO_BACKUP, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def salvar_galeria(galeria):
    """Salva o histórico eterno de campeões na galeria."""
    with open(ARQUIVO_GALERIA, "w", encoding="utf-8") as f:
        json.dump(galeria, f, indent=4, ensure_ascii=False)

def carregar_galeria():
    """Busca o histórico de todos os torneios já finalizados."""
    if os.path.exists(ARQUIVO_GALERIA):
        try:
            with open(ARQUIVO_GALERIA, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def obter_ip_da_rede():
    """Detecta o IP local para os jogadores conectarem pelo celular."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"
