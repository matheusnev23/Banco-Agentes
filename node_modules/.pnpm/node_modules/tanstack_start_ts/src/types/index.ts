/**
 * Domain types shared by UI, mocks and the future REST integration.
 * Field names mirror the planned FastAPI contract (snake_case on the wire is
 * mapped inside `src/services/api.ts`).
 */

/** Internal agent handling the turn. Never surfaced to the customer. */
export type AgentState = "triage" | "credit" | "credit_interview" | "exchange";

/** Lifecycle of the service session. */
export type ServiceStatus =
  | "unauthenticated"
  | "authenticating"
  | "authenticated"
  | "processing"
  | "completed"
  | "error";

export type AuthenticationState = ServiceStatus;

export interface Client {
  id: string;
  name: string;
  /** Masked on purpose — never store or render full documents. */
  maskedDocument: string;
  authenticated: boolean;
}

export interface AuthenticationPayload {
  document: string;
  birthDate: string;
}

export interface CreditLimit {
  available: number;
  total: number;
  currency: string;
  updatedAt: string;
}

export type CreditRequestStatus = "pending" | "approved" | "rejected";

export interface CreditRequest {
  id: string;
  requestedLimit: number;
  currency: string;
  status: CreditRequestStatus;
  message?: string;
  createdAt: string;
  newTotal?: number;
  newAvailable?: number;
}

export interface CreditScore {
  value: number;
  max: number;
  band: "low" | "medium" | "high";
  updatedAt: string;
}

export interface ExchangeRate {
  base: string;
  quote: string;
  rate: number;
  variation?: number;
  updatedAt: string;
}

export interface InterviewQuestion {
  id: string;
  label: string;
  placeholder?: string;
  kind: "currency" | "number" | "text" | "choice";
  options?: string[];
  answer?: string;
}

export interface ServiceError {
  title: string;
  description: string;
  retryable: boolean;
}

/** Rich blocks the assistant can attach to a message. */
export type MessageWidget =
  | { kind: "credit_limit"; creditLimit: CreditLimit }
  | { kind: "credit_request"; creditRequest: CreditRequest }
  | { kind: "interview"; questions: InterviewQuestion[] }
  | { kind: "score"; score: CreditScore }
  | { kind: "exchange_rate"; exchangeRate: ExchangeRate }
  | { kind: "error"; error: ServiceError }
  | { kind: "closing" };

export type MessageRole = "assistant" | "user";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  widget?: MessageWidget;
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
  status: ServiceStatus;
  messages: Message[];
}

export interface ConversationSummary {
  id: string;
  title: string;
  preview: string;
  updatedAt: string;
}

/** Shape of `POST /api/chat` (mocked for now). */
export interface ChatResponse {
  session_id: string;
  message: string;
  status: ServiceStatus;
  authenticated: boolean;
  metadata: {
    agent?: AgentState;
    widget?: MessageWidget;
    client?: Client;
    [key: string]: unknown;
  };
}

export interface ChatRequest {
  session_id: string;
  message: string;
}