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
As etapas abaixo são fatias verticais: cada uma atravessa as camadas necessárias (interface, regras e dados) e termina com algo que pode ser demonstrado e testado. A Etapa 1 é o esqueleto mínimo, a funcionalidade mais fina possível funcionando de ponta a ponta.

### Etapa 1 – Esqueleto: cadastrar e listar candidatos
- Objetivo: ter ambiente, banco e menu funcionando com a primeira funcionalidade completa
- Entregáveis: ambiente Python 3, conexão com MySQL via mysql.connector, tabela de candidatos com número único, menu inicial, opções de cadastrar e listar candidatos
- Demonstração: cadastrar dois candidatos, tentar repetir um número e ver o bloqueio, listar os dois
- Dependências: nenhuma

### Etapa 2 – Cadastrar eleitor com validação
- Objetivo: registrar quem pode votar
- Entregáveis: tabela de eleitores (nome, título, CPF, mesário), validação matemática de CPF e título, bloqueio de duplicidade, geração e exibição da chave de acesso, listagem de eleitores
- Demonstração: cadastrar um eleitor, receber a chave de acesso e ver tentativas com CPF inválido ou repetido serem recusadas
- Dependências: Etapa 1

### Etapa 3 – Buscar, editar e remover
- Objetivo: manter eleitores e candidatos atualizados
- Entregáveis: busca de eleitor por CPF ou título e de candidato por número, edição e remoção dos dois, mantendo as regras de validação e unicidade
- Demonstração: editar um candidato sem repetir número, buscar um eleitor por CPF e remover um registro
- Dependências: Etapas 1 e 2

### Etapa 4 – Criptografia com Cifra de Hill
- Objetivo: proteger CPF e chave de acesso no banco
- Entregáveis: funções de cifrar e decifrar com matriz-chave válida, aplicação ao CPF e à chave de acesso na gravação e na conferência, ajuste das telas de cadastro e busca
- Demonstração: cadastrar um eleitor e ver no banco os valores cifrados, com a busca e a conferência ainda funcionando
- Dependências: Etapa 3

### Etapa 5 – Abrir a votação (mesário e zerézima)
- Objetivo: liberar a urna só para o mesário e começar do zero
- Entregáveis: autenticação do mesário (título, 4 primeiros dígitos do CPF e chave), mensagem de erro clara, zerézima com limpeza de votos e listagem dos candidatos com zero votos, menu da urna (votar ou encerrar), arquivo de log com o evento de abertura e de acesso negado
- Demonstração: tentar abrir com um eleitor comum (recusado e registrado no log) e abrir com um mesário vendo a zerézima
- Dependências: Etapa 4

### Etapa 6 – Registrar um voto
- Objetivo: fazer o caminho principal da votação funcionar
- Entregáveis: identificação do eleitor, pedido do número do candidato, exibição de nome, número e partido, confirmação, tabela de votos com data, hora e protocolo cifrado, status "Já Votou", exibição do protocolo, log de sucesso
- Demonstração: votar em um candidato, ver o protocolo e conferir o voto e o status no banco
- Dependências: Etapa 5

### Etapa 7 – Regras do voto: duplo, nulo e correção
- Objetivo: tratar os casos especiais do voto
- Entregáveis: bloqueio de eleitor que já votou com log de tentativa de voto duplo, voto nulo ao confirmar número inexistente, retorno ao campo do número quando o eleitor não confirma
- Demonstração: tentar votar duas vezes e ver o bloqueio, votar em número inexistente e ver o voto nulo
- Dependências: Etapa 6

### Etapa 8 – Encerrar a votação
- Objetivo: fechar a urna apenas com autorização do mesário
- Entregáveis: validação do mesário, pergunta de confirmação, dupla confirmação com nova digitação da chave, log de encerramento, retorno ao menu principal
- Demonstração: responder "Não" e voltar ao menu, depois responder "Sim", confirmar a chave e encerrar
- Dependências: Etapa 5

### Etapa 9 – Auditoria: logs e protocolos
- Objetivo: permitir conferir o que aconteceu na votação
- Entregáveis: opções de menu para exibir o arquivo de logs e listar os protocolos de votação
- Demonstração: abrir a auditoria e ver os eventos de abertura, voto, alertas e encerramento na ordem certa
- Dependências: Etapas 6, 7 e 8

### Etapa 10 – Resultado: boletim de urna e vencedor
- Objetivo: apresentar o resultado da eleição
- Entregáveis: menu pós-encerramento, boletim com votos por candidato em ordem alfabética, declaração do vencedor com nome, número, partido e total de votos
- Demonstração: encerrar uma votação de teste e ver o boletim e o vencedor corretos
- Dependências: Etapa 8

### Etapa 11 – Estatísticas e integridade
- Objetivo: conferir a confiabilidade dos números
- Entregáveis: estatística de comparecimento (quantidade e percentual), votos por partido, validação de integridade comparando votos registrados com eleitores "Já Votou"
- Demonstração: gerar os três relatórios e ver os totais coerentes entre si
- Dependências: Etapa 10

### Etapa 12 – Testes, documentação e entrega final
- Objetivo: integrar o menu principal e validar o sistema
- Entregáveis: menu principal ligando gerenciamento, votação, auditoria e resultados, testes dos fluxos críticos (voto duplo, mesário inválido, voto nulo, integridade), código comentado, README com instruções de execução
- Demonstração: executar uma eleição completa do cadastro ao resultado, seguindo apenas o README
- Dependências: todas as anteriores
