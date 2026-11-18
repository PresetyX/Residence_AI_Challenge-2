# Projeto: CDC Shop – Loja Virtual de Materiais de Construção
Tipo: App web CRUD
Descrição: Loja virtual de ferragens e materiais de construção. O cliente se cadastra, consulta o catálogo, monta um carrinho, paga e acompanha o pedido; o lojista, em uma área própria, mantém os produtos e os preços.
Login na Etapa 1: sim — o escopo exige conta de cliente e uma área separada para o lojista.

## Etapas

### Etapa 1 – Esqueleto: cadastro e login do cliente de ponta a ponta
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend, banco de dados, tabela de clientes (nome, e-mail e senha protegida), rotas de cadastro e de login, telas de cadastro e de login, página inicial simples
- Demonstração: cadastrar um cliente, entrar com ele e ver a página inicial; tentar cadastrar o mesmo e-mail de novo e ver a recusa
- Dependências: nenhuma

### Etapa 2 – Perfil do cliente e saída da conta
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: consultar os dados da conta e sair com segurança
- Entregáveis: rota de leitura do perfil, tela de perfil com os dados da conta, botão de sair que encerra a sessão
- Demonstração: entrar, abrir o perfil e ver nome e e-mail; clicar em sair e ver que o perfil volta a pedir login
- Dependências: Etapa 1

### Etapa 3 – Acesso do lojista
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: dar ao lojista uma área própria, separada dos clientes
- Entregáveis: contas de lojista criadas por carga inicial, tela de login do lojista, página inicial do lojista, perfil do lojista, botão de sair
- Demonstração: entrar na página do lojista com uma conta de lojista, abrir o perfil e sair; tentar entrar nessa página com uma conta de cliente e ver a recusa
- Dependências: Etapa 1

### Etapa 4 – Lojista cadastra e lista produtos
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: começar a montar o catálogo da loja
- Entregáveis: tabela de produtos (nome, descrição e preço), rota de cadastro de produto, formulário de novo produto, rota e tela de listagem dos produtos na área do lojista
- Demonstração: entrar como lojista, cadastrar um martelo a R$ 35,00 e uma chave de fenda a R$ 12,50 e ver os dois na lista
- Dependências: Etapa 3

### Etapa 5 – Detalhes do produto e alteração de preço
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: consultar um produto e corrigir seu preço
- Entregáveis: rota de detalhe do produto, tela de detalhes, rota e formulário de alteração de preço, validação de preço positivo
- Demonstração: abrir os detalhes do martelo, mudar o preço de R$ 35,00 para R$ 39,90 e ver o novo valor nos detalhes e na lista; tentar um preço negativo e ver a mensagem de erro
- Dependências: Etapa 4

### Etapa 6 – Lojista remove produtos
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: tirar do catálogo o que a loja não vende mais
- Entregáveis: rota de remoção de produto, botão de remover na lista com confirmação em janela
- Demonstração: remover a chave de fenda confirmando na janela e ver que ela sumiu da lista
- Dependências: Etapa 4

### Etapa 7 – Catálogo para o cliente: lista e detalhes
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: deixar o cliente ver o que a loja vende
- Entregáveis: tela de lista de produtos para o cliente, tela de detalhes do produto com nome, descrição e preço, link da lista para os detalhes
- Demonstração: entrar como cliente, ver a lista de produtos cadastrados, abrir os detalhes do martelo e ver nome, descrição e preço atualizado
- Dependências: Etapas 2 e 4

### Etapa 8 – Ordenar produtos por preço
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: comparar os produtos pelo preço
- Entregáveis: parâmetro de ordenação por preço crescente ou decrescente na rota de listagem, controle de ordenação nas listas do cliente e do lojista
- Demonstração: ordenar a lista por preço crescente e ver o mais barato primeiro, depois por decrescente e ver a ordem inversa; repetir como lojista
- Dependências: Etapas 4 e 7

### Etapa 9 – Buscar produto pelo nome
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: encontrar um produto sem percorrer a lista inteira
- Entregáveis: barra de busca nas listas do cliente e do lojista, parâmetro de busca por parte do nome na rota de listagem, mensagem para busca sem resultado
- Demonstração: digitar "mart" na busca e ver só o martelo; buscar um nome que não existe e ver a mensagem de nenhum resultado
- Dependências: Etapas 4 e 7

### Etapa 10 – Adicionar ao carrinho e ver o carrinho
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: reunir os produtos que o cliente pretende comprar
- Entregáveis: tabela de itens do carrinho de cada cliente, rota para adicionar produto, botão de adicionar nos detalhes do produto, rota e tela do carrinho com itens, quantidades e total
- Demonstração: entrar como cliente, adicionar dois produtos ao carrinho e abrir o carrinho vendo os itens, as quantidades e o total
- Dependências: Etapas 2 e 7

### Etapa 11 – Esvaziar o carrinho
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: recomeçar a compra do zero
- Entregáveis: rota que remove todos os itens do carrinho do cliente, botão de esvaziar com confirmação, carrinho vazio com total zero
- Demonstração: com itens no carrinho, clicar em esvaziar, confirmar e ver o carrinho vazio com total zero
- Dependências: Etapa 10

### Etapa 12 – Pagar o carrinho e gerar o pedido
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: concluir a compra
- Entregáveis: tabelas de pedidos e de itens do pedido, rota de pagamento que cria o pedido com os itens e o valor total e esvazia o carrinho em uma única operação, tela de pagamento, tela de confirmação com o número do pedido
- Demonstração: montar um carrinho com dois produtos, pagar e ver a confirmação com o número do pedido e o carrinho vazio
- Dependências: Etapa 10

### Etapa 13 – Acompanhar o pedido e o pacote
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: saber o que foi comprado e em que situação está o envio
- Entregáveis: situação do envio registrada no pedido (inicialmente "em preparação"), rota de pedidos do cliente, tela com a lista de pedidos, tela de detalhes do pedido
- Demonstração: abrir a lista de pedidos, escolher o pedido recém-pago e ver os itens, o valor, a data e a situação do envio
- Dependências: Etapa 12

### Etapa 14 – Página Sobre nós
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: apresentar a loja a clientes e lojistas
- Entregáveis: página de conteúdo estático, link na barra de navegação da área do cliente e da área do lojista
- Demonstração: abrir a página Sobre nós como cliente e como lojista e ver o mesmo conteúdo
- Dependências: Etapas 2 e 3

### Etapa 15 – Contato com a loja
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: tirar dúvidas com a loja
- Entregáveis: tabela de mensagens, formulário de contato (assunto e mensagem), rota de envio, mensagem de confirmação
- Demonstração: entrar como cliente, preencher e enviar uma dúvida e ver a confirmação de envio; tentar enviar com a mensagem vazia e ver o erro
- Dependências: Etapa 2

### Etapa 16 – Testes, documentação e entrega final
Contexto: CDC Shop – Loja Virtual de Materiais de Construção | Tipo: App web CRUD
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes do cadastro e do login, do carrinho (adicionar e esvaziar), do pagamento (pedido criado e carrinho esvaziado em uma única operação) e das permissões (cliente não acessa a área do lojista), código comentado, README com instruções de execução, versão final publicada
- Demonstração: executar o roteiro completo de uso em um ambiente limpo, do cadastro do cliente ao acompanhamento do pedido, seguindo apenas o README
- Dependências: todas as anteriores
