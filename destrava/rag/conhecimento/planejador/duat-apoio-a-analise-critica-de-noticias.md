# Projeto: DUAT – Apoio à Análise Crítica de Notícias
Tipo: Projeto de machine learning com protótipo web
Descrição: Sistema que ajuda o leitor a avaliar a credibilidade de uma notícia sem entregar um veredito pronto. O usuário cola o texto; o sistema calcula critérios de escrita, indica o perfil de escrita do texto e destaca os critérios que mais importam naquele perfil. O usuário registra o seu próprio julgamento e só depois vê a avaliação do modelo, para comparar. Um modelo de classificação e um modelo de agrupamento são treinados com notícias públicas rotuladas como falsas ou verdadeiras.
Login na Etapa 1: não — o sistema não exige contas; qualquer pessoa cola um texto e analisa.

## Etapas

### Etapa 1 – Esqueleto: de um texto colado até uma previsão, com poucos dados
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: ter o ambiente e o ciclo completo, dos dados à tela, funcionando em pequena escala
- Entregáveis: repositório com branches, ambiente de notebooks, mini conjunto de 200 notícias públicas (100 falsas e 100 verdadeiras) com rótulo, um critério simples calculado do texto (tamanho médio da frase), classificador básico treinado com esse mini conjunto, serviço com uma rota que recebe um texto e devolve a previsão, tela mínima com campo de texto e botão analisar
- Demonstração: colar o texto de uma notícia na tela, clicar em analisar e ver a previsão do classificador; ver no notebook a acurácia do classificador no mini conjunto
- Dependências: nenhuma

### Etapa 2 – Montar o conjunto de dados completo
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: reunir notícias suficientes, variadas e balanceadas para o treinamento
- Entregáveis: scripts de coleta de notícias verdadeiras de portais diversos e de notícias falsas desmentidas por agências de checagem, tabela única (texto, rótulo, origem, data de publicação e link), metade das linhas de cada classe, registro de licença e de origem de cada fonte
- Demonstração: carregar a tabela no notebook e ver o total de notícias, a contagem por classe e a contagem por ano
- Dependências: Etapa 1

### Etapa 3 – Limpeza e validação dos dados
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: garantir que os dados estejam consistentes antes de qualquer análise
- Entregáveis: remoção de notícias duplicadas, de textos vazios e de textos muito curtos, validação das colunas e dos tipos, relatório com a quantidade de linhas removidas por motivo
- Demonstração: executar o script de limpeza e ver o relatório com o número de linhas antes e depois, e as classes ainda balanceadas
- Dependências: Etapa 2

### Etapa 4 – Revisão da qualidade dos rótulos
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: descobrir e corrigir amostras com rótulo enganoso antes de treinar
- Entregáveis: revisão manual de uma amostra de 100 notícias por classe, regra automática que encontra textos rotulados como falsos que desmentem a própria notícia (por exemplo, citam a checagem no corpo do texto), substituição dessas amostras por notícias falsas originais, nova versão do conjunto de dados com o número da versão registrado
- Demonstração: abrir a lista das amostras defeituosas encontradas, ver que foram substituídas e conferir que a nova versão continua com as classes balanceadas
- Dependências: Etapa 3

### Etapa 5 – Extrair os critérios de escrita do texto
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: transformar qualquer texto em números que descrevem seu estilo
- Entregáveis: função que recebe um texto e calcula critérios (proporção de verbos, de substantivos, de adjetivos, de advérbios e de pronomes, proporção de palavras sensacionalistas, de fontes citadas e de verbos de dúvida ou de ordem, erros ortográficos, tamanho médio da frase e da palavra, pausas e índice de legibilidade), todos como proporção do total de palavras, aplicação da função a todo o conjunto, testes da função com textos conhecidos
- Demonstração: rodar a função em um texto e ver a tabela de critérios; rodar em um texto curto e em um longo do mesmo estilo e ver que os valores ficam parecidos, por serem proporções
- Dependências: Etapa 4

### Etapa 6 – Análise exploratória dos dados
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: entender como cada critério se comporta nas duas classes
- Entregáveis: notebook com a distribuição de cada critério por classe, correlação de cada critério com o rótulo, correlação entre os critérios, gráficos de caixa e de histograma, lista dos pares de critérios redundantes
- Demonstração: abrir o notebook e ver a tabela de correlação com o rótulo ordenada e o gráfico de dois critérios comparando falsas e verdadeiras
- Dependências: Etapa 5

### Etapa 7 – Escolher o que entra no modelo
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: tirar do treinamento o que é redundante, vaza o rótulo ou não descreve o conteúdo da notícia
- Entregáveis: remoção de critérios redundantes, de metadados (link, fonte, data e categoria) e de contagens brutas que funcionam como atalho de tamanho do texto, tabela com cada coluna mantida ou removida e o motivo, padronização dos critérios restantes
- Demonstração: abrir a tabela de colunas com os motivos; treinar um classificador simples com e sem as contagens de tamanho e ver o desempenho de validação cair pouco sem elas, o que mostra que eram atalho
- Dependências: Etapas 5 e 6

### Etapa 8 – Dividir os dados e definir as métricas
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: criar uma avaliação justa e reutilizável para todos os modelos
- Entregáveis: divisão estratificada em treino (60%), validação (20%) e teste (20%) com semente fixa, regra de que o teste só é usado uma vez no final, função de avaliação com acurácia, precisão, revocação e F1 por classe e matriz de confusão
- Demonstração: rodar a função de avaliação com um classificador qualquer e ver o relatório por classe e a matriz de confusão; conferir que a proporção de falsas e verdadeiras é a mesma nos três conjuntos
- Dependências: Etapa 4

### Etapa 9 – Representar o texto como números
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: deixar o próprio texto da notícia utilizável pelos modelos, além dos critérios de escrita
- Entregáveis: vetorização do texto por frequência ponderada de palavras, com remoção de palavras comuns, limite de vocabulário e frequência mínima, junção da matriz do texto com os critérios padronizados, ajuste do vetorizador apenas no treino
- Demonstração: ver a matriz final com o número de linhas e de colunas, e a lista das dez palavras de maior peso no treino
- Dependências: Etapas 7 e 8

### Etapa 10 – Treinar e comparar três classificadores
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: saber qual tipo de algoritmo se adapta melhor a este problema
- Entregáveis: treinamento de um classificador por vizinhança, de um por margem de separação e de um por conjunto de árvores de decisão com os mesmos dados e a mesma avaliação, tabela comparativa das métricas de validação e de treino
- Demonstração: executar o script e ver a tabela com a acurácia e o F1 por classe de cada algoritmo, e identificar o que está claramente abaixo dos outros
- Dependências: Etapa 9

### Etapa 11 – Ajustar parâmetros e escolher o modelo final
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: escolher o modelo que generaliza melhor, não apenas o de maior nota
- Entregáveis: busca de parâmetros usando só a validação, comparação do desempenho de treino com o de validação para detectar sobreajuste, curvas de aprendizado, avaliação final no conjunto de teste uma única vez, registro da decisão por escrito
- Demonstração: abrir a tabela das combinações testadas, ver a diferença entre treino e validação de cada uma e o resultado final no teste do modelo escolhido
- Dependências: Etapa 10

### Etapa 12 – Agrupar as notícias em perfis de escrita
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: descobrir estilos de escrita que organizem a análise
- Entregáveis: algoritmo de agrupamento sobre os critérios padronizados, escolha do número de grupos por uma métrica de separação, descrição de cada grupo pelos valores médios dos critérios, proporção de notícias falsas e verdadeiras em cada grupo, função que atribui um texto novo ao grupo mais próximo
- Demonstração: passar dois textos de estilos bem diferentes pela função e ver cada um ir para um perfil; abrir a descrição dos perfis e a proporção de falsas e verdadeiras em cada um
- Dependências: Etapa 7

### Etapa 13 – Critérios prioritários de cada perfil
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: mostrar ao usuário os critérios que mais ajudam a avaliar a credibilidade em cada estilo
- Entregáveis: classificador treinado separadamente dentro de cada perfil, cálculo da importância de cada critério, lista dos seis critérios mais importantes por perfil com uma explicação curta do que cada um significa naquele estilo, posição de cada critério (percentil) entre as notícias do mesmo perfil
- Demonstração: abrir a tabela dos seis critérios de cada perfil com a importância e a explicação, e ver que os critérios e os pesos diferem de um perfil para o outro
- Dependências: Etapas 8 e 12

### Etapa 14 – Serviço de análise completo
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: oferecer à tela tudo o que o usuário vai ver sobre um texto
- Entregáveis: modelos e padronizadores salvos em arquivos, rota que recebe o texto e devolve o perfil, os seis critérios prioritários com a posição de cada um e a avaliação do modelo classificador, validação da entrada (texto vazio ou muito curto), mensagens de erro claras, testes da rota
- Demonstração: enviar um texto de notícia e ver a resposta com perfil, critérios e avaliação; enviar um texto vazio e ver a mensagem de erro
- Dependências: Etapas 5, 11, 12 e 13

### Etapa 15 – Tela de análise: perfil e critérios em cores neutras
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: mostrar ao usuário o perfil de escrita e os critérios sem antecipar a avaliação do modelo
- Entregáveis: tela com campo de texto e botão analisar, exibição do perfil de escrita em linguagem simples, tabela dos seis critérios com explicação curta, régua de posição de cada critério entre as notícias do mesmo perfil, gráfico de radar da notícia sobre a notícia típica, cores neutras, mensagem de carregamento e de erro
- Demonstração: colar uma notícia, ver o perfil, a tabela, as réguas e o radar, e confirmar que nenhum elemento indica se a notícia é falsa ou verdadeira
- Dependências: Etapa 14

### Etapa 16 – Veredito do usuário e comparação com o modelo
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: fazer o usuário julgar primeiro e só depois ver a avaliação do modelo
- Entregáveis: tabela de análises (texto, perfil, veredito do usuário e avaliação do modelo), botões de veredito (falsa, verdadeira ou não sei) com campo opcional de justificativa, rota que registra o veredito, tela de comparação que só aparece depois do registro, indicação dos critérios em que o usuário e o modelo divergem, aviso de que o resultado do modelo é apoio à decisão e pode errar
- Demonstração: analisar uma notícia, tentar abrir a comparação antes de votar e ver o bloqueio; registrar o veredito e ver a avaliação do modelo ao lado dele, com os critérios que divergem em destaque
- Dependências: Etapa 15

### Etapa 17 – Validação com usuários do público-alvo
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: verificar se as visualizações são compreendidas e ajudam a analisar a notícia
- Entregáveis: roteiro com tarefas dirigidas, sessões com cinco pessoas de 40 a 65 anos pensando em voz alta, registro da taxa de sucesso e do tempo de cada tarefa, questionário de usabilidade ao final, lista priorizada de ajustes na interface
- Demonstração: apresentar o relatório com a taxa de sucesso, os tempos, a nota do questionário e as três principais dificuldades encontradas, e mostrar os ajustes já aplicados
- Dependências: Etapa 16

### Etapa 18 – Documentação e entrega final
Contexto: DUAT – Apoio à Análise Crítica de Notícias | Tipo: Projeto de machine learning com protótipo web
- Objetivo: deixar o projeto reproduzível e pronto para uso
- Entregáveis: testes da extração de critérios, da rota de análise e do bloqueio da comparação, relatório dos experimentos com as versões do conjunto de dados e as decisões tomadas, limitações e cuidados éticos (dados públicos, apoio à decisão e não veredito), código comentado, README com instruções para treinar e executar, versão final publicada
- Demonstração: seguindo apenas o README, preparar o ambiente, treinar os modelos e executar o roteiro completo, da colagem do texto à comparação com o veredito do usuário
- Dependências: todas as anteriores
