# Projeto: Sistema de Acompanhamento de Demandas de Desenvolvimento

## Descrição
Aplicação web, inspirada em ferramentas como GitHub Projects, para organizar tarefas, defeitos, melhorias e documentação de projetos de software. Cada projeto tem várias demandas, e cada demanda é acompanhada por status, prioridade, responsável, comentários e histórico de alterações.

## Tipo / domínio
Aplicação web de gestão de demandas. Frontend, API e banco de dados relacional integrados.

## Tecnologias exigidas
- Frontend: HTML5, CSS3, JavaScript (Bootstrap opcional)
- Backend: Node.js (LTS) com TypeScript e Express
- Banco de dados: relacional (MySQL ou Oracle)
- Versionamento: Git e GitHub

## Requisitos principais
- Autenticação com três perfis: Administrador, Líder de Projeto e Membro da Equipe
- Projetos e usuários podem ser inseridos previamente no banco (telas de cadastro dessas entidades são opcionais)
- Demanda vinculada a um projeto, com título, descrição, tipo, prioridade, status, responsável (opcional na criação), data de criação, data da última atualização e prazo de finalização
- Tipos: tarefa, defeito, melhoria, documentação
- Prioridades: crítica, alta, média, baixa
- Status: aberta, em andamento, em revisão, concluída, cancelada (toda demanda nasce "aberta")
- Ciclo de vida: aberta → em andamento → em revisão → concluída; revisão pode voltar a em andamento; qualquer status (exceto concluída) pode ir para cancelada; não pode concluir direto de "em andamento" nem voltar de "em andamento" para "aberta"
- Permissões por perfil: o Membro só move aberta → em andamento → em revisão nas demandas atribuídas a ele; as demais transições, prioridade e responsável ficam com Líder e Administrador
- Proibida a exclusão física: demanda não usada mais é cancelada
- Comentários vinculados a uma demanda e a um usuário, com data e hora
- Histórico automático de alterações (status, responsável, prioridade, prazo, cancelamento), nunca apagado
- Prazo de finalização validado por API externa de feriados nacionais (feriado bloqueia o cadastro ou a atualização do prazo)
- Listagem, filtro por pelo menos dois critérios, busca textual por título ou descrição e ordenação
- Dashboard com totais por status, prioridade e tipo, críticas em aberto e demandas próximas do prazo

## Etapas
As etapas abaixo são fatias verticais: cada uma atravessa as camadas necessárias (interface, regras e dados) e termina com algo que pode ser demonstrado e testado. A Etapa 1 é o esqueleto mínimo, a funcionalidade mais fina possível funcionando de ponta a ponta.

### Etapa 1 – Esqueleto: login de ponta a ponta
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend Node.js/TypeScript/Express, conexão com o banco, tabelas de usuário e projeto com carga inicial de perfis e projetos, rota de login, tela de login e página inicial simples
- Demonstração: entrar com um usuário pré-cadastrado e ver a página inicial conforme o perfil
- Dependências: nenhuma

### Etapa 2 – Cadastrar e listar demandas
- Objetivo: registrar a principal entidade do sistema e vê-la em uma lista
- Entregáveis: tabela de demandas, rota de criação (status inicial "aberta", datas automáticas) e de listagem, formulário de nova demanda e tela de lista
- Demonstração: criar uma demanda e vê-la na lista com os dados principais
- Dependências: Etapa 1

### Etapa 3 – Ver detalhes e editar demanda
- Objetivo: consultar e corrigir uma demanda
- Entregáveis: rotas de detalhe e de edição, tela de detalhes e formulário de edição, atualização da data da última atualização
- Demonstração: abrir uma demanda, alterar título e descrição e ver a mudança salva
- Dependências: Etapa 2

### Etapa 4 – Cancelar demanda
- Objetivo: tirar uma demanda de uso sem apagá-la do banco
- Entregáveis: rota e botão de cancelamento (status "cancelada", sem exclusão física), bloqueio do cancelamento de demandas concluídas
- Demonstração: cancelar uma demanda e ver que ela continua no banco com o status cancelada
- Dependências: Etapa 3

### Etapa 5 – Fluxo básico de status
- Objetivo: acompanhar o andamento da demanda
- Entregáveis: transições aberta → em andamento → em revisão → concluída e em revisão → em andamento, rota e botões de mudança de status, bloqueio de transições inválidas (como concluir direto de "em andamento")
- Demonstração: percorrer o ciclo completo de uma demanda e ver o sistema recusar uma transição inválida
- Dependências: Etapa 3

### Etapa 6 – Permissões por perfil nas ações
- Objetivo: limitar o que cada perfil pode fazer
- Entregáveis: regras no backend e na tela: administrador faz tudo, líder faz tudo no seu projeto, membro só move aberta → em andamento → em revisão nas demandas atribuídas a ele e não conclui nem cancela
- Demonstração: entrar como membro e ver que as ações não permitidas ficam bloqueadas, depois repetir como líder
- Dependências: Etapas 4 e 5

### Etapa 7 – Responsável e prioridade
- Objetivo: organizar quem faz o quê e o que é mais urgente
- Entregáveis: atribuição ou troca de responsável (campo opcional na criação), prioridade (crítica, alta, média, baixa), regras de quem pode alterar, exibição na lista e nos detalhes
- Demonstração: atribuir uma demanda a um membro, mudar a prioridade e ver o resultado na lista
- Dependências: Etapa 6

### Etapa 8 – Prazo com validação de feriado
- Objetivo: definir a data prevista de conclusão sem cair em feriado nacional
- Entregáveis: campo de prazo, integração com API externa de feriados, mensagem de erro e bloqueio do cadastro ou da atualização quando for feriado
- Demonstração: tentar salvar um prazo em feriado e ver a mensagem de erro, depois salvar uma data válida
- Dependências: Etapa 3

### Etapa 9 – Comentários
- Objetivo: registrar conversas e justificativas na demanda
- Entregáveis: tabela de comentários (demanda, usuário, data e hora), rotas de criação e listagem, área de comentários na tela de detalhes
- Demonstração: comentar em uma demanda e ver o comentário com autor, data e hora
- Dependências: Etapa 3

### Etapa 10 – Histórico de alterações
- Objetivo: registrar automaticamente as mudanças importantes
- Entregáveis: tabela de histórico, gravação automática de mudanças de status, responsável, prioridade, prazo e cancelamento, exibição na tela de detalhes, histórico preservado após o cancelamento
- Demonstração: mudar o status de uma demanda e ver a frase do histórico com o nome do usuário
- Dependências: Etapas 5, 6 e 7

### Etapa 11 – Filtros, busca e ordenação
- Objetivo: encontrar demandas rapidamente
- Entregáveis: filtros combinados (status, prioridade, tipo, responsável, projeto), busca por título ou descrição, ordenação por prioridade, data de criação, prazo ou status, controles na tela de lista
- Demonstração: filtrar por status e prioridade ao mesmo tempo, buscar por uma palavra e ordenar por prazo
- Dependências: Etapa 2

### Etapa 12 – Dashboard
- Objetivo: mostrar um resumo do andamento
- Entregáveis: rota de indicadores e tela inicial com totais por status, por prioridade e por tipo, críticas em aberto e demandas próximas do prazo
- Demonstração: abrir a tela inicial e ver os números batendo com a lista de demandas
- Dependências: Etapas 5 e 7

### Etapa 13 – Testes, documentação e entrega final
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das permissões, do fluxo de status e da validação de prazo, código comentado, README com instruções de execução, versão final publicada
- Demonstração: executar o roteiro completo de uso em um ambiente limpo, seguindo apenas o README
- Dependências: todas as anteriores
