# Projeto: ChronoPic – Gestão de Fotos com Detecção de Idade
Tipo: App web com processamento em segundo plano
Descrição: Plataforma para guardar fotos pessoais. O usuário envia uma imagem; o sistema detecta o rosto, estima a idade da pessoa em segundo plano, sem travar o envio, e marca a foto com o resultado. O usuário consulta, filtra e apaga suas fotos. O acesso exige conta verificada.
Login na Etapa 1: sim — o escopo exige conta de usuário e cada pessoa só vê as próprias fotos.

## Etapas

### Etapa 1 – Esqueleto: cadastro e login de ponta a ponta
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: ter o ambiente e a primeira funcionalidade completa atravessando todas as camadas
- Entregáveis: repositório com branches, backend, banco de dados, tabela de usuários (e-mail e senha protegida), rotas de cadastro e de login, telas de cadastro e de login, página inicial simples
- Demonstração: cadastrar um usuário, entrar com ele e ver a página inicial; tentar cadastrar o mesmo e-mail de novo e ver a recusa
- Dependências: nenhuma

### Etapa 2 – Verificação da conta por código
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: garantir que o e-mail pertence a quem se cadastrou
- Entregáveis: situação da conta (pendente ou ativa), geração de código de uso único com validade curta, envio do código por e-mail, rota e tela de confirmação do código, bloqueio do login enquanto a conta estiver pendente
- Demonstração: cadastrar um usuário, tentar entrar e ver o bloqueio; informar o código recebido e ver a conta ativa e o login liberado; informar um código errado ou vencido e ver a recusa
- Dependências: Etapa 1

### Etapa 3 – Manter o usuário conectado
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: evitar que o usuário digite a senha toda vez
- Entregáveis: opção "continuar conectado" no login, sessão de longa duração, renovação automática enquanto o usuário usa o sistema, botão de sair que encerra a sessão
- Demonstração: entrar marcando a opção, fechar o navegador, abrir de novo e continuar conectado; sair e ver que a página inicial volta a pedir login
- Dependências: Etapa 2

### Etapa 4 – Recuperação de senha
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: devolver o acesso a quem esqueceu a senha
- Entregáveis: link "esqueci a senha" na tela de login, rota que envia um link de redefinição por e-mail com validade curta, tela de nova senha, rota de redefinição
- Demonstração: pedir a redefinição, abrir o link recebido, definir uma nova senha e entrar com ela; tentar entrar com a senha antiga e ver a recusa; usar o mesmo link duas vezes e ver a recusa
- Dependências: Etapa 2

### Etapa 5 – Enviar uma foto com informações opcionais
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: guardar a primeira foto do usuário
- Entregáveis: tabela de fotos (dono, arquivo, data e etiqueta opcional), armazenamento do arquivo, rota de envio, formulário com escolha do arquivo e campo de etiqueta, validação do tipo e do tamanho do arquivo
- Demonstração: entrar, enviar uma foto com a etiqueta "férias" e ver a confirmação do envio; tentar enviar um arquivo que não é imagem e ver o erro
- Dependências: Etapa 3

### Etapa 6 – Listar as minhas fotos
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: ver tudo o que o usuário já enviou
- Entregáveis: rota de listagem das fotos do usuário com suas etiquetas, tela de galeria com miniaturas e etiquetas
- Demonstração: enviar três fotos e ver as três na galeria; entrar com outro usuário e ver que as fotos do primeiro não aparecem
- Dependências: Etapa 5

### Etapa 7 – Abrir uma foto
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: exibir a imagem completa de uma foto
- Entregáveis: rota que devolve o arquivo da foto pelo identificador, tela de detalhe da foto, link da galeria para a tela de detalhe, recusa para fotos de outro usuário
- Demonstração: clicar numa miniatura da galeria e ver a imagem em tamanho completo; tentar abrir o endereço da foto de outro usuário e ver a recusa
- Dependências: Etapa 6

### Etapa 8 – Filtrar fotos por e-mail e etiqueta
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: achar rapidamente um grupo de fotos
- Entregáveis: parâmetros de filtro por e-mail e por etiqueta na rota de listagem, campos de filtro na galeria, botão para limpar os filtros, mensagem de "nenhuma foto encontrada"
- Demonstração: filtrar pela etiqueta "férias" e ver só as fotos marcadas; combinar com o e-mail e ver o resultado diminuir; limpar os filtros e ver todas de novo
- Dependências: Etapa 6

### Etapa 9 – Detecção de rosto e recorte automático
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: preparar a imagem para a estimativa de idade
- Entregáveis: serviço de visão computacional que localiza o rosto na foto enviada, recorte da região do rosto, guardar o recorte junto da foto, marca de "sem rosto detectado" quando não houver rosto
- Demonstração: enviar uma foto com um rosto e ver o recorte gerado; enviar uma paisagem e ver a marca de "sem rosto detectado"
- Dependências: Etapa 5

### Etapa 10 – Estimar a idade em segundo plano
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: obter a idade sem fazer o usuário esperar
- Entregáveis: fila de trabalhos de estimativa, processamento em segundo plano a cada foto com rosto, situação da foto (processando, concluída ou com falha), tabela de resultados (foto e idade estimada), etiqueta automática com a faixa de idade, indicação da situação na galeria
- Demonstração: enviar uma foto e ver a resposta imediata de envio com a situação "processando"; recarregar a galeria depois de alguns segundos e ver a idade estimada e a etiqueta automática; enviar uma foto sem rosto e ver que ela não entra na fila
- Dependências: Etapa 9

### Etapa 11 – Consultar a idade de uma foto
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: ver o resultado de uma foto específica
- Entregáveis: rota que devolve a idade estimada de uma foto, indicação do resultado na tela de detalhe da foto, mensagem "ainda processando" quando o resultado não estiver pronto
- Demonstração: abrir o detalhe de uma foto concluída e ver a idade estimada; abrir o de uma foto ainda em processamento e ver a mensagem de espera
- Dependências: Etapas 7 e 10

### Etapa 12 – Consultar as idades de várias fotos de uma vez
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: evitar uma chamada por foto ao montar a galeria
- Entregáveis: rota que recebe uma lista de identificadores e devolve as idades de todas em uma única resposta, uso dessa rota para preencher a galeria, tratamento de identificadores inexistentes ou de outro usuário
- Demonstração: abrir a galeria com dez fotos e ver as idades aparecerem de uma só vez; pedir um identificador inexistente na lista e ver que ele é ignorado sem derrubar o resto
- Dependências: Etapa 11

### Etapa 13 – Excluir fotos e seus resultados
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: deixar o usuário apagar o que não quer mais guardar
- Entregáveis: rota que apaga uma ou várias fotos, remoção do arquivo, do recorte e do resultado de idade de cada foto, seleção múltipla na galeria, botão de excluir com confirmação em janela
- Demonstração: selecionar duas fotos na galeria, excluir confirmando na janela e ver que sumiram; conferir que a idade das duas também foi apagada
- Dependências: Etapas 8 e 10

### Etapa 14 – Testes, documentação e entrega final
Contexto: ChronoPic – Gestão de Fotos com Detecção de Idade | Tipo: App web com processamento em segundo plano
- Objetivo: validar o sistema e deixá-lo pronto para uso
- Entregáveis: testes do cadastro e da verificação, do envio de foto, da fila de estimativa, das permissões (usuário não vê fotos de outro) e da exclusão, código comentado, README com instruções de execução, versão final publicada
- Demonstração: executar o roteiro completo, do cadastro à exclusão de uma foto, seguindo apenas o README
- Dependências: todas as anteriores
