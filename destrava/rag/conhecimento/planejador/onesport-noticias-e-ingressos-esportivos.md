# Projeto: OneSport – Notícias e Ingressos Esportivos
Tipo: App web com serviços externos
Descrição: Site de esportes em que o usuário lê as notícias mais recentes e vê os ingressos de eventos esportivos, ambos obtidos de serviços externos. Ele filtra por país, guarda notícias e ingressos de interesse em coleções pessoais e se conecta com outros usuários por pedidos de amizade.
Login na Etapa 1: sim — o escopo exige conta, coleções pessoais e lista de amigos.

## Etapas

### Etapa 1 – Esqueleto: cadastro e login de ponta a ponta
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend, banco de dados, tabela de usuários (nome, e-mail e senha protegida), rotas de cadastro e de login, telas de cadastro e de login, página inicial simples
- Demonstração: cadastrar um usuário, entrar com ele e ver a página inicial; tentar cadastrar o mesmo e-mail de novo e ver a recusa
- Dependências: nenhuma

### Etapa 2 – Barra de navegação, sair e perfil
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: dar ao usuário um menu fixo e acesso aos dados da conta
- Entregáveis: barra de navegação nas páginas com o botão de sair, rota de leitura do perfil, tela de configurações do perfil com nome e e-mail
- Demonstração: entrar, abrir o perfil pela barra de navegação e ver nome e e-mail; clicar em sair e ver que o perfil volta a pedir login
- Dependências: Etapa 1

### Etapa 3 – Alterar e-mail e senha
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: deixar o usuário trocar suas credenciais
- Entregáveis: rota e formulário de alteração do e-mail, rota e formulário de alteração da senha com confirmação da senha atual, validação de e-mail já usado
- Demonstração: trocar o e-mail e a senha, sair e entrar com os novos dados; tentar entrar com os antigos e ver a recusa; tentar usar o e-mail de outro usuário e ver o erro
- Dependências: Etapa 2

### Etapa 4 – Ver as notícias recentes
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: mostrar ao usuário as notícias esportivas mais novas
- Entregáveis: integração com o serviço externo de notícias, chave de acesso guardada em configuração fora do código, rota que devolve as notícias recentes (título, resumo, imagem, data e link), tela de lista de notícias, mensagem de erro quando o serviço externo não responder
- Demonstração: abrir a página de notícias e ver a lista de notícias recentes vinda do serviço externo; desligar a chave de acesso e ver a mensagem de erro em vez de uma página quebrada
- Dependências: Etapa 2

### Etapa 5 – Filtrar notícias por país
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: ver só as notícias do país de interesse
- Entregáveis: parâmetro de país na rota de notícias, menu com os países disponíveis, botão para limpar o filtro
- Demonstração: escolher a Itália no menu e ver só as notícias desse país; escolher outro país e ver a lista mudar; limpar e ver todas
- Dependências: Etapa 4

### Etapa 6 – Notícias favoritas
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: guardar notícias para ler depois
- Entregáveis: tabela de notícias favoritas (usuário e dados da notícia), rotas de adicionar e de remover, botão de favoritar em cada notícia, tela com a coleção de notícias salvas, botão de remover em cada item
- Demonstração: favoritar duas notícias e ver as duas na coleção; remover uma e ver só a outra; sair e entrar de novo e ver que a coleção continua
- Dependências: Etapa 4

### Etapa 7 – Ver os ingressos de eventos
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: mostrar os ingressos disponíveis para os próximos eventos esportivos
- Entregáveis: integração com o serviço externo de ingressos, rota que devolve os eventos próximos (nome, data, local e preço), tela de lista de ingressos, mensagem de erro quando o serviço externo não responder
- Demonstração: abrir a página de ingressos e ver a lista de eventos próximos vinda do serviço externo; simular a falha do serviço e ver a mensagem de erro
- Dependências: Etapa 2

### Etapa 8 – Filtrar ingressos por país
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: ver só os eventos do país de interesse
- Entregáveis: parâmetro de país na rota de ingressos, menu com os países disponíveis, botão para limpar o filtro
- Demonstração: escolher a Itália no menu e ver só os eventos desse país; limpar e ver todos
- Dependências: Etapa 7

### Etapa 9 – Coleção de ingressos
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: guardar os ingressos de interesse para comprar depois
- Entregáveis: tabela de ingressos salvos (usuário e dados do evento), rotas de adicionar e de remover, botão de salvar em cada ingresso, tela com a coleção de ingressos salvos, botão de remover em cada item
- Demonstração: salvar dois ingressos e ver os dois na coleção; remover um e ver só o outro
- Dependências: Etapa 7

### Etapa 10 – Esvaziar as coleções
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: limpar tudo o que foi guardado de uma vez
- Entregáveis: rota que apaga todas as notícias e todos os ingressos salvos do usuário, botão "esvaziar coleções" com confirmação em janela
- Demonstração: com duas notícias e dois ingressos salvos, clicar em esvaziar, confirmar na janela e ver as duas coleções vazias
- Dependências: Etapas 6 e 9

### Etapa 11 – Buscar outro usuário por e-mail
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: encontrar uma pessoa para se conectar
- Entregáveis: rota de busca de usuário por e-mail, tela de busca com campo de e-mail, tela com os dados públicos do usuário encontrado (nome), mensagem de "usuário não encontrado"
- Demonstração: digitar o e-mail de outro usuário cadastrado e ver o nome dele; digitar um e-mail inexistente e ver a mensagem
- Dependências: Etapa 2

### Etapa 12 – Enviar pedido de amizade
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: pedir para outro usuário ser amigo
- Entregáveis: tabela de pedidos de amizade (quem enviou, quem recebeu e situação), rota de envio, botão "enviar pedido" na tela do usuário encontrado, bloqueio de pedido repetido e de pedido para si mesmo
- Demonstração: buscar um usuário, enviar o pedido e ver a confirmação; tentar enviar de novo e ver a recusa
- Dependências: Etapa 11

### Etapa 13 – Aceitar ou recusar pedidos recebidos
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: responder aos pedidos de amizade
- Entregáveis: rota de pedidos recebidos pendentes, tela de pedidos recebidos com os botões aceitar e recusar, tabela de amizades, criação da amizade ao aceitar, remoção do pedido ao recusar
- Demonstração: entrar com o usuário que recebeu o pedido, ver o pedido pendente e aceitá-lo; enviar outro pedido, recusá-lo e ver que ele sumiu da lista
- Dependências: Etapa 12

### Etapa 14 – Lista de amigos
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: ver e gerenciar os amigos
- Entregáveis: rota da lista de amigos, tela com os amigos e seus dados, botão de remover amigo com confirmação em janela
- Demonstração: ver o amigo aceito na lista, abrir seus dados, removê-lo e ver que ele sumiu para os dois lados
- Dependências: Etapa 13

### Etapa 15 – Excluir a própria conta
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: deixar o usuário encerrar sua conta e apagar seus dados
- Entregáveis: rota que apaga a conta junto com as notícias e os ingressos salvos, os pedidos de amizade e as amizades, botão de excluir conta nas configurações do perfil com confirmação em janela
- Demonstração: excluir a conta confirmando na janela e ver o retorno à tela de login; tentar entrar com ela e ver a recusa; ver que o ex-usuário sumiu da lista de amigos do outro
- Dependências: Etapas 3, 10 e 14

### Etapa 16 – Testes, documentação e entrega final
Contexto: OneSport – Notícias e Ingressos Esportivos | Tipo: App web com serviços externos
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes do cadastro e do login, dos filtros por país, das coleções, dos pedidos de amizade e da exclusão de conta, testes com resposta simulada do serviço externo, código comentado, README com instruções de execução, versão final publicada
- Demonstração: executar o roteiro completo, do cadastro até a amizade entre dois usuários e a exclusão da conta, seguindo apenas o README
- Dependências: todas as anteriores
