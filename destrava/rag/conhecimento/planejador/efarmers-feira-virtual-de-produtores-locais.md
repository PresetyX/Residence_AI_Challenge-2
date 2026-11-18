# Projeto: E-Farmers – Feira Virtual de Produtores Locais
Tipo: App web de marketplace com papéis
Descrição: Loja virtual que liga agricultores locais a clientes que querem produtos frescos. O agricultor publica inserções com caixas de produtos; o cliente procura, compra ou reserva e acompanha o pedido; quem não pode buscar na propriedade recebe em casa por um entregador. Há também seguidores, notificações, comentários e selos.
Login na Etapa 1: sim — o escopo exige contas e papéis diferentes (cliente, agricultor e entregador).

## Etapas

### Etapa 1 – Esqueleto: cadastro e login de ponta a ponta
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend, banco de dados, tabela de usuários (nome, e-mail e senha protegida), rotas de cadastro e de login, telas de cadastro e de login, página inicial simples
- Demonstração: cadastrar um usuário, entrar com ele e ver a página inicial; tentar cadastrar o mesmo e-mail de novo e ver a recusa
- Dependências: nenhuma

### Etapa 2 – Perfil, edição dos dados e saída
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: consultar e corrigir os dados da conta e sair com segurança
- Entregáveis: rota de leitura do perfil, tela de página pessoal, rota e formulário de alteração dos dados, botão de sair
- Demonstração: entrar, abrir a página pessoal e ver os dados; alterar o nome e ver a mudança; clicar em sair e ver que a página volta a pedir login
- Dependências: Etapa 1

### Etapa 3 – Cadastro com conta de outro serviço
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: oferecer um jeito mais rápido de criar a conta
- Entregáveis: botão "entrar com outra conta" nas telas de cadastro e de login, rota de retorno que recebe os dados do serviço externo, criação do usuário no primeiro acesso, ligação à conta existente quando o e-mail já estiver cadastrado
- Demonstração: clicar no botão, autorizar o acesso, ver o usuário criado e a página inicial; sair e entrar de novo pelo mesmo botão e ver o mesmo usuário
- Dependências: Etapa 1

### Etapa 4 – Mudar a função da conta
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: deixar o cliente passar a vender ou a entregar
- Entregáveis: campo de função na tabela de usuários (cliente, agricultor ou entregador), rota e botão para mudar a função na página pessoal, menu que muda conforme a função
- Demonstração: um cliente muda para agricultor e ver o menu de agricultor; mudar outra conta para entregador e ver o menu de entregador
- Dependências: Etapa 2

### Etapa 5 – Agricultor publica inserções com caixas
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: colocar produtos à venda
- Entregáveis: tabela de inserções (agricultor, título, descrição e data), tabela de caixas (inserção, produto, quantidade, preço e validade), rotas e formulários de nova inserção e de nova caixa, lista das inserções do agricultor
- Demonstração: entrar como agricultor, publicar a inserção "Hortaliças da semana" com duas caixas, uma de alface e uma de tomate, e ver a inserção e suas caixas na lista; tentar publicar como cliente e ver que a opção não aparece
- Dependências: Etapa 4

### Etapa 6 – Editar e excluir inserções
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: manter as inserções corretas
- Entregáveis: rotas de alteração e de exclusão de inserção e de caixa, botões editar e excluir visíveis só para o dono, confirmação em janela
- Demonstração: mudar o preço da caixa de tomate e ver o novo valor; excluir a inserção confirmando na janela e ver que sumiu; entrar com outro agricultor e ver que ele não tem os botões nessa inserção
- Dependências: Etapa 5

### Etapa 7 – Buscar inserções e ver caixas que vencem em breve
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: ajudar visitantes e clientes a achar produtos
- Entregáveis: rota pública de busca de inserções por palavra, tela de busca aberta a visitantes sem login, lista de caixas com validade nos próximos dias, mensagem de "nenhuma inserção encontrada"
- Demonstração: sem entrar, buscar "tomate" e ver a inserção correspondente; abrir a lista de caixas que vencem em breve e ver a caixa de alface com a validade
- Dependências: Etapa 5

### Etapa 8 – Página do agricultor
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: mostrar quem vende os produtos
- Entregáveis: rota de detalhe do agricultor, tela com nome, descrição e inserções ativas, link das inserções para a página do agricultor
- Demonstração: abrir uma inserção, clicar no nome do agricultor e ver a página dele com as inserções ativas
- Dependências: Etapa 7

### Etapa 9 – Calendário de alimentos sazonais
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: mostrar o que está na safra em cada mês
- Entregáveis: tabela de alimentos sazonais (alimento e meses de safra) com carga inicial, rota por mês, tela de calendário com a lista do mês escolhido
- Demonstração: abrir o calendário, escolher janeiro e ver os alimentos da safra; escolher julho e ver a lista mudar
- Dependências: Etapa 2

### Etapa 10 – Carrinho de compras
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: juntar as caixas que o cliente quer comprar
- Entregáveis: tabela de itens do carrinho (cliente, caixa e quantidade), rotas de adicionar e de remover, botão de adicionar em cada caixa, tela do carrinho com os itens e o total, botão de remover em cada item
- Demonstração: adicionar duas caixas ao carrinho, ver os dois itens e o total; remover uma e ver o total diminuir
- Dependências: Etapas 2 e 7

### Etapa 11 – Gerar o pedido a partir do carrinho
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: transformar o carrinho em uma compra
- Entregáveis: tabela de pedidos (cliente, data, valor e situação "aguardando pagamento") e de itens do pedido, rota que cria o pedido com os itens do carrinho e esvazia o carrinho em uma única operação, tela de resumo do pedido
- Demonstração: com duas caixas no carrinho, gerar o pedido, ver o resumo com os itens e o valor e ver o carrinho vazio; tentar gerar com o carrinho vazio e ver o erro
- Dependências: Etapa 10

### Etapa 12 – Pagamento seguro do pedido
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: cobrar o cliente com segurança
- Entregáveis: integração com o serviço de pagamento externo, rota que inicia o pagamento do pedido, tela de pagamento, tratamento do retorno do serviço, mudança da situação do pedido para paga
- Demonstração: pagar o pedido com um cartão de teste e ver a situação mudar para paga; usar um cartão recusado e ver a mensagem de erro com o pedido ainda aguardando pagamento
- Dependências: Etapa 11

### Etapa 13 – Histórico de pedidos
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: lembrar o que foi comprado
- Entregáveis: rota de pedidos do cliente, tela com a lista de pedidos (data, valor e situação), tela de detalhes com os itens
- Demonstração: abrir o histórico, ver o pedido pago e abrir os detalhes com os itens e o valor
- Dependências: Etapa 12

### Etapa 14 – Reservar uma caixa pelo calendário
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: garantir um produto antes da safra
- Entregáveis: tabela de reservas (cliente, agricultor, produto, mês e situação "pendente"), rota de envio de reserva, botão "reservar" nos alimentos do calendário, lista das reservas do cliente com a situação de cada uma
- Demonstração: escolher um alimento do calendário, reservar e ver a reserva como "pendente" na lista do cliente
- Dependências: Etapas 5 e 9

### Etapa 15 – Agricultor aceita ou recusa reservas
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: deixar o agricultor decidir quais reservas atender
- Entregáveis: rota de reservas recebidas pelo agricultor, tela com a lista, botões aceitar e recusar, mudança da situação da reserva
- Demonstração: entrar como agricultor, ver a reserva pendente e aceitá-la; entrar como cliente e ver a reserva como "aceita"; recusar outra e ver "recusada"
- Dependências: Etapa 14

### Etapa 16 – Entrega em casa
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: levar o pedido até quem não pode buscar
- Entregáveis: situação de disponível do entregador com botão para mudá-la, opção "entrega em casa" ao gerar o pedido com o endereço, atribuição do pedido a um entregador disponível, página de entregas do entregador com os pedidos recebidos
- Demonstração: deixar um entregador como disponível, gerar um pedido com entrega em casa e vê-lo na página de entregas dele; deixar o entregador como indisponível e ver a mensagem de que não há entregador no momento
- Dependências: Etapas 4 e 12

### Etapa 17 – Atualizar a situação da entrega
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: informar quando o pedido chegou
- Entregáveis: situações do pedido (em preparação, a caminho e entregue), rota e botão do entregador para atualizar a situação, exibição da situação nos detalhes do pedido do cliente
- Demonstração: como entregador, marcar o pedido como a caminho e depois como entregue; como cliente, abrir os detalhes do pedido e ver a situação mudar
- Dependências: Etapas 13 e 16

### Etapa 18 – Seguir agricultores
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: acompanhar os agricultores de que o cliente mais gosta
- Entregáveis: tabela de seguidores (cliente e agricultor), botões seguir e deixar de seguir na página do agricultor, lista dos agricultores seguidos
- Demonstração: seguir dois agricultores e ver os dois na lista; deixar de seguir um e ver só o outro
- Dependências: Etapa 8

### Etapa 19 – Central de notificações
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: avisar os seguidores das novidades
- Entregáveis: tabela de notificações (usuário, texto, data e situação de lida), criação de uma notificação para cada seguidor quando o agricultor publica uma inserção, rota de listagem, tela de central de notificações, contador de não lidas no menu
- Demonstração: seguir um agricultor, deixá-lo publicar uma inserção nova e ver a notificação na central do cliente, com o contador em 1; marcar como lida e ver o contador em 0
- Dependências: Etapas 5 e 18

### Etapa 20 – Comentário ao agricultor
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: deixar o cliente dar sua opinião depois da compra
- Entregáveis: tabela de comentários (cliente, agricultor, texto e data), rota de envio permitida só a quem comprou uma caixa do agricultor, formulário de comentário e lista de comentários na página do agricultor
- Demonstração: com um pedido pago, comentar na página do agricultor e ver o comentário na lista; tentar comentar na página de um agricultor de quem nunca comprou e ver a recusa
- Dependências: Etapas 8 e 12

### Etapa 21 – Selos do agricultor
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: mostrar as conquistas do agricultor
- Entregáveis: tabela de selos (nome e regra, como "primeira venda" e "dez vendas"), concessão automática ao cumprir a regra, seção de selos na página do agricultor
- Demonstração: concluir a primeira venda de um agricultor e ver o selo "primeira venda" na página dele; abrir a página de outro agricultor sem vendas e ver a seção vazia
- Dependências: Etapas 8 e 12

### Etapa 22 – Testes, documentação e entrega final
Contexto: E-Farmers – Feira Virtual de Produtores Locais | Tipo: App web de marketplace com papéis
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes do cadastro e do login, do carrinho, do pedido e do pagamento, da reserva, da entrega, das notificações e das permissões (cliente não edita inserção de agricultor), código comentado, README com instruções de execução, versão final publicada
- Demonstração: executar o roteiro completo, da publicação da inserção à entrega do pedido ao cliente, seguindo apenas o README
- Dependências: todas as anteriores
