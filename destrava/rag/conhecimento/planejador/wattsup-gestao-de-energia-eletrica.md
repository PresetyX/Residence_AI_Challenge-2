# Projeto: WattsUp – Gestão de Energia Elétrica
Tipo: App web com perfis e monitoramento
Descrição: Sistema de gestão de energia para a rede elétrica, do lado do usuário e do lado da central. O usuário registra seus dispositivos, acompanha consumo e produção, recebe faturas, compara fornecedores e paga contas. O gerente de um nó central acompanha o uso dos usuários de sua área e o nível dos armazenamentos. O produtor de energia renovável vende o excedente.
Login na Etapa 1: sim — o escopo exige conta de usuário e um perfil separado para o gerente do nó central.

## Etapas

### Etapa 1 – Esqueleto: cadastro e login do usuário de ponta a ponta
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend, banco de dados, tabela de usuários (nome, dados pessoais, nome de usuário e senha protegida), rotas de cadastro e de login, telas de cadastro e de login, página inicial simples
- Demonstração: cadastrar um usuário, entrar com ele e ver a página inicial; tentar cadastrar o mesmo nome de usuário de novo e ver a recusa
- Dependências: nenhuma

### Etapa 2 – Página inicial com menu e dados pessoais
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: dar acesso rápido às áreas do site e permitir a troca de senha
- Entregáveis: página inicial com menu que leva às áreas do sistema, rota de leitura dos dados pessoais, tela de dados pessoais, rota e formulário de alteração de senha, botão de sair
- Demonstração: entrar, usar o menu para abrir os dados pessoais, trocar a senha, sair e entrar com a nova; tentar entrar com a antiga e ver a recusa
- Dependências: Etapa 1

### Etapa 3 – Gerente registra o nó central
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: criar a estrutura que cobre uma área da rede
- Entregáveis: contas de gerente criadas por carga inicial, login do gerente com página própria, tabela de nós centrais (nome, área e gerente), rota e formulário de registro de nó, lista dos nós do gerente
- Demonstração: entrar como gerente, registrar o nó "Zona Norte" e vê-lo na lista; tentar abrir a página do gerente com uma conta de usuário comum e ver a recusa
- Dependências: Etapa 1

### Etapa 4 – Ligar fornecedores e usuários ao nó
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: dizer quem pertence a cada nó
- Entregáveis: tabela de fornecedores (nome, tarifa por kWh e fonte renovável ou tradicional), rota e formulário de cadastro de fornecedor, vínculo de fornecedores e de usuários ao nó, lista dos fornecedores e dos usuários do nó na página do gerente
- Demonstração: cadastrar dois fornecedores e ligar um usuário ao nó "Zona Norte" e ver, na página do gerente, os dois fornecedores e o usuário na lista do nó
- Dependências: Etapa 3

### Etapa 5 – Registrar dispositivos
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: dizer o que o usuário quer monitorar
- Entregáveis: tabela de dispositivos (usuário, nome, tipo de consumo ou de produção e potência), rotas de cadastro, de listagem e de remoção, tela de dispositivos com formulário
- Demonstração: cadastrar um ar-condicionado como consumo e um painel solar como produção e ver os dois na lista; remover um e ver que sumiu
- Dependências: Etapa 2

### Etapa 6 – Registrar o consumo e a produção
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: ter os dados de energia que serão acompanhados
- Entregáveis: tabela de leituras (dispositivo, data e hora e quantidade em kWh), rota que recebe leituras, carga de leituras de exemplo por dispositivo
- Demonstração: carregar leituras de uma semana para o ar-condicionado e para o painel solar e conferir que elas aparecem registradas na rota de leituras de cada dispositivo
- Dependências: Etapa 5

### Etapa 7 – Painel de consumo e produção
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: deixar o usuário acompanhar seu uso de energia
- Entregáveis: rota que soma o consumo e a produção por dia e por dispositivo, tela de painel com gráficos de consumo e de produção, seletor de período
- Demonstração: abrir o painel e ver o consumo e a produção da última semana, por dia; mudar o período e ver os gráficos se ajustarem
- Dependências: Etapa 6

### Etapa 8 – Notificações do usuário
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: avisar o usuário das mudanças que acontecem
- Entregáveis: tabela de notificações (usuário, texto, data e situação de lida), rota de listagem, tela de notificações com marcar como lida, contador de não lidas no menu, rota interna para o sistema criar notificações
- Demonstração: criar duas notificações pela rota interna, ver as duas na página e o contador em 2; marcar uma como lida e ver o contador em 1
- Dependências: Etapa 2

### Etapa 9 – Dicas de economia personalizadas
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: ajudar o usuário a gastar menos e poluir menos
- Entregáveis: regras que analisam as leituras (por exemplo, consumo noturno alto ou dispositivo com pico de uso), rota de dicas do usuário, seção de dicas no painel
- Demonstração: com o ar-condicionado ligado a noite toda nas leituras, abrir o painel e ver a dica sobre consumo noturno; com leituras baixas, ver a mensagem de que não há dicas no momento
- Dependências: Etapa 7

### Etapa 10 – Gerente acompanha o uso do nó
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: deixar o gerente ver o consumo de todos os usuários de sua área
- Entregáveis: rota que soma o consumo e a produção dos usuários do nó, tela do gerente com a lista de usuários e o uso atual de cada um, total do nó, atualização automática da tela
- Demonstração: entrar como gerente, abrir o nó "Zona Norte" e ver o consumo de cada usuário e o total; carregar novas leituras e ver os números atualizarem sozinhos
- Dependências: Etapas 4 e 6

### Etapa 11 – Armazenamento de energia do usuário
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: mostrar quanta energia o usuário tem guardada
- Entregáveis: tabela de armazenamentos (usuário, capacidade e nível atual em kWh), nível atualizado a partir das leituras de produção e de consumo, tela com o nível guardado em barra de progresso
- Demonstração: abrir a tela de armazenamento, ver o nível atual de uma bateria de 10 kWh e ver o nível subir depois de carregar leituras de produção
- Dependências: Etapa 6

### Etapa 12 – Gerente vê o nível dos armazenamentos
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: garantir energia disponível nos horários de pico
- Entregáveis: rota com os níveis de armazenamento dos usuários do nó, tela do gerente com o nível de cada armazenamento e o total, alerta quando o total ficar abaixo de um limite
- Demonstração: entrar como gerente, ver os níveis de cada usuário e o total do nó; esvaziar um armazenamento e ver o alerta de nível baixo
- Dependências: Etapas 4 e 11

### Etapa 13 – Comparar fornecedores do nó
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: ajudar o usuário a escolher o fornecedor mais vantajoso
- Entregáveis: rota que lista os fornecedores do nó do usuário, tela de comparação lado a lado (tarifa, fonte renovável ou tradicional e custo estimado com base no consumo do usuário), ordenação por custo
- Demonstração: abrir a comparação, ver os dois fornecedores do nó com a tarifa e o custo estimado do mês, e ordenar pelo mais barato
- Dependências: Etapas 4 e 7

### Etapa 14 – Contrato com um fornecedor
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: ligar o usuário ao fornecedor escolhido e à fonte de energia desejada
- Entregáveis: tabela de contratos (usuário, fornecedor, fonte renovável ou tradicional e data de início), rota e formulário para criar ou trocar o contrato, tela com o contrato atual
- Demonstração: escolher o fornecedor de fonte renovável e criar o contrato; trocar depois por outro fornecedor e ver o contrato atualizado com a nova fonte
- Dependências: Etapa 13

### Etapa 15 – Faturas geradas pelo nó central
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: cobrar o usuário pelo consumo do período
- Entregáveis: tabela de faturas (usuário, período, consumo, tarifa do fornecedor, valor e situação de paga ou em aberto), rotina que gera a fatura do período, notificação ao usuário quando uma fatura nova é criada, tela com a fatura em aberto
- Demonstração: gerar a fatura do mês para um usuário com contrato, ver a fatura com o consumo, a tarifa e o valor, e ver a notificação de nova fatura
- Dependências: Etapas 6, 8 e 14

### Etapa 16 – Histórico de faturas
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: deixar o usuário consultar o que já pagou e se organizar
- Entregáveis: rota de listagem das faturas do usuário, tela de histórico com período, valor e situação, total gasto no ano
- Demonstração: com faturas de três meses, abrir o histórico e ver as três com valor e situação, mais o total gasto
- Dependências: Etapa 15

### Etapa 17 – Forma de pagamento e pagamento de fatura
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: permitir que o usuário pague suas contas pelo sistema
- Entregáveis: tabela de formas de pagamento (usuário e dados do cartão sem guardar o número completo), rotas e formulário para inserir e trocar a forma de pagamento, integração com o serviço de pagamento externo, rota de pagamento da fatura, mudança da situação da fatura para paga
- Demonstração: cadastrar um cartão de teste, pagar a fatura em aberto, ver a situação mudar para paga no histórico; trocar o cartão e pagar outra fatura; usar um cartão recusado e ver a mensagem de erro com a fatura ainda em aberto
- Dependências: Etapas 15 e 16

### Etapa 18 – Comprar energia adicional
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: evitar a falta de energia quando o consumo passar do fornecido
- Entregáveis: tabela de transações de energia (usuário, tipo de compra ou de venda, quantidade, valor e data), rota de compra de kWh adicionais ao nó central, tela de compra com preço calculado, cobrança na forma de pagamento do usuário, confirmação da transação em tempo real
- Demonstração: pedir a compra de 5 kWh adicionais, ver o preço, confirmar e ver a confirmação da transação na hora, com a cobrança registrada
- Dependências: Etapa 17

### Etapa 19 – Produtor vende o excedente
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: deixar quem produz energia renovável ganhar com o que sobra
- Entregáveis: verificação de que o usuário tem dispositivo de produção, rota de venda de excedente ao nó central, limite da venda ao excedente disponível, crédito do valor ao usuário, confirmação da transação em tempo real
- Demonstração: com o painel solar produzindo mais do que o consumo, vender 3 kWh e ver a confirmação e o crédito; tentar vender mais do que o excedente e ver a recusa; tentar vender com um usuário sem dispositivo de produção e ver a recusa
- Dependências: Etapas 11 e 18

### Etapa 20 – Testes, documentação e entrega final
Contexto: WattsUp – Gestão de Energia Elétrica | Tipo: App web com perfis e monitoramento
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes do cadastro e do login, do cálculo da fatura, do pagamento, da compra e da venda de energia e das permissões (usuário comum não abre a área do gerente), código comentado, README com instruções de execução, versão final publicada
- Demonstração: executar o roteiro completo, do cadastro do usuário à venda de excedente e ao pagamento da fatura, seguindo apenas o README
- Dependências: todas as anteriores
