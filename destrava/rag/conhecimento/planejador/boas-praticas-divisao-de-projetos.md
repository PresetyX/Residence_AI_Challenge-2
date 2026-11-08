# Boas práticas para dividir um projeto de software em etapas

## Objetivo deste documento
Orientar a divisão de um projeto de software em etapas pequenas, ordenadas e testáveis. A regra central é dividir em **fatias verticais**: partes que atravessam todas as camadas do sistema e entregam algo que funciona. Os exemplos vêm de cinco projetos já estruturados na base: Sistema de Gerenciamento de Demandas (SGD), Votação Digital, Monitoramento de Sustentabilidade Pessoal, NotaDez e MesclaInvest.

## Princípio central: dividir por valor entregue, não por camada técnica
Uma etapa boa responde "o que o usuário consegue fazer ao final dela?". Uma etapa ruim responde "qual camada técnica foi construída?".

Exemplo (NotaDez):

| Divisão por camada (evitar) | Divisão por fatia vertical (preferir) |
|---|---|
| Criar todas as tabelas | Docente cria conta e entra no sistema |
| Criar todas as rotas da API | Docente cadastra disciplinas e turmas |
| Criar todas as telas | Docente cadastra alunos um a um |
| Ligar tudo | Docente importa alunos por CSV |

Na divisão por camada, nada funciona até a última etapa, e os problemas de integração aparecem todos juntos. Na divisão vertical, cada etapa termina com algo demonstrável, e os problemas aparecem cedo e isolados.

## O que é uma fatia vertical
É uma parte do projeto que inclui o trabalho necessário em cada camada (interface, regras de negócio e dados) para uma funcionalidade ficar utilizável. Exemplo (SGD): "Cancelar demanda" envolve o botão na tela, a rota que muda o status para cancelada e a garantia de que o registro continua no banco.

## Checklist de uma boa etapa
1. Dá para demonstrar funcionando, de ponta a ponta?
2. Existe um teste claro de "funcionou" ou "não funcionou"?
3. Depende de poucas etapas anteriores e não exige que outra etapa futura termine primeiro?
4. É pequena o bastante para ser concluída sem se perder?
5. Entrega algo de valor para quem usa o sistema, mesmo que simples?

Quando uma etapa falha em algum ponto, deve ser dividida de novo ou reescrita.

## Passo a passo para dividir um projeto
1. **Ler o escopo inteiro** e listar tudo o que o sistema deve fazer, sem esquecer requisitos de segurança, validação e registro de eventos (nada do escopo pode ficar de fora de todas as etapas).
2. **Separar o que está dentro e o que está fora do escopo.** Itens fora do escopo não geram etapas (exemplo: MesclaInvest não tem pagamentos reais nem blockchain).
3. **Agrupar os requisitos por funcionalidade**, usando o ponto de vista de quem usa o sistema.
4. **Escolher a menor funcionalidade completa** para ser a primeira etapa (esqueleto).
5. **Quebrar as funcionalidades grandes** com os padrões da próxima seção.
6. **Ordenar pelas dependências reais e pelo valor**: o que sustenta outras etapas vem antes.
7. **Escrever, para cada etapa, objetivo, entregáveis por camada, uma demonstração e dependências.**
8. **Conferir a cobertura:** todo requisito do escopo aparece em pelo menos uma etapa, e nenhuma etapa trata de algo fora do escopo.
9. **Fechar com testes, documentação e entrega.**

## A primeira etapa: o esqueleto
A Etapa 1 deve ser a funcionalidade mais fina possível, atravessando todas as camadas. Ela já obriga o ambiente, o banco e a interface a existirem, sem construir tudo antes.

Exemplos:
- NotaDez e MesclaInvest: criar conta e entrar no sistema.
- SGD: login de um usuário pré-cadastrado, com página inicial por perfil.
- Votação Digital: cadastrar e listar candidatos, com conexão ao banco e menu.
- Sustentabilidade Pessoal: informar o consumo de água de um dia e ver a classificação.

O esqueleto não precisa ser bonito nem completo. Precisa funcionar de ponta a ponta.

## Padrões de divisão

### Padrão 1 – Por operação
Quando a funcionalidade é "gerenciar" algo, separe em cadastrar, listar, ver detalhes, editar e remover (ou cancelar).
Exemplo (SGD): "Cadastrar e listar demandas", "Ver detalhes e editar demanda" e "Cancelar demanda" são três etapas.

### Padrão 2 – Por passo do fluxo
Quando existe um processo com começo, meio e fim, cada passo vira uma etapa.
Exemplo (Votação Digital): abrir a votação, registrar um voto e encerrar a votação, cada passo funcionando sozinho.

### Padrão 3 – Por regra de negócio
Primeiro o comportamento básico, depois as restrições e exceções.
Exemplo (SGD): o fluxo básico de status vem antes das permissões por perfil (como o membro só poder mover até "em revisão").
Exemplo (Votação Digital): registrar um voto vem antes das regras de voto duplo e voto nulo.

### Padrão 4 – Do simples ao complexo
Comece pela versão mais simples da regra e evolua.
Exemplo (NotaDez): nota final por média simples, depois ponderada, e só então fórmula livre digitada pelo professor.
Exemplo (Sustentabilidade): classificar a água, depois energia e resíduos, depois o transporte com ponderação, por fim o resultado geral.

### Padrão 5 – Por variação de dados ou de entrada
Cada forma de entrar com os dados pode ser uma etapa.
Exemplo (NotaDez): alunos cadastrados um a um e, depois, importação por CSV.
Exemplo (MesclaInvest): lista de startups, depois filtro por estágio, depois página de detalhe completa.

### Padrão 6 – Por perfil de usuário
Primeiro funciona para o perfil mais amplo, depois entram as restrições dos demais.
Exemplo (SGD): ações liberadas para o administrador, depois as regras do líder e do membro.

### Padrão 7 – Pelos dois lados de uma negociação ou troca
Quando duas partes interagem, comece por um lado e complete com o outro.
Exemplo (MesclaInvest): oferta de venda, depois compra de uma oferta existente, depois oferta de compra com cancelamento.

### Padrão 8 – Primeiro o resultado, depois o refinamento
Faça funcionar com o necessário e melhore depois (validações extras, aparência, desempenho).
Exemplo (MesclaInvest): variação de valor dos tokens em um único período, depois nos demais períodos.

## Quando a fatia vertical não se encaixa
- **Esqueleto e ambiente:** a preparação inicial (repositório, ambiente, conexão com o banco) é inevitável, mas deve ser mínima e já embutida na primeira funcionalidade.
- **Mudanças que alteram telas já existentes:** criptografia e auditoria costumam ser aplicadas sobre funcionalidades prontas. Nesse caso, a etapa deve mostrar o efeito de ponta a ponta (exemplo, Votação Digital: cadastrar um eleitor e ver no banco os dados cifrados, com a busca ainda funcionando).
- **Testes, documentação e entrega:** ficam em uma etapa final, mas testes das regras críticas devem acompanhar cada etapa durante o desenvolvimento.

## Erros comuns (anti-padrões)
- **Etapa só de banco de dados** ("criar todas as tabelas"): modele o necessário para a funcionalidade da etapa e evolua o modelo aos poucos.
- **Etapa só de interface** ("fazer todas as telas"): cada tela nasce com a funcionalidade que ela usa.
- **Etapa "ligar tudo"** no final: a integração acontece em cada etapa.
- **Etapa grande demais**, como "implementar o módulo de votação": divida por fluxo e por regra.
- **Etapa sem demonstração clara**, como "melhorar o sistema": sempre diga como verificar que funcionou.
- **Dependências escondidas**, como uma etapa que só funciona depois de outra não listada: declare as dependências.
- **Requisito esquecido**: um requisito de segurança, auditoria ou validação sem etapa correspondente.
- **Etapa para algo fora do escopo**.

## Como cuidar das dependências
- Liste, em cada etapa, de quais etapas anteriores ela depende.
- Prefira poucas dependências, e que apontem para etapas simples e centrais (login, cadastro básico).
- Quando duas etapas não dependem uma da outra, elas podem andar em paralelo.
- Evite ciclos: se a etapa A precisa da B e a B precisa da A, junte-as ou redivida.

## Formato recomendado para cada etapa
```
### Etapa N – <título curto, com o resultado para o usuário>
- Objetivo: <o que o usuário ou o sistema passa a poder fazer>
- Entregáveis: <o que é feito em cada camada: interface, regras, dados>
- Demonstração: <um teste simples que mostra a etapa funcionando>
- Dependências: <etapas anteriores necessárias, ou "nenhuma">
```

Nota: a estimativa de tempo de cada etapa não faz parte da divisão e é calculada em outra parte do sistema.

## Exemplo completo de raciocínio (NotaDez, resumido)
Escopo: o professor cadastra instituições, disciplinas, turmas e alunos, lança notas, vê a nota final calculada e exporta.

1. Esqueleto: criar conta e entrar.
2. Instituição e curso no primeiro acesso.
3. Disciplinas e turmas.
4. Alunos, um a um.
5. Importação de alunos por CSV.
6. Componentes de nota.
7. Lançar notas por componente.
8. Auditoria das alterações.
9. Nota final (média).
10. Exportação em CSV.
11. Testes, documentação e entrega.

Observe que cada etapa muda o que o professor consegue fazer, que a importação por CSV vem depois do cadastro manual (do simples ao variado) e que a auditoria vem logo depois do lançamento de notas, porque depende dele.

## Princípios de qualidade herdados da decomposição de escopo (WBS)
- Todo o trabalho do escopo deve estar coberto pelas etapas, e nada além disso.
- As etapas não devem se sobrepor: um mesmo trabalho não aparece em duas etapas.
- O nível de detalhe deve ser parecido entre etapas do mesmo plano.
- A decomposição é revista quando o escopo muda.

## Referências para aprofundamento
- Mike Cohn, *User Stories Applied* (critérios INVEST: independente, negociável, valiosa, estimável, pequena e testável).
- Jeff Patton, *User Story Mapping* (fatias verticais no planejamento de entregas).
- Richard Lawrence, padrões de divisão de histórias (Humanizing Work).
- Project Management Institute, *Practice Standard for Work Breakdown Structures* (decomposição de escopo).
