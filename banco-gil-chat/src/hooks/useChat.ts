import { useCallback, useEffect, useRef, useState } from "react";

import { createEmptyConversation } from "@/mocks/bancoAgil";
import { chatService } from "@/services/chatService";
import type {
  ChatResponse,
  Client,
  Conversation,
  Message,
  MessageWidget,
  ServiceStatus,
} from "@/types";

const createId = (prefix: string) => `${prefix}_${Math.random().toString(36).slice(2, 10)}`;

const createMessage = (
  role: Message["role"],
  content: string,
  widget?: MessageWidget,
): Message => ({
  id: createId("msg"),
  role,
  content,
  createdAt: new Date().toISOString(),
  ...(widget ? { widget } : {}),
});

/** Chave usada para persistir o histórico da conversa no navegador. */
const STORAGE_KEY = "banco-agil:conversation";

function loadPersistedConversation(): Conversation | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Conversation;
    if (!parsed || !Array.isArray(parsed.messages)) return null;
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Single source of truth for the conversation. All side effects go through
 * `chatService`, so replacing the mocks with the FastAPI endpoints requires no
 * change in this hook's public surface.
 *
 * Fluxo 100% conversacional: a autenticação e a coleta de informações são feitas
 * extraindo dados diretamente do texto do usuário (CPF, data de nascimento,
 * valores). As caixas (widgets) servem apenas para exibir informações.
 *
 * O histórico das mensagens (do agente e do usuário) é salvo no navegador via
 * `localStorage`, de modo que a conversa sobreviva a um recarregamento da página.
 */
export function useChat() {
  const [conversation, setConversation] = useState<Conversation>(() => {
    const persisted = loadPersistedConversation();
    if (persisted) return persisted;
    return createEmptyConversation(createId("conv"));
  });
  const [status, setStatus] = useState<ServiceStatus>(() =>
    conversation.status ? conversation.status : "unauthenticated",
  );
  const [client, setClient] = useState<Client | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const lastUserMessage = useRef<string | null>(null);

  // Persiste a conversa (agente + usuário) no navegador a cada mudança.
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(conversation));
    } catch {
      // Quota excedida ou armazenamento indisponível — ignora silenciosamente.
    }
  }, [conversation]);

  const appendMessages = useCallback((...messages: Message[]) => {
    setConversation((current) => ({
      ...current,
      messages: [...current.messages, ...messages],
      updatedAt: new Date().toISOString(),
    }));
  }, []);

  const applyResponse = useCallback(
    (response: ChatResponse) => {
      setStatus(response.status);
      if (response.metadata.client) {
        setClient(response.metadata.client);
      } else if (response.status === "unauthenticated" || response.status === "completed") {
        setClient(null);
      }
      appendMessages(createMessage("assistant", response.message, response.metadata.widget));
    },
    [appendMessages],
  );

  const dispatchToBackend = useCallback(
    async (message: string) => {
      setIsProcessing(true);
      try {
        const response = await chatService.sendMessage(
          { session_id: conversation.id, message },
          { authenticated: client !== null },
        );
        applyResponse(response);
      } finally {
        setIsProcessing(false);
      }
    },
    [applyResponse, conversation.id, client],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const text = content.trim();
      if (!text || isProcessing) return;
      lastUserMessage.current = text;
      appendMessages(createMessage("user", text));
      await dispatchToBackend(text);
    },
    [appendMessages, dispatchToBackend, isProcessing],
  );

  const requestCreditIncrease = useCallback(
    async (amount: number) => {
      setIsProcessing(true);
      appendMessages(createMessage("user", `Quero solicitar um limite de R$ ${amount.toLocaleString("pt-BR")}`));
      try {
        const creditRequest = await chatService.requestCreditIncrease(conversation.id, amount);
        appendMessages(
          createMessage(
            "assistant",
            creditRequest.status === "approved"
              ? "Analisei sua solicitação e tenho boas notícias."
              : "Analisei sua solicitação com atenção.",
            { kind: "credit_request", creditRequest },
          ),
        );
      } finally {
        setIsProcessing(false);
      }
    },
    [appendMessages, conversation.id],
  );

  const submitInterview = useCallback(
    async (answers: Record<string, string>) => {
      setIsProcessing(true);
      try {
        const { score } = await chatService.submitInterview(conversation.id, answers);
        appendMessages(createMessage("assistant", "Seu score foi atualizado.", { kind: "score", score }));
      } finally {
        setIsProcessing(false);
      }
    },
    [appendMessages, conversation.id],
  );

  const showCreditIncreaseForm = useCallback(async () => {
    await sendMessage("Quero solicitar aumento de limite");
  }, [sendMessage]);

  const startInterview = useCallback(async () => {
    await sendMessage("Quero atualizar meu score");
  }, [sendMessage]);

  const changeCurrency = useCallback(
    async (base: string) => {
      setIsProcessing(true);
      try {
        const exchangeRate = await chatService.getExchangeRate(base);
        appendMessages(
          createMessage("assistant", "Aqui está a cotação atualizada.", {
            kind: "exchange_rate",
            exchangeRate,
          }),
        );
      } finally {
        setIsProcessing(false);
      }
    },
    [appendMessages],
  );

  const retryLastMessage = useCallback(async () => {
    const last = lastUserMessage.current;
    if (!last) return;
    await sendMessage(last);
  }, [sendMessage]);

  const endConversation = useCallback(async () => {
    const response = await chatService.endConversation(conversation.id);
    applyResponse(response);
  }, [applyResponse, conversation.id]);

  const startNewConversation = useCallback(() => {
    lastUserMessage.current = null;
    setClient(null);
    setStatus("unauthenticated");
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignora falhas de armazenamento.
    }
    setConversation(createEmptyConversation(createId("conv")));
  }, []);

  return {
    conversation,
    status,
    client,
    isProcessing,
    sendMessage,
    requestCreditIncrease,
    submitInterview,
    showCreditIncreaseForm,
    startInterview,
    changeCurrency,
    retryLastMessage,
    endConversation,
    startNewConversation,
  };
}

export type ChatController = ReturnType<typeof useChat>;