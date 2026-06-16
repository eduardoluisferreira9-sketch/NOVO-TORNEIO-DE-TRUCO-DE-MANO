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
    
    # Computa os resultados das mesas concluídas
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
    Rebatizada para fins de compatibilidade estrutural com o app.py.
    """
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
                m['TentosJ1'], m['TentosJ2'] = 0, 24
            else:
                m['SetsJ1'], m['SetsJ2'] = 2, 0
                m['TentosJ1'], m['TentosJ2'] = 24, 0

    # Retorna o dicionário estruturado para o app.py gerenciar a persistência
    return {
        'Numero': numero_rodada,
        'Status': 'Em Andamento',
        'Mesas': novas_mesas
    }
