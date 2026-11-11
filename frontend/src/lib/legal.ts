/**
 * Terms of Service and Privacy Policy shown in the pre-auth consent modal.
 * Bump TERMS_VERSION whenever the text changes so new consent is recorded.
 */
export const TERMS_VERSION = "2026-11-10";

/** Placeholder: replace with the team's real contact address before publishing. */
export const CONTACT_EMAIL = "contato@exemplo.com";

export interface LegalSection {
  title: string;
  paragraphs: string[];
}

export const CALENDAR_CONSENT_POINTS: string[] = [
  "Leitura: consultar seus eventos para calcular horários livres e identificar conflitos.",
  "Escrita: criar, ajustar e remover os blocos dos planos que você pedir ao assistente, e os eventos que você mesmo criar, editar ou excluir no painel Agenda.",
  "O acesso é feito pela API oficial do Google Agenda e pode ser revogado a qualquer momento em myaccount.google.com/permissions.",
];

export const TERMS_SECTIONS: LegalSection[] = [
  {
    title: "1. Sobre o serviço",
    paragraphs: [
      "O Destrava é um assistente contra a procrastinação desenvolvido no AI Residence Challenge. Ele transforma metas e projetos em planos de blocos de foco e, por meio de agentes especializados, agenda esses blocos no seu Google Agenda. Compromissos avulsos são criados por você, manualmente.",
      "Ao entrar com sua conta Google, você declara ter lido e aceitado estes Termos de Serviço e a Política de Privacidade abaixo.",
    ],
  },
  {
    title: "2. Conta e autenticação",
    paragraphs: [
      "O acesso é feito exclusivamente pelo login do Google (OAuth 2.0). O Destrava nunca recebe nem armazena a sua senha.",
      "Você é responsável pelas ações realizadas na sua sessão e por manter seu dispositivo e sua conta Google protegidos.",
    ],
  },
  {
    title: "3. Acesso ao Google Agenda",
    paragraphs: [
      "Para funcionar, o aplicativo solicita permissão de leitura e de escrita no seu Google Agenda por meio da API do Google Calendar.",
      "Essa permissão é usada somente para consultar seus horários, agendar, ajustar e desmarcar os blocos dos planos que você pedir e executar as ações manuais que você fizer no painel Agenda. O assistente não altera eventos que não pertencem a um plano criado por ele. O uso das informações recebidas das APIs do Google segue a Política de Dados do Usuário dos Serviços de API do Google, incluindo os requisitos de uso limitado.",
    ],
  },
  {
    title: "4. Dados que tratamos",
    paragraphs: [
      "Dados de perfil do Google: nome, e-mail e foto, para identificar a sua sessão.",
      "Dados da agenda: título, descrição, data, horário e local dos eventos necessários para atender ao seu pedido.",
      "Conteúdo das conversas: as mensagens que você envia ao assistente e as respostas geradas.",
      "Tokens de acesso do Google: mantidos de forma protegida apenas enquanto a integração estiver ativa.",
    ],
  },
  {
    title: "5. Como usamos os dados",
    paragraphs: [
      "Os dados são usados para prestar o serviço, manter a segurança da aplicação e corrigir falhas. Não vendemos seus dados, não os utilizamos para publicidade e não usamos os dados do seu Google Agenda para treinar modelos de IA.",
      "O tratamento segue a Lei Geral de Proteção de Dados (Lei nº 13.709/2018), com base no seu consentimento e na execução do serviço solicitado por você.",
    ],
  },
  {
    title: "6. Modelos de IA: execução local e na nuvem",
    paragraphs: [
      "Você escolhe o modelo que responde às suas mensagens. Com o modelo local (Gemma 2B), o processamento acontece no próprio dispositivo.",
      "Com os modelos em nuvem (Gemma 4 26B A4B e Gemma 4 12B), suas mensagens e os dados de agenda necessários ao pedido são enviados a servidores de inferência para gerar a resposta.",
    ],
  },
  {
    title: "7. Limitações da inteligência artificial",
    paragraphs: [
      "Respostas geradas por IA podem conter erros ou interpretar um pedido de forma diferente da esperada. Confira os blocos de cada plano criado ou replanejado.",
      "A exclusão de eventos é irreversível no Destrava; por isso, toda exclusão manual exige a sua confirmação.",
    ],
  },
  {
    title: "8. Seus direitos",
    paragraphs: [
      "Você pode, a qualquer momento, confirmar a existência de tratamento, acessar, corrigir ou solicitar a exclusão dos seus dados, bem como revogar o consentimento.",
      `Para revogar o acesso à agenda, use as configurações de segurança da sua conta Google. Para as demais solicitações, escreva para ${CONTACT_EMAIL}.`,
    ],
  },
  {
    title: "9. Retenção e segurança",
    paragraphs: [
      "Mantemos os dados apenas pelo tempo necessário para prestar o serviço. Ao revogar o acesso ou encerrar a conta, os tokens e os dados associados são removidos.",
      "Adotamos medidas técnicas razoáveis de proteção, como comunicação criptografada e controle de acesso às credenciais.",
    ],
  },
  {
    title: "10. Disponibilidade e alterações",
    paragraphs: [
      "O Destrava é um projeto em desenvolvimento, oferecido no estado em que se encontra, sem garantia de disponibilidade contínua.",
      "Estes termos podem ser atualizados. Mudanças relevantes exigirão um novo aceite antes do próximo acesso.",
    ],
  },
];
