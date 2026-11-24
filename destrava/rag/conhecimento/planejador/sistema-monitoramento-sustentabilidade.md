# Projeto: Sistema de Monitoramento de Sustentabilidade Pessoal
Tipo: App de terminal com banco
Descrição: Sistema de linha de comando que registra o dia a dia de uma pessoa (água, energia, resíduos, reciclagem e transporte) e classifica a sustentabilidade de cada dia e das médias de vários dias. Os dados ficam em um banco de dados e são manipulados por um menu.
Login na Etapa 1: não — é uma aplicação de terminal de uso pessoal; a Etapa 1 é a funcionalidade mínima de entrada, regra e saída.

## Etapas

### Etapa 1 – Esqueleto: um dia com a classificação da água
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: ter o ambiente e o caminho completo de entrada, regra e saída com o indicador mais simples
- Entregáveis: ambiente de desenvolvimento, repositório com branches, leitura da data e dos litros de água com validação, classificação (alta, moderada ou baixa) e exibição
- Demonstração: informar 180 litros e ver "moderada sustentabilidade"
- Dependências: nenhuma

### Etapa 2 – Energia e resíduos
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: classificar mais dois indicadores
- Entregáveis: leitura e validação de kWh e de percentual reciclado (0 a 100), regras de classificação de cada um, exibição junto com a água
- Demonstração: informar 6,5 kWh e 60% reciclado e ver as duas classificações, testando também os valores nos limites das faixas
- Dependências: Etapa 1

### Etapa 3 – Transporte com ponderação
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: classificar o meio de transporte
- Entregáveis: menu de meios de transporte (incluindo os que a equipe acrescentar), pesos de cada meio, regra de classificação
- Demonstração: escolher caminhada e ver alta sustentabilidade, escolher carro a combustível e ver baixa
- Dependências: Etapa 2

### Etapa 4 – Sustentabilidade geral do dia
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: resumir o dia em uma classificação única
- Entregáveis: regra de ponderação da classificação geral definida pela equipe, exibição do resultado completo no formato do exemplo
- Demonstração: repetir o exemplo do enunciado (24/3/2025) e obter a classificação geral esperada
- Dependências: Etapa 3

### Etapa 5 – Guardar um dia no banco (inserir)
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: tornar o cadastro permanente
- Entregáveis: tabela de monitoramento criada manualmente, conexão com o banco, menu principal com a opção Inserir, gravação do registro e exibição da classificação do dia
- Demonstração: cadastrar um dia pelo menu e conferir o registro na tabela
- Dependências: Etapa 4

### Etapa 6 – Listar monitoramentos com classificação
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: consultar o que foi cadastrado
- Entregáveis: leitura dos registros no banco, opção de listagem no menu, classificação de cada dia exibida
- Demonstração: cadastrar três dias e ver a lista com as classificações de cada um
- Dependências: Etapa 5

### Etapa 7 – Médias e classificação geral
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: resumir vários dias
- Entregáveis: cálculo das médias de água, energia, resíduos, percentual reciclado e transporte, classificação pelas médias, opção de menu
- Demonstração: usar dados de exemplo com média conhecida e ver o resultado bater com o cálculo manual
- Dependências: Etapa 6

### Etapa 8 – Alterar monitoramento
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: corrigir um dia já cadastrado
- Entregáveis: escolha do registro, nova entrada com validação, atualização no banco e nova classificação
- Demonstração: alterar o consumo de água de um dia e ver a classificação mudar
- Dependências: Etapa 6

### Etapa 9 – Apagar monitoramento
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: remover um registro escolhido
- Entregáveis: escolha do registro, confirmação, remoção no banco e retorno ao menu
- Demonstração: apagar um dia e ver que ele sumiu da lista e das médias
- Dependências: Etapa 6

### Etapa 10 – Criptografia dos dados
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: proteger os dados armazenados
- Entregáveis: algoritmo de criptografia com chave válida, cifra na gravação e decifra na leitura, em todas as opções do menu
- Demonstração: cadastrar um dia, ver os valores cifrados no banco e as telas continuarem mostrando os valores corretos
- Dependências: Etapas 5 a 9

### Etapa 11 – Testes, documentação e entrega final
Contexto: Sistema de Monitoramento de Sustentabilidade Pessoal | Tipo: App de terminal com banco
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das faixas (incluindo os limites), das médias e do CRUD, código comentado, README com instruções de execução
- Demonstração: executar o roteiro completo do menu em um ambiente limpo, seguindo apenas o README
- Dependências: todas as anteriores
