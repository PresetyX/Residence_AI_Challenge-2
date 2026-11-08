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
As etapas abaixo são fatias verticais: cada uma atravessa as camadas necessárias (interface, regras e dados) e termina com algo que pode ser demonstrado e testado. A Etapa 1 é o esqueleto mínimo, a funcionalidade mais fina possível funcionando de ponta a ponta.

### Etapa 1 – Esqueleto: criar conta e entrar
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend Node.js/TypeScript, banco de dados, tabela de docentes, cadastro (nome, e-mail, celular e senha), login, tela de login como primeira página e página inicial simples
- Demonstração: criar uma conta, sair e entrar de novo com ela
- Dependências: nenhuma

### Etapa 2 – Recuperação de senha
- Objetivo: permitir recuperar o acesso
- Entregáveis: rota que envia o e-mail de recuperação, tela de "esqueci minha senha" e de nova senha
- Demonstração: pedir a recuperação, receber o e-mail e entrar com a nova senha
- Dependências: Etapa 1

### Etapa 3 – Instituição e curso no primeiro acesso
- Objetivo: começar a organizar o trabalho do docente
- Entregáveis: tabelas de instituição e curso, exigência de pelo menos uma instituição e um curso no primeiro acesso, telas de cadastro e listagem
- Demonstração: entrar pela primeira vez, ser levado ao cadastro e cadastrar PUC-Campinas e Engenharia de Software
- Dependências: Etapa 1

### Etapa 4 – Disciplinas e turmas
- Objetivo: cadastrar o que o docente leciona
- Entregáveis: tabelas de disciplina (nome, sigla, código, período) e turma, rotas e telas de cadastro, edição e listagem
- Demonstração: criar uma disciplina com duas turmas e ver as duas na listagem
- Dependências: Etapa 3

### Etapa 5 – Exclusão com regras de dependência
- Objetivo: evitar perdas acidentais
- Entregáveis: exclusão apenas na ordem turma, disciplina, instituição, bloqueio com mensagem quando houver itens dentro, confirmação em janela modal para excluir turma
- Demonstração: tentar excluir uma disciplina com turma (bloqueado), excluir a turma confirmando na janela e depois a disciplina
- Dependências: Etapa 4

### Etapa 6 – Alunos, um a um
- Objetivo: manter os estudantes de uma turma
- Entregáveis: tabela de alunos com identificador único por turma, inclusão, edição e remoção, remoção por seleção múltipla, tela da turma com a lista
- Demonstração: incluir três alunos, editar um, remover dois por seleção múltipla e tentar repetir um identificador
- Dependências: Etapa 4

### Etapa 7 – Importação de alunos por CSV
- Objetivo: cadastrar vários alunos de uma vez
- Entregáveis: envio do arquivo, leitura das duas primeiras colunas, colunas extras ignoradas, duplicados não sobrescritos, resumo do que foi importado e do que foi ignorado
- Demonstração: importar um CSV com uma coluna extra e um aluno repetido e ver o resumo correto
- Dependências: Etapa 6

### Etapa 8 – Componentes de nota
- Objetivo: definir de que notas a nota final é composta
- Entregáveis: tabela de componentes por disciplina (nome, sigla e descrição), sigla única, telas de cadastro e listagem, colunas dos componentes no quadro da turma
- Demonstração: cadastrar P1, P2 e P3 e ver as três colunas vazias no quadro da turma
- Dependências: Etapas 4 e 6

### Etapa 9 – Lançar notas por componente
- Objetivo: registrar as notas dos alunos
- Entregáveis: quadro em modo de visualização, edição de um componente por vez, validação de 0.00 a 10.00 com duas casas, gravação no banco
- Demonstração: lançar a P1 de toda a turma, tentar uma nota 10.5 (recusada) e ver as notas salvas
- Dependências: Etapa 8

### Etapa 10 – Auditoria por trigger
- Objetivo: registrar toda mudança de nota
- Entregáveis: tabela de log e trigger que grava data e hora do servidor, aluno, nota anterior e nova, tanto no primeiro lançamento quanto nas alterações
- Demonstração: alterar uma nota e conferir no banco o registro com a nota anterior e a nova
- Dependências: Etapa 9

### Etapa 11 – Nota final (média)
- Objetivo: calcular a nota final automaticamente
- Entregáveis: fórmula de média simples ou ponderada definida pela equipe, verificação de que todos os componentes são usados, coluna de nota final somente leitura
- Demonstração: lançar P1, P2 e P3 e ver a nota final correta na coluna calculada
- Dependências: Etapa 9

### Etapa 12 – Exportação em CSV
- Objetivo: entregar as notas da turma em arquivo
- Entregáveis: verificação de que todas as notas e a nota final existem, aviso em caso de pendência, geração do CSV com nome padronizado, download imediato sem guardar o arquivo
- Demonstração: tentar exportar com nota faltando (aviso) e exportar com tudo completo recebendo o arquivo
- Dependências: Etapa 11

### Etapa 13 – Testes, documentação e entrega final
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes das regras de exclusão, da importação, da validação das notas, do cálculo e da exportação, código comentado, README com instruções de execução, versão final publicada
- Demonstração: executar o roteiro completo de uso em um ambiente limpo, seguindo apenas o README
- Dependências: todas as anteriores
