# Projeto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade
Tipo: App web CRUD
Descrição: Plataforma web para jogar online, contra outros usuários, jogos de alinhar peças em um tabuleiro com gravidade (como o ligue quatro). Cada jogador tem conta, perfil e estatísticas; o tamanho do tabuleiro e o tempo da partida, no estilo do xadrez, são configuráveis; há chat durante a partida e replay das partidas passadas.
Login na Etapa 1: sim — o escopo exige contas individuais, com perfil e histórico de partidas.

## Etapas

### Etapa 1 – Esqueleto: cadastro e login de ponta a ponta
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend, banco de dados, tabela de usuários (nome de usuário e senha protegida), rotas de cadastro e de login, telas de cadastro e de login, página inicial simples
- Demonstração: criar uma conta, entrar com ela e ver a página inicial com o nome de usuário; tentar cadastrar um nome já usado e ver a recusa
- Dependências: nenhuma

### Etapa 2 – Sessão lembrada, saída da conta e navegação
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: manter o usuário conectado e permitir sair com segurança
- Entregáveis: sessão que continua ao reabrir o site, botão de sair que encerra a sessão, barra de navegação nas páginas existentes
- Demonstração: entrar, fechar e reabrir o site sem digitar as credenciais de novo, depois sair e ver que as páginas internas voltam a pedir login
- Dependências: Etapa 1

### Etapa 3 – Meu perfil: ver e editar nome de usuário e senha
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: consultar e manter os dados da própria conta
- Entregáveis: rota de leitura do perfil, tela de perfil com os dados da conta, rotas e formulários de alteração de nome de usuário e de senha, validação de nome repetido
- Demonstração: abrir o perfil, trocar o nome de usuário e a senha, sair e entrar com os novos dados
- Dependências: Etapa 2

### Etapa 4 – Criar e listar desafios abertos
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: permitir que um jogador convide outros e veja quem está esperando uma partida
- Entregáveis: tabela de desafios, rota de criação com o tabuleiro padrão, lista de desafios abertos na página inicial mostrando quem criou cada um
- Demonstração: criar um desafio com uma conta e ver, com outra conta, o desafio na lista com o nome de quem o criou
- Dependências: Etapa 2

### Etapa 5 – Configurações do desafio: tamanho do tabuleiro e tempo
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: personalizar a partida antes de convidar
- Entregáveis: campos de linhas, colunas e quantidade de peças para vencer, modos de tempo (rápido, médio ou personalizado) com tempo total e acréscimo por jogada, validação dos limites, exibição das configurações na lista de desafios
- Demonstração: criar um desafio com tabuleiro de 6 por 7 e 5 minutos por jogador e ver as configurações na lista; tentar uma dimensão inválida e ver a mensagem de erro
- Dependências: Etapa 4

### Etapa 6 – Perfil de quem criou o desafio
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: conhecer o adversário antes de aceitar
- Entregáveis: rota de perfil público de outro jogador, link no nome do criador na lista de desafios, tela de perfil em modo somente leitura
- Demonstração: clicar no nome do criador de um desafio e ver o perfil dele, sem as opções de edição
- Dependências: Etapas 3 e 4

### Etapa 7 – Aceitar um desafio e abrir a partida
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: começar uma partida entre dois jogadores
- Entregáveis: ação de aceitar desafio, criação da partida com as configurações do desafio, retirada do desafio da lista, comunicação em tempo real entre os dois jogadores, página da partida com o tabuleiro vazio e a indicação de quem joga primeiro
- Demonstração: aceitar o desafio com a segunda conta e ver, nas duas telas, o tabuleiro vazio e de quem é a vez
- Dependências: Etapas 4 e 5

### Etapa 8 – Jogadas com gravidade e alternância de turnos
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: jogar de verdade, com as regras aplicadas pelo servidor
- Entregáveis: clique no tabuleiro para soltar a peça em uma coluna, peça que cai até a primeira posição livre, validação das jogadas no servidor (vez do jogador, coluna cheia), atualização em tempo real nas duas telas, indicação da vez
- Demonstração: jogar alternadamente com as duas contas e ver a peça cair; tentar jogar fora da vez e em uma coluna cheia e ver o bloqueio
- Dependências: Etapa 7

### Etapa 9 – Fim da partida por vitória e saída
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: encerrar a partida e deixar o resultado claro
- Entregáveis: detecção da sequência vencedora, mensagem com quem venceu e como a partida terminou, registro da partida concluída (jogadores, resultado, configurações e sequência de jogadas), botão para sair da partida e voltar ao início
- Demonstração: completar uma sequência de quatro peças e ver, nas duas telas, o vencedor e o motivo do fim; sair e ver a página inicial
- Dependências: Etapa 8

### Etapa 10 – Relógio da partida e derrota por tempo
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: aplicar o controle de tempo configurado no desafio
- Entregáveis: contagem regressiva de cada jogador visível nas duas telas, acréscimo por jogada, fim da partida por tempo esgotado registrado como tipo de término
- Demonstração: criar uma partida com 1 minuto por jogador, deixar o tempo de um deles acabar e ver a derrota por tempo nas duas telas
- Dependências: Etapas 5 e 9

### Etapa 11 – Desistência e empate
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: encerrar partidas sem esperar o fim
- Entregáveis: botão de desistir, oferta de empate com as ações de aceitar, recusar e retirar a oferta, tipos de término (desistência e empate) registrados na partida
- Demonstração: oferecer empate e retirar a oferta, oferecer de novo e ver a recusa, oferecer uma terceira vez e ver o empate aceito; em outra partida, desistir e ver a vitória do adversário
- Dependências: Etapa 9

### Etapa 12 – Chat durante a partida
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: conversar com o adversário durante o jogo
- Entregáveis: caixa de mensagens na página da partida, envio e recebimento em tempo real, mensagens visíveis só para os dois jogadores da partida
- Demonstração: enviar uma mensagem com uma conta e vê-la aparecer na tela da outra; abrir a partida com uma terceira conta e confirmar que a conversa não aparece
- Dependências: Etapa 7

### Etapa 13 – Histórico e estatísticas no perfil
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: acompanhar o desempenho ao longo do tempo
- Entregáveis: rota de partidas do jogador, lista de partidas no perfil com adversário, vencedor, configurações (tamanho do tabuleiro e tempo) e quem criou o desafio, estatísticas agregadas (partidas, vitórias, derrotas e empates)
- Demonstração: jogar três partidas com resultados diferentes (vitória, derrota e empate) e ver no perfil a lista completa e os totais corretos
- Dependências: Etapas 3, 9 e 11

### Etapa 14 – Replay passo a passo
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: rever uma partida jogada por jogada
- Entregáveis: página de replay, rota que devolve a sequência de jogadas, botões de avançar e de voltar uma jogada, contador com o total de jogadas, resultado da partida (vencedor e como terminou) exibido no replay, link para abrir o replay a partir da lista do perfil
- Demonstração: abrir o replay de uma partida do histórico, ver o total de jogadas, avançar até o fim e ver o resultado, voltar duas jogadas e ver o tabuleiro correspondente
- Dependências: Etapa 13

### Etapa 15 – Replay logo após a partida e de outros jogadores
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: facilitar a análise da própria partida e o estudo das partidas de outros jogadores
- Entregáveis: botão para abrir o replay ao fim da partida, botão para voltar ao perfil a partir do replay, acesso ao replay das partidas listadas no perfil de outro jogador
- Demonstração: terminar uma partida e abrir o replay pelo botão, voltar ao perfil, abrir o perfil do adversário e assistir ao replay de uma partida dele
- Dependências: Etapas 6, 9 e 14

### Etapa 16 – Testes, documentação e entrega final
Contexto: 4-by-4 – Plataforma Web de Jogos de Tabuleiro com Gravidade | Tipo: App web CRUD
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das regras do jogo (gravidade, vitória, empate, tempo), das permissões (só os jogadores da partida jogam e conversam) e da gravação do histórico, código comentado, README com instruções de execução, versão final publicada
- Demonstração: executar o roteiro completo de uso em um ambiente limpo, do cadastro à partida e ao replay, seguindo apenas o README
- Dependências: todas as anteriores
