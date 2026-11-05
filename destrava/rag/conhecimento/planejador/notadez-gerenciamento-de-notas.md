# Projeto: NotaDez – Gerenciamento de Notas para Docentes

## Descrição
Aplicação 100% web para o professor controlar as notas de seus estudantes. O docente cadastra instituições, cursos, disciplinas e turmas, importa ou cadastra alunos, define os componentes de nota (provas, atividades), lança as notas e obtém a nota final calculada automaticamente. Todo lançamento ou alteração de nota fica registrado em log de auditoria, e as notas podem ser exportadas.

## Tipo / domínio
Aplicação web com autenticação, CRUD de entidades hierárquicas, importação e exportação de arquivos CSV, regras de cálculo e auditoria em banco de dados.

## Tecnologias exigidas
- Backend: Node.js (LTS) com TypeScript
- Frontend: HTML5 e CSS3 (Bootstrap opcional)
- Banco de dados: relacional (MySQL, PostgreSQL ou Oracle)
- Versionamento: Git e GitHub

## Requisitos principais

### Autenticação
- A primeira página é a de login; não há acesso anônimo, modo visitante nem páginas informativas
- Criação de conta com nome, e-mail, telefone celular e senha
- Recuperação de senha por e-mail ("esqueci a minha senha")

### Instituições, disciplinas e turmas
- No primeiro acesso, o docente informa pelo menos uma instituição e um curso
- Disciplina com nome, sigla, código e período do curso
- Turma (conjunto de estudantes de uma disciplina em dia, horário e local), com quantas turmas o docente quiser por disciplina
- Exclusão respeita a ordem de dependências: primeiro turmas, depois disciplinas, depois a instituição (não se exclui o que ainda tem itens dentro)
- Exclusão de turma com notas lançadas pede confirmação simples em janela modal ("Tem certeza que deseja excluir esta turma?") e é irreversível

### Alunos
- Cadastro, edição e remoção de alunos de uma turma, um a um ou por seleção múltipla
- Importação por arquivo CSV, usando só as duas primeiras colunas (identificador e nome completo); as demais são ignoradas
- Importação em turma que já tem alunos: identificador duplicado não sobrescreve (os dados do sistema são a fonte da verdade)

### Componentes de nota
- Componente de nota é qualquer prova, atividade ou tarefa que compõe a nota final
- Cadastro com nome, sigla (usada na fórmula) e descrição; vale para a disciplina e se aplica a todas as turmas
- Nota numérica de 0.00 a 10.00, com duas casas decimais

### Lançamento de notas
- Quadro da turma com alunos nas linhas e componentes nas colunas, sempre aberto em modo de visualização para evitar edição acidental
- Edição das notas de um componente por vez
- Não há desfazer nem refazer

### Auditoria
- Cada nota lançada pela primeira vez ou alterada gera um registro de log salvo no banco de dados por meio de trigger
- Exemplo de registro: data e hora do servidor, aluno e a mudança da nota (de 5.0 para 5.5)
- A auditoria é obrigatória e não pode ser desligada pelo docente

### Cálculo da nota final
- Disponível quando existem componentes cadastrados
- Média simples ou ponderada dos componentes, por exemplo (P1 + P2 + P3) / 3 ou (P1*0,4 + P2*0,3 + P3*0,3), com fórmula fixada pela equipe
- Todos os componentes cadastrados devem entrar na fórmula
- A coluna da nota final é calculada automaticamente e não pode ser editada

### Exportação
- Exportação das notas de uma turma em CSV
- Só é permitida quando todas as notas de todos os alunos estão lançadas e a nota final foi calculada; caso contrário, o sistema avisa
- Nome do arquivo no padrão AAAA-MM-DD_HHmmssms-Turma_Sigla.csv (exemplo: 2025-12-10_223001001-T1-PI2.csv)
- Download imediato, sem guardar o arquivo no servidor nem no banco

### Itens removidos do escopo
- Importação e exportação em JSON (fica só CSV)
- Modo de edição completa das notas (fica só a edição por componente)
- Coluna de notas finais ajustadas e arredondamento de meio em meio ponto
- Confirmação de exclusão de turma por e-mail (substituída por janela modal)
- Exibição do painel de auditoria na tela (fica só o registro via trigger no banco)

## Etapas

### Etapa 1 – Organização do projeto e do ambiente
- Objetivo: deixar o ambiente pronto antes de programar
- Entregáveis: repositório com estratégia de branches, backend Node.js com TypeScript, estrutura do frontend, banco de dados instalado, README inicial
- Dependências: nenhuma

### Etapa 2 – Modelagem do banco de dados
- Objetivo: definir como os dados serão armazenados
- Entregáveis: tabelas de docente, instituição, curso, disciplina, turma, aluno, componente de nota, nota e log de auditoria, relacionamentos e regras de unicidade (identificador do aluno por turma), scripts de criação
- Dependências: Etapa 1

### Etapa 3 – API base e conexão com o banco
- Objetivo: ter um servidor funcionando e conversando com o banco
- Entregáveis: servidor com estrutura de rotas, controladores e acesso a dados, conexão com o banco
- Dependências: Etapa 2

### Etapa 4 – Autenticação
- Objetivo: restringir o uso a docentes cadastrados
- Entregáveis: criação de conta, login, controle de sessão ou token, bloqueio de rotas sem login, recuperação de senha por e-mail
- Dependências: Etapa 3

### Etapa 5 – Instituições, cursos, disciplinas e turmas
- Objetivo: organizar a estrutura de trabalho do docente
- Entregáveis: cadastro, edição e listagem das quatro entidades, regra de exclusão pela ordem de dependências, confirmação modal na exclusão de turma
- Dependências: Etapa 4

### Etapa 6 – Cadastro de alunos
- Objetivo: manter os estudantes de cada turma
- Entregáveis: inclusão, edição e remoção (individual e múltipla), identificador único por turma
- Dependências: Etapa 5

### Etapa 7 – Importação de alunos por CSV
- Objetivo: cadastrar vários alunos de uma vez
- Entregáveis: envio do arquivo, leitura das duas primeiras colunas, ignorar colunas extras, não sobrescrever identificadores duplicados, resumo do que foi importado e do que foi ignorado
- Dependências: Etapa 6

### Etapa 8 – Componentes de nota
- Objetivo: definir de que notas a nota final é composta
- Entregáveis: cadastro com nome, sigla e descrição, validação da sigla única na disciplina, aplicação a todas as turmas
- Dependências: Etapa 5

### Etapa 9 – Quadro e lançamento de notas
- Objetivo: lançar e corrigir as notas dos alunos
- Entregáveis: quadro da turma em modo de visualização, edição por componente, validação de 0.00 a 10.00 com duas casas decimais, gravação no banco
- Dependências: Etapas 6 e 8

### Etapa 10 – Auditoria por trigger
- Objetivo: registrar toda mudança de nota
- Entregáveis: trigger que grava no log a data e hora do servidor, o aluno e a nota anterior e a nova, tanto no primeiro lançamento quanto nas alterações
- Dependências: Etapa 9

### Etapa 11 – Cálculo da nota final
- Objetivo: calcular a nota final automaticamente
- Entregáveis: fórmula de média simples ou ponderada definida pela equipe, verificação de que todos os componentes são usados, coluna de nota final calculada e somente leitura
- Dependências: Etapa 9

### Etapa 12 – Exportação em CSV
- Objetivo: entregar as notas da turma em arquivo
- Entregáveis: verificação de que todas as notas e a nota final existem, aviso em caso de pendência, geração do CSV com o nome padronizado, download imediato sem guardar o arquivo
- Dependências: Etapa 11

### Etapa 13 – Interface (frontend) e integração
- Objetivo: oferecer as telas que usam a API
- Entregáveis: telas de login, recuperação de senha, instituições, disciplinas, turmas, alunos, componentes e quadro de notas, mensagens de erro e confirmação
- Dependências: Etapas 4 a 12 (pode avançar em paralelo, à medida que cada rota fica pronta)

### Etapa 14 – Testes, documentação e entrega final
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das regras de exclusão, da importação, da validação das notas, do cálculo da nota final e da exportação, código comentado, README com instruções de execução, versão final publicada
- Dependências: todas as anteriores
