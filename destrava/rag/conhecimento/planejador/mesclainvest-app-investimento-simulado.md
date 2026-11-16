# Projeto: MesclaInvest – Aplicativo Mobile de Investimento Simulado em Startups
Tipo: App mobile com API
Descrição: Aplicativo mobile para conhecer startups de um ecossistema universitário de inovação e simular a compra e a venda de participações digitais (tokens), com saldo fictício e regras no backend.
Login na Etapa 1: sim — o escopo exige conta individual e não há acesso anônimo.

## Etapas

### Etapa 1 – Esqueleto: cadastro e login ponta a ponta
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando app, API e banco
- Entregáveis: repositório com branches, projeto do app mobile, backend (API), banco de dados, registro de usuários, rota de cadastro e login, telas de cadastro e login
- Demonstração: criar uma conta no app, sair e entrar de novo
- Dependências: nenhuma

### Etapa 2 – Recuperação de senha
- Objetivo: permitir recuperar o acesso
- Entregáveis: rota de envio de instruções por e-mail, tela de "esqueci minha senha"
- Demonstração: pedir a recuperação e receber as instruções no e-mail cadastrado
- Dependências: Etapa 1

### Etapa 3 – Catálogo: lista de startups
- Objetivo: mostrar as startups cadastradas
- Entregáveis: registro de startups com dados iniciais carregados por script, rota de listagem, tela de lista no app
- Demonstração: entrar e ver a lista de startups com nome, estágio e capital simulado
- Dependências: Etapa 1

### Etapa 4 – Filtro por estágio
- Objetivo: ajudar a entender o nível de maturidade
- Entregáveis: classificação em nova, em operação ou em expansão, parâmetro de filtro na rota, controle de filtro na tela
- Demonstração: filtrar por "em operação" e ver só essas startups
- Dependências: Etapa 3

### Etapa 5 – Detalhe da startup
- Objetivo: conhecer cada startup a fundo
- Entregáveis: rota de detalhe com descrição, estrutura societária e percentuais, capital aportado, tokens emitidos, conselho, vídeos e documentos públicos, tela de detalhe
- Demonstração: abrir uma startup e ver sócios, percentuais, vídeo e documentos
- Dependências: Etapa 3

### Etapa 6 – Perguntas e respostas públicas
- Objetivo: criar interação com os empreendedores
- Entregáveis: registro de perguntas e respostas, rotas de envio e listagem, área de perguntas na tela da startup
- Demonstração: enviar uma pergunta e ver uma resposta pública já cadastrada
- Dependências: Etapa 5

### Etapa 7 – Carteira simulada
- Objetivo: ter saldo fictício para negociar
- Entregáveis: registro de carteiras, crédito simulado em reais, extrato de movimentações, regra no backend contra saldo negativo, tela da carteira
- Demonstração: carregar R$ 1.000 fictícios e ver o saldo e o extrato
- Dependências: Etapa 1

### Etapa 8 – Oferta de venda de tokens
- Objetivo: colocar tokens à venda no balcão
- Entregáveis: registro de participações e de ofertas, rota de criação de oferta de venda com validação da quantidade que o usuário possui, tela de balcão listando ofertas, botão na página da startup
- Demonstração: criar uma oferta de venda e vê-la no balcão e na página da startup
- Dependências: Etapas 5 e 7

### Etapa 9 – Comprar uma oferta existente
- Objetivo: concluir uma negociação simulada
- Entregáveis: rota que executa a compra em uma única operação (débito do saldo, crédito do vendedor, transferência dos tokens, registro da transação), mensagens de saldo insuficiente, tela de confirmação
- Demonstração: comprar tokens de uma oferta e ver saldo, quantidade de tokens e extrato atualizados nos dois usuários
- Dependências: Etapa 8

### Etapa 10 – Oferta de compra e cancelamento
- Objetivo: completar o balcão com o outro lado da negociação
- Entregáveis: criação de oferta de compra com reserva de saldo, casamento com ofertas de venda compatíveis, cancelamento de ofertas abertas, telas correspondentes
- Demonstração: criar uma oferta de compra que casa com uma de venda e cancelar outra oferta aberta
- Dependências: Etapa 9

### Etapa 11 – Perguntas privadas para investidores
- Objetivo: dar acesso exclusivo a quem investe
- Entregáveis: regra no backend que identifica investidores da startup, rota e tela de perguntas privadas visíveis apenas para eles
- Demonstração: ver o campo de perguntas privadas como investidor e não vê-lo como usuário sem tokens da startup
- Dependências: Etapas 6 e 9

### Etapa 12 – Valorização: variação diária
- Objetivo: mostrar como o valor dos tokens muda
- Entregáveis: lógica de cálculo definida pela equipe (por exemplo, preço da última transação), rota de variação diária, painel gráfico simples no app
- Demonstração: fazer duas transações em preços diferentes e ver a variação diária refletida no gráfico
- Dependências: Etapa 9

### Etapa 13 – Valorização: demais períodos
- Objetivo: ampliar a análise de desempenho
- Entregáveis: variação semanal, mensal, de 6 meses e acumulada do ano, seletor de período no painel
- Demonstração: alternar entre os períodos usando histórico de exemplo e ver os valores coerentes entre si
- Dependências: Etapa 12

### Etapa 14 – Autenticação multifator opcional
- Objetivo: oferecer uma camada extra de segurança
- Entregáveis: ativação e desativação do segundo fator pelo usuário, segundo fator no login, tela de configuração
- Demonstração: ativar o segundo fator, sair e entrar passando por ele
- Dependências: Etapa 1

### Etapa 15 – Atualizações e eventos
- Objetivo: manter o investidor informado
- Entregáveis: registro e rota de atualizações e eventos, tela de feed com destaque para as startups em que o usuário investe
- Demonstração: ver o feed e identificar as novidades das startups em que há tokens
- Dependências: Etapa 5

### Etapa 16 – Testes, documentação e entrega final
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das regras de negociação (saldo insuficiente, quantidade acima da disponível, casamento de ofertas), da valorização e do acesso restrito a investidores, código comentado, README com instruções de execução
- Demonstração: executar o roteiro completo, do cadastro à compra e ao painel, seguindo apenas o README
- Dependências: todas as anteriores
