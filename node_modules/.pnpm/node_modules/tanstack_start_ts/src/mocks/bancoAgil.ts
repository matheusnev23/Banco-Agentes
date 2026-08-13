import type {
  Client,
  Conversation,
  ConversationSummary,
  CreditLimit,
  CreditRequest,
  CreditScore,
  ExchangeRate,
  InterviewQuestion,
  Message,
  ServiceError,
} from "@/types";

export const MOCK_CLIENT: Client = {
  id: "cli_10294",
  name: "Marina Duarte",
  maskedDocument: "***.***.789-**",
  authenticated: true,
};

export const MOCK_CREDIT_LIMIT: CreditLimit = {
  available: 5000,
  total: 8000,
  currency: "BRL",
  updatedAt: new Date().toISOString(),
};

export const MOCK_CREDIT_SCORE: CreditScore = {
  value: 742,
  max: 1000,
  band: "high",
  updatedAt: new Date().toISOString(),
};

export const MOCK_EXCHANGE_RATES: ExchangeRate[] = [
  { base: "USD", quote: "BRL", rate: 5.42, variation: 0.42, updatedAt: new Date().toISOString() },
  { base: "EUR", quote: "BRL", rate: 5.89, variation: -0.18, updatedAt: new Date().toISOString() },
  { base: "GBP", quote: "BRL", rate: 6.94, variation: 0.11, updatedAt: new Date().toISOString() },
  { base: "ARS", quote: "BRL", rate: 0.0061, variation: -0.9, updatedAt: new Date().toISOString() },
];

export const MOCK_INTERVIEW_QUESTIONS: InterviewQuestion[] = [
  { id: "income", label: "Qual é a sua renda mensal?", kind: "currency", placeholder: "0,00" },
  {
    id: "employment",
    label: "Qual é o seu tipo de vínculo?",
    kind: "choice",
    options: ["CLT", "Autônomo", "Empresário", "Servidor público", "Aposentado"],
  },
  { id: "expenses", label: "Quanto somam suas despesas fixas?", kind: "currency", placeholder: "0,00" },
  { id: "dependents", label: "Quantos dependentes você possui?", kind: "number", placeholder: "0" },
  {
    id: "debts",
    label: "Você possui dívidas em aberto?",
    kind: "choice",
    options: ["Não possuo", "Sim, em negociação", "Sim, em atraso"],
  },
];

export const MOCK_APPROVED_REQUEST: CreditRequest = {
  id: "req_88213",
  requestedLimit: 12000,
  currency: "BRL",
  status: "approved",
  message: "Seu novo limite já está disponível para uso.",
  createdAt: new Date().toISOString(),
};

export const MOCK_REJECTED_REQUEST: CreditRequest = {
  id: "req_88214",
  requestedLimit: 25000,
  currency: "BRL",
  status: "rejected",
  message: "Não foi possível aprovar o aumento neste momento.",
  createdAt: new Date().toISOString(),
};

export const MOCK_SERVICE_ERROR: ServiceError = {
  title: "Não foi possível concluir sua solicitação.",
  description: "Estamos enfrentando uma instabilidade temporária. Tente novamente em alguns instantes.",
  retryable: true,
};

export const WELCOME_MESSAGE: Message = {
  id: "msg_welcome",
  role: "assistant",
  content: "Olá! Sou o assistente do Banco Ágil. Como posso ajudar você hoje?",
  createdAt: new Date().toISOString(),
};

export const MOCK_CONVERSATION_HISTORY: ConversationSummary[] = [
  {
    id: "conv_1",
    title: "Consulta de limite",
    preview: "Limite disponível de R$ 5.000,00",
    updatedAt: "Hoje",
  },
  {
    id: "conv_2",
    title: "Cotação do dólar",
    preview: "US$ 1,00 = R$ 5,42",
    updatedAt: "Ontem",
  },
  {
    id: "conv_3",
    title: "Aumento de crédito",
    preview: "Solicitação aprovada",
    updatedAt: "3 dias",
  },
  {
    id: "conv_4",
    title: "Entrevista financeira",
    preview: "Score atualizado para 742",
    updatedAt: "1 sem.",
  },
];

export const createEmptyConversation = (id: string): Conversation => ({
  id,
  title: "Nova conversa",
  updatedAt: new Date().toISOString(),
  status: "unauthenticated",
  messages: [{ ...WELCOME_MESSAGE, createdAt: new Date().toISOString() }],
});