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

### Etapa 1 – Organização do projeto e do ambiente
- Objetivo: deixar repositório, ferramentas e tarefas prontos antes de programar
- Entregáveis: repositório no GitHub com estratégia de branches, estrutura inicial do backend (Node.js, TypeScript, Express) e do frontend, README inicial
- Dependências: nenhuma

### Etapa 2 – Modelagem do banco de dados
- Objetivo: definir como os dados serão armazenados
- Entregáveis: modelo de dados (usuário, projeto, vínculo usuário-projeto, demanda, comentário, histórico), scripts de criação das tabelas, carga inicial de projetos e usuários
- Dependências: Etapa 1

### Etapa 3 – API base e conexão com o banco
- Objetivo: ter um servidor funcionando e conversando com o banco
- Entregáveis: servidor Express em TypeScript, conexão com o banco, estrutura de rotas, controladores e acesso a dados
- Dependências: Etapa 2

### Etapa 4 – Autenticação e perfis de acesso
- Objetivo: identificar o usuário e limitar o que cada perfil pode fazer
- Entregáveis: login, controle de sessão ou token, verificação de perfil e de vínculo com o projeto nas rotas
- Dependências: Etapa 3

### Etapa 5 – Gestão de demandas
- Objetivo: permitir cadastrar, listar, ver detalhes, editar e cancelar demandas
- Entregáveis: rotas de demanda, status inicial "aberta", datas automáticas, cancelamento no lugar da exclusão, atribuição de responsável
- Dependências: Etapa 4

### Etapa 6 – Ciclo de vida e permissões de status
- Objetivo: garantir que as mudanças de status sigam as regras
- Entregáveis: validação das transições permitidas, regras de cada perfil para alterar status, prioridade e responsável
- Dependências: Etapa 5

### Etapa 7 – Validação do prazo com API de feriados
- Objetivo: impedir prazos em feriados nacionais
- Entregáveis: integração com API externa de feriados, mensagem de erro clara ao cadastrar ou atualizar o prazo
- Dependências: Etapa 5

### Etapa 8 – Comentários e histórico de alterações
- Objetivo: registrar a conversa e a trilha de mudanças de cada demanda
- Entregáveis: cadastro e consulta de comentários, gravação automática do histórico a cada alteração relevante, histórico preservado mesmo após cancelamento
- Dependências: Etapas 5 e 6

### Etapa 9 – Listagem, filtros, busca e ordenação
- Objetivo: encontrar e organizar demandas
- Entregáveis: filtros combinados (status, prioridade, tipo, responsável, projeto), busca por título ou descrição, ordenação por prioridade, data de criação, prazo ou status
- Dependências: Etapa 5

### Etapa 10 – Dashboard
- Objetivo: mostrar um resumo do andamento
- Entregáveis: totais por status, prioridade e tipo, críticas em aberto, demandas próximas do prazo
- Dependências: Etapas 5 e 9

### Etapa 11 – Interface (frontend) e integração
- Objetivo: oferecer telas que consomem a API
- Entregáveis: telas de login, listagem com filtros, detalhes da demanda (comentários e histórico), formulário de demanda, dashboard, com exibição de acordo com o perfil
- Dependências: Etapas 4 a 10 (pode avançar em paralelo, à medida que cada rota fica pronta)

### Etapa 12 – Testes, documentação e entrega final
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das regras de permissão e do ciclo de vida, código comentado, README completo (como executar o projeto), versão final publicada
- Dependências: todas as anteriores
