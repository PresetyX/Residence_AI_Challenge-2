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
As etapas abaixo são fatias verticais: cada uma atravessa as camadas necessárias (interface, regras e dados) e termina com algo que pode ser demonstrado e testado. A Etapa 1 é o esqueleto mínimo, a funcionalidade mais fina possível funcionando de ponta a ponta.

### Etapa 1 – Esqueleto: um dia com a classificação da água
- Objetivo: ter o ambiente e o caminho completo de entrada, regra e saída com o indicador mais simples
- Entregáveis: ambiente Python, repositório com branches, leitura da data e dos litros de água com validação, classificação (alta, moderada ou baixa) e exibição
- Demonstração: informar 180 litros e ver "moderada sustentabilidade"
- Dependências: nenhuma

### Etapa 2 – Energia e resíduos
- Objetivo: classificar mais dois indicadores
- Entregáveis: leitura e validação de kWh e de percentual reciclado (0 a 100), regras de classificação de cada um, exibição junto com a água
- Demonstração: informar 6,5 kWh e 60% reciclado e ver as duas classificações, testando também os valores nos limites das faixas
- Dependências: Etapa 1

### Etapa 3 – Transporte com ponderação
- Objetivo: classificar o meio de transporte
- Entregáveis: menu de meios de transporte (incluindo os que a equipe acrescentar), pesos de cada meio, regra de classificação
- Demonstração: escolher caminhada e ver alta sustentabilidade, escolher carro a combustível e ver baixa
- Dependências: Etapa 2

### Etapa 4 – Sustentabilidade geral do dia
- Objetivo: resumir o dia em uma classificação única
- Entregáveis: regra de ponderação da classificação geral definida pela equipe, exibição do resultado completo no formato do exemplo
- Demonstração: repetir o exemplo do enunciado (24/3/2025) e obter a classificação geral esperada
- Dependências: Etapa 3

### Etapa 5 – Guardar um dia no banco (inserir)
- Objetivo: tornar o cadastro permanente
- Entregáveis: tabela de monitoramento criada manualmente, conexão com o banco, menu principal com a opção Inserir, gravação do registro e exibição da classificação do dia
- Demonstração: cadastrar um dia pelo menu e conferir o registro na tabela
- Dependências: Etapa 4

### Etapa 6 – Listar monitoramentos com classificação
- Objetivo: consultar o que foi cadastrado
- Entregáveis: leitura dos registros no banco, opção de listagem no menu, classificação de cada dia exibida
- Demonstração: cadastrar três dias e ver a lista com as classificações de cada um
- Dependências: Etapa 5

### Etapa 7 – Médias e classificação geral
- Objetivo: resumir vários dias
- Entregáveis: cálculo das médias de água, energia, resíduos, percentual reciclado e transporte, classificação pelas médias, opção de menu
- Demonstração: usar dados de exemplo com média conhecida e ver o resultado bater com o cálculo manual
- Dependências: Etapa 6

### Etapa 8 – Alterar monitoramento
- Objetivo: corrigir um dia já cadastrado
- Entregáveis: escolha do registro, nova entrada com validação, atualização no banco e nova classificação
- Demonstração: alterar o consumo de água de um dia e ver a classificação mudar
- Dependências: Etapa 6

### Etapa 9 – Apagar monitoramento
- Objetivo: remover um registro escolhido
- Entregáveis: escolha do registro, confirmação, remoção no banco e retorno ao menu
- Demonstração: apagar um dia e ver que ele sumiu da lista e das médias
- Dependências: Etapa 6

### Etapa 10 – Criptografia dos dados
- Objetivo: proteger os dados armazenados
- Entregáveis: algoritmo de álgebra linear (por exemplo, Cifra de Hill) com matriz-chave válida, cifra na gravação e decifra na leitura, em todas as opções do menu
- Demonstração: cadastrar um dia, ver os valores cifrados no banco e as telas continuarem mostrando os valores corretos
- Dependências: Etapas 5 a 9

### Etapa 11 – Testes, documentação e entrega final
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das faixas (incluindo os limites), das médias e do CRUD, código comentado, README com instruções de execução
- Demonstração: executar o roteiro completo do menu em um ambiente limpo, seguindo apenas o README
- Dependências: todas as anteriores
