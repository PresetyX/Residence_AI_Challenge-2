# Projeto: ExamRush – Quiz de Estudo no Celular
Tipo: App mobile com API
Descrição: Aplicativo de celular para estudar com perguntas de múltipla escolha. O professor monta baralhos de perguntas; o aluno escolhe um baralho, responde por toque ou inclinando o celular e acompanha seu desempenho em estatísticas. Cada usuário tem conta e foto de perfil.
Login na Etapa 1: sim — o escopo exige conta com e-mail e senha, e o professor e o aluno têm funções diferentes.

## Etapas

### Etapa 1 – Esqueleto: cadastro e login de ponta a ponta
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando app, API e banco
- Entregáveis: repositório com branches, projeto do app, API, banco de dados, tabela de usuários (nome, e-mail, senha protegida e função de aluno ou professor), rotas de cadastro e de login, telas de cadastro e de login, tela inicial simples
- Demonstração: cadastrar um aluno e um professor, entrar com cada um e ver a tela inicial; tentar cadastrar o mesmo e-mail de novo e ver a recusa
- Dependências: nenhuma

### Etapa 2 – Foto de perfil
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: deixar o usuário personalizar a conta com uma foto
- Entregáveis: campo de foto no cadastro do usuário, rota de envio e de troca da foto, tela de perfil com a foto atual, escolha da imagem na galeria do celular, imagem padrão para quem não enviou foto
- Demonstração: abrir o perfil, escolher uma foto da galeria e ver a foto aparecer; trocar por outra e ver a nova; sair e entrar de novo e ver que a foto continua
- Dependências: Etapa 1

### Etapa 3 – Filtro de desenho animado na foto
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: deixar a foto de perfil divertida
- Entregáveis: opção "aplicar filtro de desenho animado" na tela de perfil, geração da versão filtrada a partir da foto original, rota para salvar a versão escolhida, botão para voltar à foto original
- Demonstração: aplicar o filtro na foto do perfil e ver a versão em desenho; salvar, sair e entrar de novo e ver a versão filtrada; voltar à original
- Dependências: Etapa 2

### Etapa 4 – Professor cria baralhos
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: permitir que o professor comece a montar o material de estudo
- Entregáveis: tabela de baralhos (título, assunto e professor dono), rota de criação, tela de novo baralho, lista dos baralhos do professor
- Demonstração: entrar como professor, criar o baralho "Geografia – Capitais" e ver o baralho na lista; tentar criar um baralho como aluno e ver que a opção não aparece
- Dependências: Etapa 1

### Etapa 5 – Professor adiciona perguntas ao baralho
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: preencher o baralho com perguntas de múltipla escolha
- Entregáveis: tabela de perguntas (enunciado, quatro alternativas e alternativa correta, ligadas ao baralho), rota de cadastro, formulário de nova pergunta, lista das perguntas do baralho, edição e remoção de pergunta
- Demonstração: no baralho "Geografia – Capitais", cadastrar a pergunta "Qual é a capital do Brasil?" com a alternativa correta marcada e ver a pergunta na lista; editar o enunciado e ver a mudança; tentar salvar sem alternativa correta e ver o erro
- Dependências: Etapa 4

### Etapa 6 – Aluno lista e escolhe baralhos
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: deixar o aluno ver o que há para estudar
- Entregáveis: rota de listagem de todos os baralhos com o número de perguntas, tela de baralhos do aluno, tela de detalhes do baralho com botão "começar"
- Demonstração: entrar como aluno, ver o baralho criado pelo professor com seu número de perguntas e abrir a tela de detalhes
- Dependências: Etapas 2 e 5

### Etapa 7 – Buscar baralhos
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: achar um baralho rápido por assunto ou palavra
- Entregáveis: parâmetro de busca por título, assunto ou palavra-chave na rota de listagem, barra de busca na tela de baralhos, mensagem de "nenhum resultado"
- Demonstração: digitar "capitais" na barra de busca e ver só os baralhos correspondentes; digitar um termo inexistente e ver a mensagem
- Dependências: Etapa 6

### Etapa 8 – Responder às perguntas por toque
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: fazer o aluno estudar de verdade, respondendo e vendo o resultado
- Entregáveis: tela de pergunta com as quatro alternativas, rota que recebe a resposta e diz se está certa, indicação de acerto ou erro com a resposta correta, tabela de sessões de estudo (aluno, baralho, data e acertos por pergunta), tela de resumo ao fim do baralho
- Demonstração: começar um baralho, responder tocando nas alternativas, ver o acerto ou o erro de cada uma e, ao fim, o resumo com a nota da sessão
- Dependências: Etapa 6

### Etapa 9 – Professor testa o próprio baralho
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: deixar o professor conferir se o baralho está certo antes de liberá-lo
- Entregáveis: botão "testar baralho" na lista do professor, uso da mesma tela de perguntas em modo de teste, resultado do teste que não entra nas estatísticas de alunos
- Demonstração: entrar como professor, testar o baralho, responder as perguntas e ver o resumo; conferir que nenhuma sessão de aluno foi registrada
- Dependências: Etapas 5 e 8

### Etapa 10 – Passar de pergunta com o movimento do celular
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: tornar a navegação entre perguntas mais interativa
- Entregáveis: leitura do sensor de movimento do celular, inclinar para a direita avança e para a esquerda volta, limite de sensibilidade para evitar passar por acidente, opção de ligar e desligar o movimento nas configurações
- Demonstração: durante um baralho, inclinar o celular para a direita e ver a próxima pergunta, para a esquerda e ver a anterior; desligar a opção e ver que o movimento não faz nada
- Dependências: Etapa 8

### Etapa 11 – Estatísticas de desempenho
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: mostrar ao aluno como ele está indo
- Entregáveis: rota de estatísticas calculadas a partir das sessões (média de acertos, assuntos com mais acertos e com mais erros, evolução ao longo do tempo), tela de estatísticas com gráfico de evolução
- Demonstração: depois de três sessões com notas diferentes, abrir as estatísticas e ver a média, o assunto mais forte e o mais fraco e o gráfico subindo ou descendo conforme as notas
- Dependências: Etapa 8

### Etapa 12 – Animações e acabamento da interface
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: deixar o aplicativo envolvente e fácil de usar
- Entregáveis: animação de transição entre perguntas, efeito visual de acerto e de erro, animação na abertura do resumo, mensagens de carregamento e de erro padronizadas
- Demonstração: percorrer um baralho completo e ver as transições e os efeitos de acerto e de erro funcionando em todas as telas
- Dependências: Etapas 10 e 11

### Etapa 13 – Testes, documentação e entrega final
Contexto: ExamRush – Quiz de Estudo no Celular | Tipo: App mobile com API
- Objetivo: validar o aplicativo e deixá-lo pronto para uso
- Entregáveis: testes do cadastro e do login, das permissões (aluno não cria baralho), da correção das respostas e das estatísticas, código comentado, README com instruções de execução, versão final instalável
- Demonstração: executar o roteiro completo, do cadastro do professor à criação do baralho e, depois, do cadastro do aluno às estatísticas, seguindo apenas o README
- Dependências: todas as anteriores
