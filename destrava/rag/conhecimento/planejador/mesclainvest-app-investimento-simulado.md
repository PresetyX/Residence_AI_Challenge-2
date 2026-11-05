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

### Etapa 1 – Organização do projeto e do ambiente
- Objetivo: deixar o ambiente pronto antes de programar
- Entregáveis: repositório com estratégia de branches, backend Node.js, projeto Flutter, projeto Firebase com Firestore, README inicial
- Dependências: nenhuma

### Etapa 2 – Modelagem dos dados no Firestore
- Objetivo: definir coleções e documentos de forma adequada a um banco não relacional
- Entregáveis: coleções de usuários, startups (com estágio, sócios, conselho, documentos e vídeos), carteiras, participações em tokens, ofertas, transações, perguntas e respostas, atualizações e eventos, e o histórico de preços usado na valorização
- Dependências: Etapa 1

### Etapa 3 – Backend base e dados iniciais das startups
- Objetivo: ter uma API funcionando e dados para o app consumir
- Entregáveis: servidor com rotas, controladores e acesso ao Firestore, script que carrega startups de exemplo, usuários de teste e histórico de transações
- Dependências: Etapa 2

### Etapa 4 – Autenticação e recuperação de senha
- Objetivo: restringir o uso a usuários cadastrados
- Entregáveis: cadastro com os campos exigidos e validação de CPF, login, proteção das rotas da API, recuperação de senha por e-mail
- Dependências: Etapa 3

### Etapa 5 – Autenticação multifator opcional
- Objetivo: oferecer uma camada extra de segurança
- Entregáveis: ativação e desativação do MFA pelo usuário, segundo fator no login, tratamento de falhas
- Dependências: Etapa 4

### Etapa 6 – API do catálogo de startups
- Objetivo: entregar ao app os dados das startups
- Entregáveis: rotas de listagem com filtro por estágio e de detalhe, com sócios, capital simulado, tokens emitidos e documentos
- Dependências: Etapa 3

### Etapa 7 – Base do aplicativo Flutter
- Objetivo: ter a estrutura do app e o acesso à API
- Entregáveis: navegação entre telas, tema, camada de acesso à API, telas de cadastro, login e recuperação de senha, tela de configuração do MFA
- Dependências: Etapas 4 e 5

### Etapa 8 – Telas do catálogo e do detalhe da startup
- Objetivo: permitir conhecer cada startup
- Entregáveis: lista com filtro por estágio, página de detalhe com sumário executivo, estrutura societária, vídeos, sócios e documentos públicos
- Dependências: Etapas 6 e 7

### Etapa 9 – Perguntas e respostas
- Objetivo: criar a interação entre investidores e empreendedores
- Entregáveis: envio de perguntas, exibição das respostas públicas, perguntas privadas liberadas só para investidores da startup
- Dependências: Etapa 8

### Etapa 10 – Carteira simulada
- Objetivo: ter saldo fictício para negociar
- Entregáveis: saldo em reais fictício, mecanismo de crédito simulado, extrato de movimentações, regras no backend que impedem saldo negativo
- Dependências: Etapa 4

### Etapa 11 – Balcão de tokens
- Objetivo: simular compra e venda de tokens entre usuários
- Entregáveis: criação de ofertas de compra e de venda, cancelamento de oferta, casamento entre ofertas, atualização de saldo e de quantidade de tokens em uma única operação, registro das transações, acesso pela página da startup e por uma tela de balcão
- Dependências: Etapas 8 e 10

### Etapa 12 – Cálculo da valorização
- Objetivo: medir como o valor dos tokens varia
- Entregáveis: lógica de cálculo definida pela equipe (por exemplo, preço da última transação ou média), variação por período (diário, semanal, mensal, 6 meses e YTD), rotas da API que entregam esses valores
- Dependências: Etapa 11

### Etapa 13 – Dashboard de valorização no app
- Objetivo: mostrar a evolução dos investimentos
- Entregáveis: gráficos por período, resumo da carteira do investidor, valor atual e variação de cada token
- Dependências: Etapa 12

### Etapa 14 – Atualizações e eventos
- Objetivo: manter o investidor informado
- Entregáveis: rota e tela com atualizações e eventos das startups, destaque para as startups em que o usuário investe
- Dependências: Etapa 8

### Etapa 15 – Testes, documentação e entrega final
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das regras de negociação (saldo insuficiente, oferta duplicada, casamento de ofertas), da valorização e do acesso restrito a investidores, código comentado, README com instruções de execução, versão final publicada
- Dependências: todas as anteriores
