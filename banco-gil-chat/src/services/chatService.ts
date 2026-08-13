import { request } from "@/services/api";
import type {
  AuthenticationPayload,
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationSummary,
  CreditLimit,
  CreditRequest,
  CreditScore,
  ExchangeRate,
  InterviewQuestion,
} from "@/types";

const createId = (prefix: string) => `${prefix}_${Math.random().toString(36).slice(2, 10)}`;

/** Mapeia CreditLimit do backend (snake_case) para o tipo do frontend (camelCase). */
const mapCreditLimit = (raw: {
  available: number;
  total: number;
  currency: string;
  updated_at: string;
}): CreditLimit => ({
  available: raw.available,
  total: raw.total,
  currency: raw.currency,
  updatedAt: raw.updated_at,
});

/** Mapeia CreditRequest do backend (snake_case) para o tipo do frontend (camelCase). */
const mapCreditRequest = (raw: {
  id: string;
  requested_limit: number;
  currency: string;
  status: CreditRequest["status"];
  message?: string | null;
  created_at: string;
}): CreditRequest => ({
  id: raw.id,
  requestedLimit: raw.requested_limit,
  currency: raw.currency,
  status: raw.status,
  ...(raw.message != null ? { message: raw.message } : {}),
  createdAt: raw.created_at,
});

/** Mapeia CreditScore do backend (snake_case) para o tipo do frontend (camelCase). */
const mapCreditScore = (raw: {
  value: number;
  max: number;
  band: CreditScore["band"];
  updated_at: string;
}): CreditScore => ({
  value: raw.value,
  max: raw.max,
  band: raw.band,
  updatedAt: raw.updated_at,
});

/** Mapeia InterviewQuestion do backend (snake_case) para o tipo do frontend (camelCase). */
const mapInterviewQuestion = (raw: {
  id: string;
  label: string;
  kind: InterviewQuestion["kind"];
  placeholder?: string | null;
  options?: string[] | null;
  answer?: string | null;
}): InterviewQuestion => ({
  id: raw.id,
  label: raw.label,
  kind: raw.kind,
  ...(raw.placeholder != null ? { placeholder: raw.placeholder } : {}),
  ...(raw.options != null ? { options: raw.options } : {}),
  ...(raw.answer != null ? { answer: raw.answer } : {}),
});

/** Mapeia ExchangeRate do backend (snake_case) para o tipo do frontend (camelCase). */
const mapExchangeRate = (raw: {
  base: string;
  quote: string;
  rate: number;
  variation?: number | null;
  updated_at: string;
}): ExchangeRate => ({
  base: raw.base,
  quote: raw.quote,
  rate: raw.rate,
  ...(raw.variation != null ? { variation: raw.variation } : {}),
  updatedAt: raw.updated_at,
});

export const chatService = {
  async startConversation(): Promise<Conversation> {
    const response = await request<{ session_id: string }>("/api/chat/start", {
      method: "POST",
      body: JSON.stringify({}),
    });
    return {
      id: response.session_id,
      title: "Nova conversa",
      updatedAt: new Date().toISOString(),
      status: "unauthenticated",
      messages: [
        {
          id: createId("msg"),
          role: "assistant",
          content: "Olá! Sou o assistente do Banco Ágil. Como posso ajudar você hoje?",
          createdAt: new Date().toISOString(),
        },
      ],
    };
  },

  async getConversation(sessionId: string): Promise<Conversation> {
    return {
      id: sessionId,
      title: "Nova conversa",
      updatedAt: new Date().toISOString(),
      status: "unauthenticated",
      messages: [],
    };
  },

  async getConversationHistory(): Promise<ConversationSummary[]> {
    return [];
  },

  /** Maps to `POST /api/chat`. */
  async sendMessage(
    { session_id, message }: ChatRequest,
    _context: { authenticated: boolean },
  ): Promise<ChatResponse> {
    return request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ session_id, message }),
    });
  },

  /** Maps to `POST /api/auth`. */
  async authenticateClient(sessionId: string, payload: AuthenticationPayload): Promise<ChatResponse> {
    return request<ChatResponse>("/api/auth", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        document: payload.document,
        birth_date: payload.birthDate,
      }),
    });
  },

  async getCreditLimit(sessionId: string): Promise<CreditLimit> {
    const raw = await request<{
      available: number;
      total: number;
      currency: string;
      updated_at: string;
    }>(`/api/credit/limit?session_id=${sessionId}`);
    return mapCreditLimit(raw);
  },

  async requestCreditIncrease(sessionId: string, requestedLimit: number): Promise<CreditRequest> {
    const raw = await request<{
      id: string;
      requested_limit: number;
      currency: string;
      status: CreditRequest["status"];
      message?: string | null;
      created_at: string;
    }>("/api/credit/increase", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, requested_limit: requestedLimit }),
    });
    return mapCreditRequest(raw);
  },

  async submitInterview(
    sessionId: string,
    answers: Record<string, string>,
  ): Promise<{ score: CreditScore; questions: InterviewQuestion[] }> {
    const raw = await request<{
      score: { value: number; max: number; band: CreditScore["band"]; updated_at: string };
      questions: Array<{
        id: string;
        label: string;
        kind: InterviewQuestion["kind"];
        placeholder?: string | null;
        options?: string[] | null;
        answer?: string | null;
      }>;
    }>("/api/interview", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, answers }),
    });
    return {
      score: mapCreditScore(raw.score),
      questions: raw.questions.map(mapInterviewQuestion),
    };
  },

  async getExchangeRate(base = "USD", quote = "BRL"): Promise<ExchangeRate> {
    const raw = await request<{
      base: string;
      quote: string;
      rate: number;
      variation?: number | null;
      updated_at: string;
    }>(`/api/exchange/rate?base=${base}&quote=${quote}`);
    return mapExchangeRate(raw);
  },

  async endConversation(sessionId: string): Promise<ChatResponse> {
    return request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message: "encerrar" }),
    });
  },
};