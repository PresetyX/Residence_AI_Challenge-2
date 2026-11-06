# Projeto: MesclaInvest – Aplicativo Mobile de Investimento Simulado em Startups

## Descrição
Aplicativo mobile, com estilo de rede social corporativa e de relações com investidores, para conhecer startups de um ecossistema universitário de inovação e simular a compra e a venda de tokens que representam participações digitais nelas. Toda a negociação é simulada, com saldo fictício e regras no backend. Não há dinheiro real, blockchain nem contratos inteligentes.

## Tipo / domínio
Aplicativo mobile com backend em API, banco de dados não relacional, autenticação com MFA opcional, simulação de negociação (balcão de ofertas) e dashboard de valorização.

## Tecnologias exigidas
- Backend: Node.js (LTS) com TypeScript e/ou JavaScript, que simula os dados, aplica as regras de negócio e expõe as APIs
- App mobile: Flutter com Dart
- Banco de dados: Firebase Firestore
- Versionamento: Git e GitHub

## Requisitos principais

### Autenticação e segurança
- Não há acesso anônimo: tudo exige conta individual
- Cadastro com nome completo, e-mail válido, CPF, telefone celular e senha
- Recuperação de senha por e-mail ("Esqueci minha senha")
- Autenticação multifator (MFA/2FA) opcional, funcionando no protótipo
- Verificação formal de identidade (KYC) fica fora do escopo

### Catálogo de startups
- Navegação pelas startups cadastradas
- Descrição, estrutura societária, participação percentual dos sócios, capital aportado (simulado), quantidade total de tokens emitidos e membros do conselho, mentores ou participantes externos
- Classificação por estágio: nova, em operação ou em expansão, com filtro por estágio
- Página de detalhe com sumário executivo, estrutura societária, perguntas e respostas públicas, vídeos demonstrativos e apresentação dos sócios
- Documentos públicos (sumário executivo e plano de negócios)
- Não há cadastro de startups pelo app: os dados já existem no banco e chegam ao app por uma rota da API

### Perguntas e atualizações
- Envio de perguntas aos empreendedores, com respostas públicas
- Perguntas privadas ou exclusivas para quem já é investidor da startup (regras definidas pela equipe)
- Acompanhamento de atualizações e eventos das startups

### Carteira e balcão de tokens
- Carteira digital com saldo fictício em reais, carregado por um mecanismo interno de crédito simulado
- Ofertas de compra e de venda de tokens, feitas na página da startup ou em uma tela de balcão de negociação
- Negociação restrita a usuários cadastrados
- Quem já é investidor de uma startup tem acesso a compra e venda e a perguntas exclusivas daquela startup
- Todas as regras ficam no backend, e os registros ficam no Firestore

### Valorização dos tokens
- Painel gráfico (dashboard) com a variação do valor dos tokens do investidor
- Períodos: diário, semanal, mensal, últimos 6 meses e acumulado do ano (YTD)
- Valores calculados a partir das transações registradas no sistema simulado
- A lógica de cálculo de variação, tendência ou oscilação é definida pela equipe (item de peso diferenciado)

### Fora do escopo
- Pagamentos reais (cartões, adquirentes, instituições financeiras)
- Emissão de tokens em blockchain, padrões como ERC-20 e contratos inteligentes (Solidity)
- Versão web completa
- Implantação em produção ou captação real de recursos

## Etapas
As etapas abaixo são fatias verticais: cada uma atravessa as camadas necessárias (interface, regras e dados) e termina com algo que pode ser demonstrado e testado. A Etapa 1 é o esqueleto mínimo, a funcionalidade mais fina possível funcionando de ponta a ponta.

### Etapa 1 – Esqueleto: cadastro e login ponta a ponta
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando app, API e banco
- Entregáveis: repositório com branches, projeto Flutter, backend Node.js, projeto Firebase com Firestore, coleção de usuários, rota de cadastro e login, telas de cadastro e login
- Demonstração: criar uma conta no app, sair e entrar de novo
- Dependências: nenhuma

### Etapa 2 – Recuperação de senha
- Objetivo: permitir recuperar o acesso
- Entregáveis: rota de envio de instruções por e-mail, tela de "esqueci minha senha"
- Demonstração: pedir a recuperação e receber as instruções no e-mail cadastrado
- Dependências: Etapa 1

### Etapa 3 – Catálogo: lista de startups
- Objetivo: mostrar as startups cadastradas
- Entregáveis: coleção de startups com dados iniciais carregados por script, rota de listagem, tela de lista no app
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
- Entregáveis: coleção de perguntas e respostas, rotas de envio e listagem, área de perguntas na tela da startup
- Demonstração: enviar uma pergunta e ver uma resposta pública já cadastrada
- Dependências: Etapa 5

### Etapa 7 – Carteira simulada
- Objetivo: ter saldo fictício para negociar
- Entregáveis: coleção de carteiras, crédito simulado em reais, extrato de movimentações, regra no backend contra saldo negativo, tela da carteira
- Demonstração: carregar R$ 1.000 fictícios e ver o saldo e o extrato
- Dependências: Etapa 1

### Etapa 8 – Oferta de venda de tokens
- Objetivo: colocar tokens à venda no balcão
- Entregáveis: coleção de participações e de ofertas, rota de criação de oferta de venda com validação da quantidade que o usuário possui, tela de balcão listando ofertas, botão na página da startup
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
- Entregáveis: variação semanal, mensal, de 6 meses e acumulada do ano (YTD), seletor de período no painel
- Demonstração: alternar entre os períodos usando histórico de exemplo e ver os valores coerentes entre si
- Dependências: Etapa 12

### Etapa 14 – Autenticação multifator opcional
- Objetivo: oferecer uma camada extra de segurança
- Entregáveis: ativação e desativação do MFA pelo usuário, segundo fator no login, tela de configuração
- Demonstração: ativar o MFA, sair e entrar passando pelo segundo fator
- Dependências: Etapa 1

### Etapa 15 – Atualizações e eventos
- Objetivo: manter o investidor informado
- Entregáveis: coleção e rota de atualizações e eventos, tela de feed com destaque para as startups em que o usuário investe
- Demonstração: ver o feed e identificar as novidades das startups em que há tokens
- Dependências: Etapa 5

### Etapa 16 – Testes, documentação e entrega final
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das regras de negociação (saldo insuficiente, quantidade acima da disponível, casamento de ofertas), da valorização e do acesso restrito a investidores, código comentado, README com instruções de execução
- Demonstração: executar o roteiro completo, do cadastro à compra e ao painel, seguindo apenas o README
- Dependências: todas as anteriores
