# Padrões de etapas por tipo de projeto

## Objetivo deste documento
Cada tipo de projeto de software tem um esqueleto típico de etapas. Este documento descreve esse esqueleto para os tipos mais comuns, para que o planejador reconheça o tipo do projeto recebido e parta da estrutura certa. O esqueleto é um ponto de partida: as etapas finais devem seguir as boas práticas de divisão em fatias verticais (ver o documento de boas práticas), ajustadas ao escopo do projeto.

## Visão geral

| Tipo de projeto | Esqueleto típico (ordem das preocupações) |
|---|---|
| App web CRUD | requisitos → banco → autenticação → telas → testes |
| Pipeline de ML | dados → limpeza → modelo → avaliação → deploy |
| Agente / RAG | base → chunking → embedding → recuperação (retrieval) → avaliação |
| App de terminal com banco | entrada e regras → banco → menu e operações → criptografia ou extras → testes |
| App mobile com API | esqueleto (cadastro e login) → telas e consumo da API → regras de negócio → testes |

Atenção ao ler a tabela: a coluna da direita mostra a **ordem das preocupações técnicas**, e não a lista final de etapas. Se cada preocupação virar uma etapa ("banco", "telas"), o plano fica dividido por camada. A regra é usar a sequência como guia do que deve existir, mas entregar em fatias verticais: uma funcionalidade por vez, atravessando as camadas necessárias.

## Como reconhecer o tipo de projeto
- **App web CRUD:** o escopo fala em cadastros, listagens, perfis de usuário, filtros e dashboards, com frontend, API e banco de dados. Exemplos na base: Sistema de Gerenciamento de Demandas e NotaDez.
- **Pipeline de ML:** o escopo fala em prever, classificar ou agrupar a partir de dados, com treino e avaliação de modelo.
- **Agente / RAG:** o escopo fala em um assistente que responde ou age com base em documentos, ferramentas ou uma base de conhecimento, usando um modelo de linguagem.
- **App de terminal com banco:** o escopo fala em menu de opções, execução pelo terminal e banco de dados, sem interface gráfica. Exemplos: Votação Digital e Monitoramento de Sustentabilidade Pessoal.
- **App mobile com API:** o escopo fala em aplicativo para celular que consome uma API e um banco. Exemplo: MesclaInvest.

Um projeto pode misturar tipos (por exemplo, um app web com um agente embutido). Nesse caso, use o esqueleto de cada parte e organize as etapas pelo que o usuário consegue fazer.

## App web CRUD

### Esqueleto típico
requisitos → banco → autenticação → telas → testes.

### Em fatias verticais
1. Esqueleto: login de ponta a ponta (ambiente, tabela de usuários, rota de login, tela de login).
2. Primeira entidade principal: cadastrar e listar.
3. Ver detalhes e editar.
4. Cancelar ou remover (respeitando regras como "sem exclusão física").
5. Regras de negócio e fluxos (status, transições).
6. Permissões por perfil.
7. Funcionalidades de apoio (comentários, histórico, auditoria).
8. Busca, filtros e ordenação.
9. Dashboard ou relatórios.
10. Importação e exportação, quando existirem.
11. Testes, documentação e entrega.

### Particularidades
- Autenticação aparece cedo, porque quase tudo depende de saber quem é o usuário.
- A modelagem do banco acontece aos poucos, a cada entidade que entra, e não toda de uma vez.
- Dashboard e exportação ficam depois, pois dependem dos dados já existirem.
- Regras de exclusão e dependências entre entidades (por exemplo, não excluir uma instituição que tem turmas) ganham etapa própria.

### Armadilhas
- Etapa "criar todas as telas" ou "criar todo o banco".
- Deixar permissões para o fim, o que obriga a refazer rotas.
- Esquecer recuperação de senha, validações e registros de auditoria quando o escopo os pede.

### Exemplos na base
Sistema de Gerenciamento de Demandas (13 etapas) e NotaDez (13 etapas).

## Pipeline de ML

### Esqueleto típico
dados → limpeza → modelo → avaliação → deploy.

### Em fatias verticais
1. Esqueleto: ler um conjunto pequeno de dados, treinar um modelo simples (linha de base) e mostrar uma métrica. Tudo de ponta a ponta, mesmo que o resultado seja fraco.
2. Separação de treino, validação e teste, feita cedo para não contaminar a avaliação (vazamento de dados).
3. Limpeza dos dados (valores ausentes, duplicados, outliers), com a métrica recalculada para ver o efeito.
4. Criação e seleção de variáveis (features), de novo com a métrica recalculada.
5. Modelo mais forte ou ajuste de hiperparâmetros, comparado com a linha de base.
6. Avaliação mais completa: métricas por tipo de erro, análise de casos errados, teste em dados novos.
7. Empacotamento e entrega do modelo (script de predição, API ou arquivo do modelo).
8. Monitoramento e atualização, quando o escopo prever uso contínuo.
9. Testes, documentação e reprodutibilidade (versões de dados, código e dependências).

### Particularidades
- O primeiro modelo simples vem cedo. Ele dá uma referência de comparação e mostra problemas nos dados antes de gastar esforço em modelos complexos.
- A avaliação não é uma etapa só do fim: cada mudança em dados ou modelo termina com a métrica recalculada.
- A entrega (deploy) é o que torna a fatia vertical útil para um usuário. Sem ela, o projeto fica só em experimento.
- Defina cedo a métrica de sucesso, pois ela orienta todas as decisões seguintes.

### Armadilhas
- Etapas só de "limpeza" sem medir o efeito no resultado.
- Avaliar no mesmo conjunto usado para treinar.
- Começar pelo modelo mais complexo sem uma linha de base.
- Deixar a entrega para depois de meses de experimentos.

## Agente / RAG

### Esqueleto típico
base → chunking → embedding → recuperação (retrieval) → avaliação.

### Em fatias verticais
1. Esqueleto: com poucos documentos, fazer uma pergunta e receber uma resposta do modelo usando trechos recuperados. Tudo de ponta a ponta, mesmo que ainda impreciso.
2. Base de conhecimento organizada: documentos em um formato padronizado, com estrutura que facilita a divisão em trechos.
3. Chunking melhor: tamanho e limites dos trechos respeitando a estrutura dos documentos (por exemplo, uma etapa de projeto por trecho, com o contexto do projeto junto).
4. Embeddings e banco vetorial persistente, com atualização quando a base muda.
5. Recuperação melhorada: número de trechos, filtros por metadados (tipo de projeto, domínio), reordenação, se necessário.
6. Montagem do contexto e do comando (prompt) do agente, com formato de saída definido.
7. Avaliação com perguntas de teste: o trecho certo foi recuperado? A resposta usou o trecho? A saída seguiu o formato?
8. Integração ao agente maior (outros agentes, supervisor, ferramentas).
9. Testes, documentação e ajustes finais.

### Particularidades
- A avaliação deve começar cedo, com um conjunto pequeno de perguntas de teste, para saber se cada mudança em chunking ou recuperação melhorou ou piorou.
- A qualidade da base pesa mais que a escolha do modelo de embeddings: documentos bem estruturados, sem contradições e com exemplos concretos geram melhores resultados.
- Metadados (tipo de projeto, tecnologia, domínio) permitem recuperar o esqueleto certo para o projeto recebido.
- A integração com o agente acontece depois que a recuperação funciona sozinha.

### Armadilhas
- Começar pela interface do agente antes de a recuperação funcionar.
- Documentos longos e sem estrutura, que geram trechos sem sentido isolado.
- Não ter perguntas de teste, o que torna impossível saber se uma mudança ajudou.
- Misturar conteúdos de domínios diferentes sem metadados, causando recuperação confusa.

### Exemplo na base
O próprio RAG do agente planejador, cuja base de conhecimento reúne projetos de exemplo, boas práticas de divisão e este documento de padrões por tipo.

## App de terminal com banco

### Esqueleto típico
entrada e regras → banco → menu e operações → criptografia ou extras → testes.

### Em fatias verticais
1. Esqueleto: uma entrada do usuário, uma regra e uma saída (por exemplo, informar um valor e ver a classificação).
2. Demais regras e validações, uma por vez.
3. Primeira gravação no banco, junto com o menu principal.
4. Listagem e consultas.
5. Alteração e remoção de registros.
6. Cálculos e relatórios sobre vários registros (médias, totais, estatísticas).
7. Segurança e extras exigidos (criptografia, logs, auditoria), mostrando o efeito de ponta a ponta.
8. Testes, documentação e entrega.

### Particularidades
- Validação de entrada (formato, faixa, duplicidade) entra desde as primeiras etapas.
- Se houver logs ou auditoria, a função de log nasce cedo e é usada pelas etapas seguintes.
- Criptografia costuma ser aplicada sobre funcionalidades prontas, por isso é uma etapa de ajuste que altera as telas existentes.

### Exemplos na base
Votação Digital (12 etapas) e Monitoramento de Sustentabilidade Pessoal (11 etapas).

## App mobile com API

### Esqueleto típico
esqueleto (cadastro e login) → telas e consumo da API → regras de negócio → testes.

### Em fatias verticais
1. Esqueleto: cadastro e login de ponta a ponta (app, API e banco).
2. Dados iniciais e primeira lista (por exemplo, o catálogo de itens principais).
3. Filtros e detalhe do item.
4. Interações do usuário (perguntas, comentários).
5. Regras de negócio centrais, quando houver (carteira, negociação), do caso mais simples para o mais complexo.
6. Painéis e gráficos que dependem dos dados anteriores.
7. Segurança complementar (autenticação em dois fatores, por exemplo).
8. Notificações, feed ou atualizações.
9. Testes, documentação e entrega.

### Particularidades
- Os dados iniciais costumam ser carregados por script e entregues ao app por uma rota da API, em vez de telas de cadastro.
- Regras de negócio críticas ficam no backend, e o app apenas as exibe.
- Operações que mexem em vários registros (por exemplo, uma compra que muda saldo e quantidade) são feitas de forma atômica.

### Exemplo na base
MesclaInvest (16 etapas).

## Como usar este documento no planejamento
1. Identifique o tipo (ou os tipos) do projeto pelos sinais de reconhecimento.
2. Parta do esqueleto em fatias verticais correspondente.
3. Adapte ao escopo real: remova o que o projeto não pede, acrescente o que é específico (regras de negócio, integrações, requisitos de segurança).
4. Confira com o checklist do documento de boas práticas: cada etapa é demonstrável, tem dependências claras, e todo requisito do escopo está coberto.
5. Escreva as etapas no formato padrão (objetivo, entregáveis, demonstração e dependências), sem estimativa de tempo.
