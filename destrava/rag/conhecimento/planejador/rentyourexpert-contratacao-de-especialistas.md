# Projeto: RentYourExpert – Contratação de Especialistas
Tipo: App web CRUD com perfis
Descrição: Plataforma que liga clientes a profissionais especialistas. O cliente procura especialistas por habilidade e local, vê as avaliações, faz perguntas e envia solicitações de serviço; o especialista mantém seu perfil, responde perguntas e aceita ou recusa solicitações; o administrador gerencia clientes, especialistas, solicitações e conteúdo.
Login na Etapa 1: sim — o escopo exige contas para três perfis (cliente, especialista e administrador).

## Etapas

### Etapa 1 – Esqueleto: cadastro e login do cliente de ponta a ponta
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend, banco de dados, tabela de clientes (nome, e-mail e senha protegida), rotas de cadastro e de login, telas de cadastro e de login, página inicial simples
- Demonstração: cadastrar um cliente, entrar com ele e ver a página inicial; tentar cadastrar o mesmo e-mail de novo e ver a recusa
- Dependências: nenhuma

### Etapa 2 – Perfil do cliente, edição e saída
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: consultar e corrigir os dados da conta e sair com segurança
- Entregáveis: rota de leitura do perfil, tela de perfil, rota e formulário de alteração dos dados, botão de sair visível em todas as páginas
- Demonstração: entrar, abrir o perfil e ver os dados; alterar o nome e ver a mudança; clicar em sair e ver que o perfil volta a pedir login
- Dependências: Etapa 1

### Etapa 3 – Especialista: cadastro, login e perfil
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: permitir que profissionais criem conta e mantenham seus dados
- Entregáveis: tabela de especialistas (nome, e-mail, senha protegida, habilidades, cidade e descrição), rotas de cadastro e de login do especialista, telas de cadastro e de login, tela de perfil do especialista com edição das informações, botão de sair
- Demonstração: cadastrar um eletricista com a cidade de São Paulo, entrar, abrir o perfil, mudar a descrição e ver a alteração; tentar abrir o perfil com a conta de cliente e ver a recusa
- Dependências: Etapa 1

### Etapa 4 – Acesso do administrador
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: dar ao administrador uma área própria
- Entregáveis: conta de administrador criada por carga inicial, login do administrador, página inicial do administrador com menu, botão de sair
- Demonstração: entrar como administrador e ver a página inicial com o menu; tentar abrir essa página com uma conta de cliente e ver a recusa
- Dependências: Etapa 1

### Etapa 5 – Catálogo de especialistas
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: deixar o cliente ver quem está disponível
- Entregáveis: rota de listagem dos especialistas, tela de catálogo com nome, habilidades e cidade de cada especialista
- Demonstração: entrar como cliente e ver, no catálogo, o eletricista e os demais especialistas cadastrados
- Dependências: Etapas 2 e 3

### Etapa 6 – Página do especialista
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: mostrar todas as informações de um especialista antes da contratação
- Entregáveis: rota de detalhe do especialista, tela com descrição, habilidades, cidade e contato, link do catálogo para a página
- Demonstração: clicar no eletricista do catálogo e ver a página com todas as informações dele
- Dependências: Etapa 5

### Etapa 7 – Buscar especialistas por habilidade e local
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: achar o profissional certo sem percorrer o catálogo inteiro
- Entregáveis: parâmetros de busca por habilidade e por cidade na rota de listagem, campos de busca no catálogo, botão para limpar a busca, mensagem de "nenhum especialista encontrado"
- Demonstração: buscar "eletricista" em São Paulo e ver só os especialistas correspondentes; buscar uma habilidade inexistente e ver a mensagem
- Dependências: Etapa 5

### Etapa 8 – Cliente envia solicitação de serviço
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: contratar a expertise de um profissional
- Entregáveis: tabela de solicitações (cliente, especialista, descrição do serviço, data e situação inicial "pendente"), rota de envio, botão e formulário "solicitar serviço" na página do especialista
- Demonstração: abrir a página do eletricista, descrever o serviço e enviar a solicitação, vendo a confirmação; tentar enviar com a descrição vazia e ver o erro
- Dependências: Etapa 6

### Etapa 9 – Minhas solicitações e cancelamento
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: acompanhar e cancelar os pedidos feitos
- Entregáveis: rota de solicitações do cliente, lista de solicitações na página de perfil com a situação de cada uma, botão de excluir em cada solicitação com confirmação em janela
- Demonstração: abrir o perfil e ver a solicitação enviada como "pendente"; excluí-la confirmando na janela e ver que sumiu
- Dependências: Etapa 8

### Etapa 10 – Especialista aceita ou recusa solicitações
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: deixar o especialista decidir quais serviços assumir
- Entregáveis: rota de solicitações recebidas pelo especialista, página de solicitações com a lista, botões aceitar e recusar, mudança da situação da solicitação
- Demonstração: entrar como o eletricista, ver a solicitação pendente e aceitá-la; entrar como o cliente e ver a situação "aceita"; recusar uma segunda solicitação e ver "recusada"
- Dependências: Etapas 3 e 9

### Etapa 11 – Perguntas ao especialista
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: tirar dúvidas antes de contratar
- Entregáveis: tabela de perguntas (cliente, especialista, texto e data), rota de envio, campo de texto para perguntar na página do especialista, lista das perguntas feitas por outros clientes
- Demonstração: na página do eletricista, enviar uma pergunta e vê-la na lista; entrar com outro cliente e ver a mesma pergunta
- Dependências: Etapa 6

### Etapa 12 – Especialista responde às perguntas
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: completar o diálogo entre cliente e especialista
- Entregáveis: tabela de respostas (pergunta, texto e data), rota de resposta, lista de perguntas recebidas com campo de resposta, exibição da resposta abaixo da pergunta na página do especialista
- Demonstração: entrar como o eletricista, responder a pergunta e ver a resposta aparecer abaixo dela na página pública
- Dependências: Etapas 3 e 11

### Etapa 13 – Avaliações do especialista
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: ajudar os clientes a decidir com base na opinião de outros
- Entregáveis: tabela de avaliações (cliente, especialista, nota de 1 a 5, comentário e data), rota de envio, formulário de avaliação na página do especialista, seção com as avaliações e a nota média
- Demonstração: avaliar o eletricista com nota 4 e um comentário e ver a avaliação na página; entrar com outro cliente e ver a mesma avaliação e a nota média; tentar enviar nota 7 e ver o erro
- Dependências: Etapa 6

### Etapa 14 – Editar e excluir a própria avaliação
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: deixar o cliente corrigir ou retirar o que escreveu
- Entregáveis: rotas de alteração e de exclusão da avaliação, botões editar e excluir visíveis só na avaliação do próprio cliente, recálculo da nota média
- Demonstração: editar a nota de 4 para 5 e ver a média mudar; excluir a avaliação e ver que sumiu; entrar com outro cliente e ver que ele não tem os botões nessa avaliação
- Dependências: Etapa 13

### Etapa 15 – Administrador gerencia clientes
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: manter a base de clientes sob controle
- Entregáveis: rota e tela de lista de clientes, tela de perfil de cada cliente, formulário de novo cliente, botão de excluir cliente com confirmação em janela
- Demonstração: entrar como administrador, ver a lista de clientes, abrir o perfil de um, criar um cliente novo e excluir outro confirmando na janela
- Dependências: Etapas 2 e 4

### Etapa 16 – Administrador gerencia especialistas
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: manter a base de especialistas sob controle
- Entregáveis: rota e tela de lista de especialistas, tela de perfil de cada especialista, formulário de novo especialista, botão de excluir especialista com confirmação em janela
- Demonstração: entrar como administrador, ver a lista de especialistas, abrir o perfil de um, criar um novo e excluir outro, vendo que ele some do catálogo dos clientes
- Dependências: Etapas 3 e 4

### Etapa 17 – Administrador gerencia solicitações
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: acompanhar e corrigir os pedidos feitos na plataforma
- Entregáveis: rota e tela com todas as solicitações (cliente, especialista, serviço e situação), formulário para adicionar uma solicitação, botão de excluir solicitação com confirmação em janela
- Demonstração: entrar como administrador, ver as solicitações de todos os clientes, adicionar uma e excluir outra confirmando na janela
- Dependências: Etapas 4 e 8

### Etapa 18 – Administrador modera avaliações e perguntas
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: remover conteúdo inadequado
- Entregáveis: botão de excluir avaliação para o administrador, botão de excluir pergunta que apaga também as respostas dela, confirmação em janela
- Demonstração: como administrador, excluir uma avaliação e ver que sumiu da página do especialista; excluir uma pergunta respondida e ver que a pergunta e a resposta sumiram
- Dependências: Etapas 4, 12 e 13

### Etapa 19 – Testes, documentação e entrega final
Contexto: RentYourExpert – Contratação de Especialistas | Tipo: App web CRUD com perfis
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes do cadastro e do login dos três perfis, da busca, das solicitações, das avaliações e das permissões (cliente não abre a área do administrador), código comentado, README com instruções de execução, versão final publicada
- Demonstração: executar o roteiro completo, do cadastro do especialista à solicitação aceita e à avaliação, seguindo apenas o README
- Dependências: todas as anteriores
