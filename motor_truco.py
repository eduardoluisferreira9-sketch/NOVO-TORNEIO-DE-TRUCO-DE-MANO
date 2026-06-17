import random
import gerenciador_dados

def processar_classificacao(dados):
    """Aplica os 9 critérios de desempate oficiais do Truco de Mano."""
    jogadores = dados.get('Jogadores', [])  # Lista de dicionários: [{'Nome': '...', 'Entidade': '...'}]
    rodadas = dados.get('Rodadas', [])
    
    tabela = {}
    for j in jogadores:
        nome = j['Nome']
        tabela[nome] = {
            'Nome': nome, 'Entidade': j.get('Entidade', 'N/A'),
            'Pts': 0, 'Vit': 0, 'SetsPró': 0, 'SetsContra': 0,
            'SaldoSets': 0, 'TentPró': 0, 'TentContra': 0, 'SaldoTent': 0,
            'FlorPró': 0, 'FlorContra': 0, 'SaldoFlor': 0, 'Jogos': 0, 'Bukes': 0
        }
        
    historico_confrontos = {j['Nome']: [] for j in jogadores}
    
    # Computa os resultados das mesas concluídas do Suíço (Fase Classificatória)
    for r in rodadas:
        for m in r.get('Mesas', []):
            if m.get('Status') == 'Concluído':
                j1, j2 = m['Jogador1'], m['Jogador2']
                s1, s2 = int(m.get('SetsJ1', 0)), int(m.get('SetsJ2', 0))
                t1, t2 = int(m.get('TentosJ1', 0)), int(m.get('TentosJ2', 0))
                f1, f2 = int(m.get('FloresJ1', 0)), int(m.get('FloresJ2', 0))
                
                if j1 != "CHAPÉU" and j1 in tabela:
                    historico_confrontos[j1].append(j2)
                    tabela[j1]['Jogos'] += 1
                    tabela[j1]['SetsPró'] += s1
                    tabela[j1]['SetsContra'] += s2
                    tabela[j1]['TentPró'] += t1
                    tabela[j1]['TentContra'] += t2
                    tabela[j1]['FlorPró'] += f1
                    tabela[j1]['FlorContra'] += f2
                    if s1 > s2:
                        tabela[j1]['Pts'] += 3
                        tabela[j1]['Vit'] += 1
                
                if j2 != "CHAPÉU" and j2 in tabela:
                    historico_confrontos[j2].append(j1)
                    tabela[j2]['Jogos'] += 1
                    tabela[j2]['SetsPró'] += s2
                    tabela[j2]['SetsContra'] += s1
                    tabela[j2]['TentPró'] += t2
                    tabela[j2]['TentContra'] += t1
                    tabela[j2]['FlorPró'] += f2
                    tabela[j2]['FlorContra'] += f1
                    if s2 > s1:
                        tabela[j2]['Pts'] += 3
                        tabela[j2]['Vit'] += 1

    # Calcula os saldos
    for j in tabela:
        tabela[j]['SaldoSets'] = tabela[j]['SetsPró'] - tabela[j]['SetsContra']
        tabela[j]['SaldoTent'] = tabela[j]['TentPró'] - tabela[j]['TentContra']
        tabela[j]['SaldoFlor'] = tabela[j]['FlorPró'] - tabela[j]['FlorContra']

    # Calcula o Buchholz (Bukes)
    for j in tabela:
        if j != "CHAPÉU":
            soma_pts_oponentes = 0
            for op in historico_confrontos[j]:
                if op != "CHAPÉU" and op in tabela:
                    soma_pts_oponentes += tabela[op]['Pts']
            tabela[j]['Bukes'] = soma_pts_oponentes

    # Remove o chapéu da exibição da tabela
    lista_tabela = [tabela[j] for j in tabela if j != "CHAPÉU"]
    
    # Ordenação oficial por prioridade de critérios
    lista_tabela.sort(key=lambda x: (
        x['Pts'], 
        x['Vit'], 
        x['SaldoSets'], 
        x['SetsPró'], 
        x['SaldoTent'], 
        x['TentPró'], 
        x['SaldoFlor'], 
        x['FlorPró'], 
        x['Bukes']
    ), reverse=True)
    
    return lista_tabela

def gerar_rodada_suica(dados, numero_rodada):
    """
    Realiza o sorteio ALEATÓRIO evitando repetição de jogos e confrontos da mesma entidade.
    TRAVA AUTOMÁTICA EM 5 RODADAS MÁXIMAS.
    """
    # 🆕 Trava de segurança: Se já passou de 5, bloqueia geração automática do Suíço
    if numero_rodada > 5:
        return None

    jogadores_cadastrados = dados.get('Jogadores', [])
    if not jogadores_cadastrados:
        return None
    
    # Mapeia quem é de qual entidade para consulta rápida
    entidades = {j['Nome']: j.get('Entidade', 'S/E') for j in jogadores_cadastrados}
    
    # Lista de nomes para o sorteio
    lista_sorteio = [j['Nome'] for j in jogadores_cadastrados]
    
    # Se for ímpar, adiciona o CHAPÉU
    if len(lista_sorteio) % 2 != 0:
        lista_sorteio.append("CHAPÉU")
        entidades["CHAPÉU"] = "SISTEMA"

    rodadas_passadas = dados.get('Rodadas', [])
    
    # Descobre o histórico de quem já jogou com quem
    historico_jogos = set()
    for r in rodadas_passadas:
        for m in r.get('Mesas', []):
            j1, j2 = m['Jogador1'], m['Jogador2']
            historico_jogos.add((j1, j2))
            historico_jogos.add((j2, j1))

    novas_mesas = []
    mesa_id = 1
    
    # Máximo de tentativas para evitar travamento matemático absoluto (sub-rotina de segurança)
    tentativas_globais = 0
    while len(lista_sorteio) > 0 and tentativas_globais < 100:
        tentativas_globais += 1
        
        # Copia a lista atual para tentar fazer os pares desta rodada
        pool = list(lista_sorteio)
        random.shuffle(pool) # Embaralha totalmente (Garante o Sorteio Aleatório)
        
        parceiros_da_rodada = []
        sucesso_rodada = True
        
        while len(pool) > 0:
            j1 = pool.pop(0)
            oponente_encontrado = None
            
            # Passo A: Tenta achar oponente ideal (Não repete jogo E não é da mesma Entidade)
            for candidato in pool:
                if (j1, candidato) not in historico_jogos:
                    if j1 == "CHAPÉU" or candidato == "CHAPÉU" or entidades[j1] != entidades[candidato]:
                        oponente_encontrado = candidato
                        break
            
            # Passo B: Se não achou do Passo A, aceita mesma entidade (mas mantém a trava de NÃO REPETIR CONFRONTO)
            if oponente_encontrado is None:
                for candidato in pool:
                    if (j1, candidato) not in historico_jogos:
                        oponente_encontrado = candidato
                        break
            
            # Se não achou ninguém válido, essa combinação quebrou. Reseta a rodada.
            if oponente_encontrado is None:
                sucesso_rodada = False
                break
            else:
                pool.remove(oponente_encontrado)
                parceiros_da_rodada.append((j1, oponente_encontrado))
        
        # Se conseguiu fechar todos os pares perfeitamente respeitando as travas, aplica as mesas
        if sucesso_rodada:
            for pair in parceiros_da_rodada:
                novas_mesas.append({
                    'Mesa': mesa_id,
                    'Jogador1': pair[0], 'Jogador2': pair[1],
                    'SetsJ1': 0, 'SetsJ2': 0,
                    'TentosJ1': 0, 'TentosJ2': 0,
                    'FloresJ1': 0, 'FloresJ2': 0,
                    'Status': 'Pendente'
                })
                mesa_id += 1
            lista_sorteio = [] # Quebra o laço principal
            
    # Se por pane matemática de fim de torneio travar (ex: impossível não repetir), gera o melhor possível
    if tentativas_globais >= 100 and len(lista_sorteio) > 0:
        random.shuffle(lista_sorteio)
        while len(lista_sorteio) > 1:
            j1 = lista_sorteio.pop(0)
            j2 = lista_sorteio.pop(0)
            novas_mesas.append({
                'Mesa': mesa_id, 'Jogador1': j1, 'Jogador2': j2,
                'SetsJ1': 0, 'SetsJ2': 0, 'TentosJ1': 0, 'TentosJ2': 0, 'FloresJ1': 0, 'FloresJ2': 0, 'Status': 'Pendente'
            })
            mesa_id += 1

    # Configuração automática e instantânea do Chapéu (Folga) - Ajustado para placar padrão de Sets
    for m in novas_mesas:
        if m['Jogador1'] == "CHAPÉU" or m['Jogador2'] == "CHAPÉU":
            m['Status'] = 'Concluído'
            if m['Jogador1'] == "CHAPÉU":
                m['SetsJ1'], m['SetsJ2'] = 0, 2
                m['TentosJ1'], m['TentosJ2'] = 0, 72  # Alinhado com a nova regra de 3x0 simulado
            else:
                m['SetsJ1'], m['SetsJ2'] = 2, 0
                m['TentosJ1'], m['TentosJ2'] = 72, 0

    return {
        'Numero': numero_rodada,
        'Status': 'Em Andamento',
        'Mesas': novas_mesas
    }

# 🆕 NOVAS FUNÇÕES ADICIONADAS PARA SUPORTE AO MATA-MATA

def iniciar_mata_mata(dados, tamanho_mata):
    """
    Pega os top 'tamanho_mata' (32, 16, 8, 4) da tabela de classificação oficial
    e gera a primeira rodada eliminatória seguindo o cruzamento Olímpico Puro:
    (1º vs Último, 2º vs Penúltimo...)
    """
    classificacao = processar_classificacao(dados)
    
    # Garante que temos competidores suficientes
    vagas = int(tamanho_mata)
    classificados = [c['Nome'] for c in classificacao[:vagas]]
    
    # Preenche com "W.O." se faltar gente para fechar a grade (Ex: escolheu 32 mas só tem 28)
    while len(classificados) < vagas:
        classificados.append("FOLGA_WO")
        
    # Define o nome legível da fase com base no tamanho inicial escolhido
    nomes_fases = {32: "32-Avos", 16: "Oitavas de Final", 8: "Quartas de Final", 4: "Semifinal"}
    nome_fase_atual = nomes_fases.get(vagas, f"Mata-{vagas}")
    
    mesas_mata = []
    mesa_id = 1
    
    # Cruzamento Olímpico: Espelhamento (i vs len-1-i)
    for i in range(vagas // 2):
        j1 = classificados[i]
        j2 = classificados[len(classificados) - 1 - i]
        
        status_inicial = 'Pendente'
        sets_j1, sets_j2, tentos_j1, tentos_j2 = 0, 0, 0, 0
        
        # Caso cruze com um competidor fantasma da folga, passa automático
        if j2 == "FOLGA_WO":
            status_inicial = 'Concluído'
            sets_j1, tentos_j1 = 2, 72
            
        mesas_mata.append({
            'Mesa': mesa_id,
            'Jogador1': j1, 'Jogador2': j2,
            'SetsJ1': sets_j1, 'SetsJ2': sets_j2,
            'TentosJ1': tentos_j1, 'TentosJ2': tentos_j2,
            'FloresJ1': 0, 'FloresJ2': 0,
            'Status': status_inicial
        })
        mesa_id += 1
        
    # Inicializa ou limpa a estrutura de chaves do Mata-Mata dentro dos dados globais
    dados['FasesMataMata'] = {
        'FaseAtual': nome_fase_atual,
        'Status': 'Em Andamento',
        'Mesas': mesas_mata
    }
    dados['Fase'] = 'Mata-Mata'
    return True

def avancar_fase_matamata(dados):
    """
    Pega os vencedores da fase atual do Mata-Mata e gera o cruzamento da próxima etapa.
    Mantém a ordem sequencial dos vencedores das chaves estabelecidas.
    """
    fase_atual = dados['FasesMataMata'].get('FaseAtual', '')
    mesas_anteriores = dados['FasesMataMata'].get('Mesas', [])
    
    # Coleta todos os vencedores na ordem das mesas
    vencedores = []
    for m in mesas_anteriores:
        if m['Status'] == 'Concluído':
            if m['SetsJ1'] > m['SetsJ2']:
                vencedores.append(m['Jogador1'])
            else:
                vencedores.append(m['Jogador2'])
        else:
            # Salvaguarda para não deixar passar mesas em aberto
            return False
            
    # Define a próxima fase do torneio
    proximas_etapas = {
        "32-Avos": ("Dezesseis-Avos", 16),
        "Dezesseis-Avos": ("Oitavas de Final", 8),
        "Oitavas de Final": ("Quartas de Final", 4),
        "Quartas de Final": ("Semifinal", 2),
        "Semifinal": ("Grande Final", 1)
    }
    
    if fase_atual not in proximas_etapas:
        if fase_atual == "Grande Final":
            dados['FasesMataMata']['Status'] = 'Finalizado'
            dados['Status'] = 'Finalizado'
            return True
        return False
        
    proximo_nome, total_mesas = proximas_etapas[fase_atual]
    
    # Monta os novos confrontos pegando os vencedores em sequência (Mesa 1 vs Mesa 2, etc)
    novas_mesas = []
    mesa_id = 1
    
    for i in range(0, len(vencedores), 2):
        j1 = vencedores[i]
        j2 = vencedores[i+1] if (i+1) < len(vencedores) else "FOLGA_WO"
        
        status_inicial = 'Pendente'
        sets_j1, sets_j2, tentos_j1, tentos_j2 = 0, 0, 0, 0
        
        if j2 == "FOLGA_WO":
            status_inicial = 'Concluído'
            sets_j1, tentos_j1 = 2, 72
            
        novas_mesas.append({
            'Mesa': mesa_id,
            'Jogador1': j1, 'Jogador2': j2,
            'SetsJ1': sets_j1, 'SetsJ2': sets_j2,
            'TentosJ1': tentos_j1, 'TentosJ2': tentos_j2,
            'FloresJ1': 0, 'FloresJ2': 0,
            'Status': status_inicial
        })
        mesa_id += 1
        
    dados['FasesMataMata'] = {
        'FaseAtual': proximo_nome,
        'Status': 'Em Andamento',
        'Mesas': novas_mesas
    }
    return True
