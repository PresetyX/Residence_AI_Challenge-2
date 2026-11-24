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
- **App web CRUD:** o escopo fala em cadastros, listagens, perfis de usuário, filtros e dashboards, com frontend, API e banco de dados. Exemplos na base: Sistema de Gerenciamento de Demandas, NotaDez, 4 by 4 (jogos online), CDC Shop (loja virtual) e RentYourExpert (contratação de especialistas). Variações de app web, com exemplos próprios, estão na seção "Variações de app web".
- **Pipeline de ML:** o escopo fala em prever, classificar ou agrupar a partir de dados, com treino e avaliação de modelo. Quando o escopo também pede que o usuário use o resultado em uma tela, o projeto é de machine learning com protótipo web. Exemplo na base: DUAT.
- **Agente / RAG:** o escopo fala em um assistente que responde ou age com base em documentos, ferramentas ou uma base de conhecimento, usando um modelo de linguagem.
- **App de terminal com banco:** o escopo fala em menu de opções, execução pelo terminal e banco de dados, sem interface gráfica. Exemplos: Votação Digital e Monitoramento de Sustentabilidade Pessoal.
- **App mobile com API:** o escopo fala em aplicativo para celular que consome uma API e um banco. Exemplos: MesclaInvest e ExamRush.

Um projeto pode misturar tipos (por exemplo, um app web com um agente embutido, ou um projeto de ML com uma tela). Nesse caso, use o esqueleto de cada parte e organize as etapas pelo que o usuário consegue fazer.

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
- Busca, ordenação e filtros são etapas próprias, depois da listagem que elas refinam (CDC Shop: ordenar por preço e buscar por nome vêm depois do catálogo).
- Perfil e saída da conta vêm logo depois do esqueleto, porque várias etapas seguintes dependem de mostrar o usuário logado.
- Excluir a própria conta ou um usuário fica perto do fim, quando já existem todos os dados ligados a ele que a exclusão precisa apagar.

### Armadilhas
- Etapa "criar todas as telas" ou "criar todo o banco".
- Deixar permissões para o fim, o que obriga a refazer rotas.
- Esquecer recuperação de senha, validações e registros de auditoria quando o escopo os pede.
- Juntar em uma só etapa o cadastro, a edição e a exclusão de uma entidade, sem nada que mostre cada operação separadamente.

### Exemplos na base
Sistema de Gerenciamento de Demandas (13 etapas), NotaDez (13), 4 by 4 (16), CDC Shop (16) e RentYourExpert (19).

## Variações de app web

Os projetos abaixo seguem o esqueleto de app web CRUD, mas têm uma preocupação a mais que muda a ordem das etapas.

### Web com vários perfis (administrador, gerente, especialista, lojista)
Exemplos: RentYourExpert (cliente, especialista e administrador), WattsUp (usuário, gerente de nó central e produtor), CDC Shop (cliente e lojista).
- O perfil extra ganha etapas próprias logo depois do esqueleto: conta criada por carga inicial (quando o escopo não prevê cadastro desse perfil), login, página inicial própria e recusa de acesso a quem tem outro perfil.
- Cada perfil tem sua fatia: o administrador gerencia clientes, especialistas e solicitações em etapas separadas, e a moderação de conteúdo vem depois que o conteúdo existe.
- Ações que envolvem dois perfis ficam em duas etapas, uma para cada lado: o cliente envia a solicitação e, depois, o especialista aceita ou recusa; o cliente pergunta e, depois, o especialista responde.
- Armadilha: uma etapa "área do administrador" com todas as telas de uma vez.

### Web com compra e pagamento (loja, marketplace)
Exemplos: CDC Shop, E-Farmers (feira de produtores com entrega).
- A sequência é carrinho → pedido → pagamento → histórico de pedidos. Gerar o pedido cria os itens e esvazia o carrinho em uma única operação.
- O pagamento usa um serviço externo e tem etapa própria, mostrando também o caso de pagamento recusado, com o pedido ainda aguardando pagamento.
- O catálogo e a gestão de produtos pelo lojista ou agricultor vêm antes do carrinho, pois o carrinho depende de itens que existam.
- Entrega, quando existe, vem depois do pedido pago: escolha da entrega, página do entregador e, em etapa seguinte, atualização da situação do pedido.
- Recursos de relacionamento (seguir, notificações, comentários, selos) ficam depois do fluxo de compra, porque dependem de vendas e de publicações já existentes.
- Armadilha: uma etapa "carrinho e pagamento" que mistura três fluxos.

### Web com monitoramento e faturamento
Exemplo: WattsUp (energia elétrica).
- Os dados a monitorar entram antes do painel: cadastro do dispositivo, depois as leituras, depois o painel com gráficos. O painel nunca vem antes de haver leituras para mostrar.
- Dicas, alertas e faturas são derivados dos dados e vêm depois do painel.
- A fatura gera uma notificação, então a central de notificações entra antes da fatura.
- Transações (compra e venda) vêm por último, depois da forma de pagamento, e mostram uma confirmação ao concluir.
- Armadilha: um painel feito com dados falsos e sem etapa de carga de dados reais.

### Web com serviços externos
Exemplo: OneSport (notícias e ingressos vindos de serviços externos).
- Cada serviço externo ganha uma etapa de integração própria, que entrega a lista vinda do serviço, com a chave de acesso guardada em configuração fora do código e uma mensagem de erro quando o serviço não responde.
- Filtros e coleções pessoais (favoritos) vêm depois da integração que os alimenta.
- Os testes usam resposta simulada do serviço externo, para não depender dele estar no ar.
- Armadilha: deixar o tratamento de falha do serviço externo para o fim.

### Web com processamento em segundo plano
Exemplo: ChronoPic (fotos com detecção de idade).
- O envio responde na hora, e o resultado chega depois: a foto fica com a situação "processando" e passa a "concluída" ou "com falha". Essa mudança de situação é o que a demonstração mostra.
- O processamento vem depois do envio e da listagem, que já funcionam sem ele.
- Consultar o resultado de uma foto e consultar o de várias de uma vez são etapas separadas.
- Excluir também apaga os resultados ligados ao item.
- Armadilha: processar tudo dentro do envio, fazendo o usuário esperar.

## Pipeline de ML

### Esqueleto típico
dados → limpeza → modelo → avaliação → deploy.

### Em fatias verticais
1. Esqueleto: ler um conjunto pequeno de dados, treinar um modelo simples (linha de base) e mostrar uma métrica. Tudo de ponta a ponta, mesmo que o resultado seja fraco. Quando o escopo tem tela, o esqueleto inclui uma entrada mínima (colar um texto, enviar um arquivo) que mostra a previsão.
2. Montagem do conjunto completo de dados, com origem e licença de cada fonte registradas.
3. Limpeza dos dados (valores ausentes, duplicados, outliers), com a métrica recalculada para ver o efeito.
4. Revisão da qualidade dos rótulos: amostra conferida à mão e correção das amostras com rótulo enganoso, com a nova versão do conjunto registrada.
5. Criação das variáveis (features) e análise exploratória: distribuição por classe, correlação com o alvo e entre as variáveis.
6. Seleção de variáveis: retirar o que é redundante, o que vaza o resultado e o que funciona como atalho (por exemplo, identificadores, datas e contagens que só refletem o tamanho do dado), com o motivo de cada remoção.
7. Separação de treino, validação e teste e definição das métricas. Essa etapa deve vir antes de comparar modelos, para não contaminar a avaliação (vazamento de dados). O teste só é usado uma vez, no final.
8. Comparação de modelos de tipos diferentes, com os mesmos dados e as mesmas métricas, contra a linha de base.
9. Ajuste de hiperparâmetros e escolha do modelo final pela capacidade de generalizar (diferença entre treino e validação), não só pela maior nota.
10. Avaliação mais completa: métricas por tipo de erro, análise de casos errados, teste em dados novos.
11. Empacotamento e entrega do modelo (modelos salvos, script de predição ou serviço com uma rota).
12. Interface para o usuário, quando o escopo pede, mostrando a saída do modelo de forma compreensível.
13. Validação com usuários do público-alvo, quando o público não é técnico (tarefas dirigidas, taxa de sucesso, tempo e questionário de usabilidade).
14. Monitoramento e atualização, quando o escopo prever uso contínuo.
15. Testes, documentação e reprodutibilidade (versões de dados, código e dependências).

### Particularidades
- O primeiro modelo simples vem cedo. Ele dá uma referência de comparação e mostra problemas nos dados antes de gastar esforço em modelos complexos.
- A avaliação não é uma etapa só do fim: cada mudança em dados ou modelo termina com a métrica recalculada.
- A entrega (deploy) é o que torna a fatia vertical útil para um usuário. Sem ela, o projeto fica só em experimento.
- Defina cedo a métrica de sucesso, pois ela orienta todas as decisões seguintes.
- Quando o projeto agrupa dados (aprendizado não supervisionado), o agrupamento ganha etapa própria, com a descrição de cada grupo e uma função que atribui um dado novo a um grupo. O resultado do agrupamento só serve ao usuário se houver uma etapa que o transforme em algo que ele veja.
- Quando a explicação é parte do escopo, o modelo é escolhido também pela facilidade de explicar, e a importância de cada variável vira uma etapa.
- Quando o usuário deve julgar antes de ver o modelo, a tela de resultado fica em duas etapas: primeiro o que não revela a resposta, depois o registro do julgamento e a comparação com o modelo.

### Armadilhas
- Etapas só de "limpeza" sem medir o efeito no resultado.
- Avaliar no mesmo conjunto usado para treinar.
- Começar pelo modelo mais complexo sem uma linha de base.
- Deixar a entrega para depois de meses de experimentos.
- Treinar com colunas que revelam o resultado ou que só medem o tamanho do dado.
- Confiar nos rótulos sem conferir uma amostra.

### Exemplo na base
DUAT, apoio à análise crítica de notícias (18 etapas), com classificação, agrupamento em perfis, serviço de análise, telas e validação com usuários.

## Agente / RAG

### Esqueleto típico
base → chunking → embedding → recuperação (retrieval) → avaliação.

### Em fatias verticais
1. Esqueleto: com poucos documentos, fazer uma pergunta e receber uma resposta do modelo usando trechos recuperados. Tudo de ponta a ponta, mesmo que ainda impreciso.
2. Base de conhecimento organizada: documentos em um formato padronizado, com estrutura que facilita a divisão em trechos.
3. Chunking melhor: tamanho e limites dos trechos respeitando a estrutura dos documentos (por exemplo, uma etapa de projeto por trecho, com o contexto do projeto junto: nome e tipo).
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
- A avaliação mede a recuperação separada da geração: primeiro se os trechos certos vieram, depois se o plano os usou.

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
5. Regras de negócio centrais, quando houver (carteira, negociação, resposta de um quiz), do caso mais simples para o mais complexo.
6. Painéis e gráficos que dependem dos dados anteriores.
7. Segurança complementar (autenticação em dois fatores, por exemplo).
8. Notificações, feed ou atualizações.
9. Testes, documentação e entrega.

### Particularidades
- Os dados iniciais costumam ser carregados por script e entregues ao app por uma rota da API, em vez de telas de cadastro.
- Regras de negócio críticas ficam no backend, e o app apenas as exibe.
- Operações que mexem em vários registros (por exemplo, uma compra que muda saldo e quantidade) são feitas de forma atômica.
- Recursos do aparelho (galeria de fotos, sensor de movimento, câmera) ganham etapa própria, depois da funcionalidade que eles controlam já funcionar por toque: no ExamRush, responder por toque vem antes de passar de pergunta inclinando o celular, com opção de desligar o movimento.
- Quando há funções diferentes (aluno e professor), a função é escolhida no cadastro do esqueleto e as telas de cada função entram em etapas separadas.
- Animações e acabamento visual ficam perto do fim, depois que as telas principais existem.

### Exemplos na base
MesclaInvest (16 etapas) e ExamRush (13 etapas).

## Como usar este documento no planejamento
1. Identifique o tipo (ou os tipos) do projeto pelos sinais de reconhecimento.
2. Parta do esqueleto em fatias verticais correspondente.
3. Adapte ao escopo real: remova o que o projeto não pede, acrescente o que é específico (regras de negócio, integrações, requisitos de segurança).
4. Confira com o checklist do documento de boas práticas: cada etapa é demonstrável, tem dependências claras, e todo requisito do escopo está coberto.
5. Escreva as etapas no formato padrão (objetivo, entregáveis, demonstração e dependências), sem estimativa de tempo.
