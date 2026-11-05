# Projeto: Sistema de Monitoramento de Sustentabilidade Pessoal

## Descrição
Sistema em Python que registra o dia a dia de uma pessoa (consumo de água, consumo de energia elétrica, resíduos não recicláveis, reciclagem e meio de transporte) e classifica a sustentabilidade de cada dia e das médias de vários dias. Os dados ficam em um banco de dados, e o usuário os manipula por um menu.

## Tipo / domínio
Aplicação de linha de comando com banco de dados relacional, regras de classificação, cálculo de médias, operações de CRUD e criptografia de dados.

## Tecnologias exigidas
- Linguagem: Python
- Banco de dados: relacional, com conexão feita pelo sistema
- Criptografia: método de álgebra linear aplicado aos dados
- Versionamento: Git e GitHub

## Requisitos principais

### Dados de um monitoramento diário
- Data
- Litros de água consumidos no dia (aproximado)
- kWh de energia elétrica consumidos no dia
- kg de resíduos não recicláveis gerados no dia
- Porcentagem de resíduos reciclados em relação ao total
- Meio de transporte usado: transporte público, bicicleta, caminhada, carro a combustível fóssil, carro elétrico, carona compartilhada (podem ser acrescentados outros)

### Regras de classificação
| Indicador | Alta | Moderada | Baixa |
|---|---|---|---|
| Consumo de água | menos de 150 litros/dia | 150 a 200 litros/dia | mais de 200 litros/dia |
| Consumo de energia elétrica | menos de 5 kWh/dia | 5 a 10 kWh/dia | mais de 10 kWh/dia |
| Resíduos (pelo percentual reciclado) | mais de 50% reciclado | 20% a 50% reciclado | menos de 20% reciclado |
| Transporte | bicicleta, transporte público ou elétrico | uso misto de público e privado | uso exclusivo de combustíveis fósseis |

- A classificação por indicador deve ser mostrada junto com a **sustentabilidade geral** do dia
- O sistema de ponderação do transporte (cada meio recebe um peso) e o da classificação geral são definidos pela equipe

### Exemplo de saída esperada
Entrada: data 24/3/2025, 180 litros de água, 6,5 kWh, 1,5 kg de resíduos não recicláveis, 60% reciclado, transporte por caminhada.
Saída: água moderada, energia moderada, resíduos alta, transporte alta, sustentabilidade geral moderada.

### Banco de dados e médias
- Tabela criada manualmente, com os campos do monitoramento e outros que a equipe julgar úteis
- O sistema conecta ao banco, lê todos os registros e calcula as médias de água, energia, resíduos não recicláveis, percentual reciclado e uso de transporte
- A classificação geral é feita a partir das médias

### Menu do sistema
- Inserir dados de monitoramento
- Alterar dados de monitoramento
- Apagar dados de monitoramento
- Listar cada monitoramento diário com sua classificação
- Calcular e mostrar as médias dos parâmetros com a classificação
- Sair do sistema

### Criptografia
- Os dados devem ser criptografados com um método de álgebra linear

## Etapas

### Etapa 1 – Organização do projeto e do ambiente
- Objetivo: deixar o ambiente pronto antes de programar
- Entregáveis: repositório no Git com estratégia de branches, ambiente Python configurado, estrutura de pastas do projeto, README inicial
- Dependências: nenhuma

### Etapa 2 – Definição das regras de classificação
- Objetivo: transformar as tabelas de classificação e o sistema de ponderação em regras claras
- Entregáveis: faixas de cada indicador, pesos dos meios de transporte, critério da sustentabilidade geral, tratamento dos valores nos limites das faixas
- Dependências: nenhuma

### Etapa 3 – Entrada e validação dos dados de um dia
- Objetivo: ler os dados de um monitoramento com segurança
- Entregáveis: perguntas ao usuário, menu de transportes, validação (números positivos, percentual entre 0 e 100, data válida, opção de transporte existente)
- Dependências: Etapa 1

### Etapa 4 – Classificação de um dia
- Objetivo: classificar cada indicador e o resultado geral
- Entregáveis: funções de classificação por indicador, cálculo da sustentabilidade geral, exibição do resultado
- Dependências: Etapas 2 e 3

### Etapa 5 – Modelagem do banco de dados
- Objetivo: definir como os monitoramentos serão armazenados
- Entregáveis: tabela de monitoramento com os campos exigidos e campos extras, script de criação, registros de exemplo inseridos manualmente
- Dependências: Etapa 1

### Etapa 6 – Conexão com o banco e acesso aos dados
- Objetivo: ter uma camada única de acesso ao banco
- Entregáveis: módulo de conexão, funções de inserção, consulta, atualização e remoção
- Dependências: Etapa 5

### Etapa 7 – Cálculo de médias e classificação geral
- Objetivo: resumir vários dias em uma única classificação
- Entregáveis: leitura dos registros do banco, médias de água, energia, resíduos, percentual reciclado e transporte, classificação pelas médias
- Dependências: Etapas 4 e 6

### Etapa 8 – Menu principal
- Objetivo: integrar as funcionalidades em um menu de opções
- Entregáveis: menu com as seis opções, repetição até o usuário sair, tratamento de opção inválida
- Dependências: Etapa 6

### Etapa 9 – Inserir monitoramento
- Objetivo: cadastrar novos dias pelo sistema
- Entregáveis: tela de inserção reaproveitando a entrada e a validação, gravação no banco, exibição da classificação do dia
- Dependências: Etapas 4, 6 e 8

### Etapa 10 – Alterar e apagar monitoramento
- Objetivo: corrigir e remover registros já cadastrados
- Entregáveis: escolha do registro, alteração com nova validação, remoção com confirmação
- Dependências: Etapa 9

### Etapa 11 – Listagem e médias no menu
- Objetivo: consultar os dados e os resultados pelo menu
- Entregáveis: listagem de cada dia com sua classificação, opção de médias com classificação geral
- Dependências: Etapas 7 e 8

### Etapa 12 – Criptografia dos dados
- Objetivo: proteger os dados armazenados
- Entregáveis: algoritmo de álgebra linear (por exemplo, Cifra de Hill) para cifrar e decifrar, matriz-chave válida, aplicação na gravação e na leitura do banco
- Dependências: Etapa 6

### Etapa 13 – Testes, documentação e entrega final
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das faixas de classificação (incluindo os limites), das médias e do CRUD, código comentado, README com instruções de execução
- Dependências: todas as anteriores
