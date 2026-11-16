# Projeto: NotaDez – Gerenciamento de Notas para Docentes
Tipo: App web CRUD
Descrição: Aplicação web para o professor controlar as notas de seus estudantes: cadastra instituições, disciplinas, turmas e alunos, lança as notas por componente e obtém a nota final calculada, com registro de auditoria e exportação das notas.
Login na Etapa 1: sim — a primeira página é o login e não há acesso anônimo.

## Etapas

### Etapa 1 – Esqueleto: criar conta e entrar
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend, banco de dados, tabela de docentes, cadastro (nome, e-mail, celular e senha), login, tela de login como primeira página e página inicial simples
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

### Etapa 10 – Auditoria automática das notas
- Objetivo: registrar toda mudança de nota
- Entregáveis: tabela de log e registro automático no banco que grava data e hora do servidor, aluno, nota anterior e nova, tanto no primeiro lançamento quanto nas alterações
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
