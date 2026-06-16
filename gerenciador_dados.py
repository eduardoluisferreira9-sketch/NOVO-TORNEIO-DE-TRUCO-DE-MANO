import json
import os
import socket

ARQUIVO_BACKUP = "banco_torneio.json"
ARQUIVO_GALERIA = "galeria_campeoes.json"

# 👑 ADICIONE SEU NOME AQUI PARA GRANDE ÊNFASE NO SISTEMA
NOME_CRIADOR = "Eduardo Luis Ferreira" 

def salvar_dados(dados):
    with open(ARQUIVO_BACKUP, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_dados():
    if os.path.exists(ARQUIVO_BACKUP):
        try:
            with open(ARQUIVO_BACKUP, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def salvar_galeria(galeria):
    with open(ARQUIVO_GALERIA, "w", encoding="utf-8") as f:
        json.dump(galeria, f, indent=4, ensure_ascii=False)

def carregar_galeria():
    if os.path.exists(ARQUIVO_GALERIA):
        try:
            with open(ARQUIVO_GALERIA, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def obter_ip_da_rede():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"