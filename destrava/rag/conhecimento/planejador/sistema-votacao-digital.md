# Projeto: Sistema de Votação Digital (urna eletrônica em terminal)

## Descrição
Sistema de votação digital executado no terminal, com ênfase em segurança, organização e confiabilidade dos dados. Permite cadastrar eleitores e candidatos, abrir a urna com um mesário, registrar votos, auditar a votação por logs e protocolos, e consultar os resultados.

## Tipo / domínio
Aplicação de linha de comando com banco de dados relacional, validação de dados, criptografia e registro de eventos (logs).

## Tecnologias exigidas
- Linguagem: Python 3.x
- Banco de dados: MySQL, acessado pela biblioteca mysql.connector
- Data e hora: biblioteca datetime (bibliotecas time e os, se necessário)
- Criptografia: Cifra de Hill, aplicada ao CPF, à chave de acesso do eleitor e ao protocolo de votação

## Requisitos principais

### Módulo de Gerenciamento (eleitores e candidatos)
- Cadastro de eleitor com nome completo, título de eleitor, CPF e indicação se atuará como mesário
- Validação matemática de CPF e título, sem duplicidade de nenhum dos dois
- Geração de chave de acesso exclusiva, informada logo após a confirmação do cadastro
- Edição, remoção, busca (por CPF ou título) e listagem de eleitores
- Cadastro de candidato com nome, número de votação e partido, sem repetir número
- Edição, remoção, busca (por número) e listagem de candidatos

### Módulo de Votação
- Abertura da votação: o mesário se identifica com título, 4 primeiros dígitos do CPF e chave de acesso; eleitor comum não abre o sistema; erros de validação mostram mensagem clara
- Zerézima obrigatória após validar o mesário: apaga votos anteriores e lista os candidatos com zero votos
- Menu da urna com as opções Votar e Encerrar
- Voto: identificação do eleitor, bloqueio de quem já votou, pedido do número do candidato, exibição de nome, número e partido para conferência, confirmação (número inexistente confirmado vira voto nulo)
- Registro do voto com data, hora, candidato e protocolo; status do eleitor muda para "Já Votou"; protocolo exibido ao final
- Encerramento: validação do mesário, pergunta de confirmação e dupla confirmação com nova digitação da chave de acesso

### Módulo de Auditoria
- Log de ocorrências em arquivo .txt, com cada linha iniciada por [YYYY-MM-DD HH:MM:SS]
- Eventos registrados: abertura, acesso negado, tentativa de voto duplo, voto realizado e encerramento
- Leitura e exibição do arquivo de logs
- Listagem dos protocolos de votação para conferência

### Módulo de Resultados
- Menu principal com Abrir Sistema de Votação, Auditoria e Resultados
- Boletim de Urna (votos por candidato em ordem alfabética, com o vencedor ao final)
- Estatística de Comparecimento (quantidade e percentual de eleitores aptos que votaram)
- Votos por Partido
- Validação de Integridade (total de votos registrados comparado ao total de eleitores com status "Já Votou")

## Etapas

### Etapa 1 – Organização do projeto e do ambiente
- Objetivo: deixar o ambiente pronto antes de programar
- Entregáveis: repositório com estratégia de branches, ambiente Python 3 configurado, MySQL instalado, biblioteca mysql.connector funcionando, estrutura de pastas do projeto, README inicial
- Dependências: nenhuma

### Etapa 2 – Modelagem do banco de dados
- Objetivo: definir como os dados serão armazenados
- Entregáveis: tabelas de eleitor (com perfil de mesário e status de voto), candidato e voto (com data, hora e protocolo), scripts de criação das tabelas, regras de unicidade (CPF, título, número do candidato)
- Dependências: Etapa 1

### Etapa 3 – Conexão com o banco e acesso aos dados
- Objetivo: ter uma camada única de acesso ao MySQL
- Entregáveis: módulo de conexão com mysql.connector, funções de inserção, consulta, atualização e remoção reaproveitadas pelos demais módulos
- Dependências: Etapa 2

### Etapa 4 – Validações (CPF e título)
- Objetivo: aceitar apenas documentos matematicamente válidos
- Entregáveis: funções de validação de CPF e de título de eleitor, tratamento de entradas inválidas
- Dependências: Etapa 1

### Etapa 5 – Criptografia com Cifra de Hill
- Objetivo: proteger os dados sensíveis
- Entregáveis: funções de cifrar e decifrar com a Cifra de Hill (escolha e validação da matriz-chave), aplicação ao CPF, à chave de acesso e ao protocolo de votação
- Dependências: Etapa 1

### Etapa 6 – Cadastro e gestão de eleitores
- Objetivo: manter a lista de quem pode votar
- Entregáveis: cadastro com validações e sem duplicidade, geração e exibição da chave de acesso, edição, remoção, busca por CPF ou título e listagem
- Dependências: Etapas 3, 4 e 5

### Etapa 7 – Cadastro e gestão de candidatos
- Objetivo: manter a lista de quem pode ser votado
- Entregáveis: cadastro com número único, edição, remoção, busca por número e listagem
- Dependências: Etapa 3

### Etapa 8 – Registro de logs
- Objetivo: ter um registro confiável de eventos críticos
- Entregáveis: função de log em arquivo .txt com marcação de data e hora, mensagens padronizadas para abertura, acesso negado, voto duplo, voto realizado e encerramento
- Dependências: Etapa 1

### Etapa 9 – Abertura da votação e zerézima
- Objetivo: liberar a urna apenas ao mesário e começar do zero
- Entregáveis: autenticação do mesário, mensagens de erro, limpeza dos votos anteriores, listagem dos candidatos com zero votos, menu da urna, log de abertura
- Dependências: Etapas 5, 6, 7 e 8

### Etapa 10 – Processo de votação
- Objetivo: registrar o voto de cada eleitor com segurança
- Entregáveis: identificação do eleitor, bloqueio de voto duplo, conferência e confirmação do candidato, voto nulo, geração e cifragem do protocolo, atualização do status "Já Votou", logs de sucesso e de alerta
- Dependências: Etapa 9

### Etapa 11 – Encerramento da votação
- Objetivo: fechar a urna apenas com autorização do mesário
- Entregáveis: validação do mesário, pergunta de confirmação, dupla confirmação com a chave de acesso, log de encerramento, retorno ao menu principal
- Dependências: Etapa 10

### Etapa 12 – Auditoria
- Objetivo: permitir a conferência do que aconteceu na votação
- Entregáveis: exibição do arquivo de logs, listagem dos protocolos de votação
- Dependências: Etapas 8 e 10

### Etapa 13 – Resultados e relatórios
- Objetivo: consolidar e apresentar o resultado
- Entregáveis: Boletim de Urna com o vencedor, Estatística de Comparecimento, Votos por Partido, Validação de Integridade
- Dependências: Etapa 11

### Etapa 14 – Menu principal, testes e documentação
- Objetivo: integrar os módulos e validar o sistema
- Entregáveis: menu principal ligando gerenciamento, votação, auditoria e resultados, testes dos fluxos principais (voto duplo, mesário inválido, voto nulo, integridade dos totais), código comentado, README com instruções de execução
- Dependências: todas as anteriores
