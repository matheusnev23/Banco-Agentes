import { ShieldCheck } from "lucide-react";
import { useEffect, useRef } from "react";

import { ChatInput } from "@/components/chat/ChatInput";
import { ChatMessage } from "@/components/chat/ChatMessage";
import type { WidgetHandlers } from "@/components/chat/MessageWidget";
import { QuickActions } from "@/components/chat/QuickActions";
import { TypingIndicator } from "@/components/chat/TypingIndicator";
import type { Conversation, ServiceStatus } from "@/types";

interface ChatWindowProps {
  conversation: Conversation;
  status: ServiceStatus;
  isProcessing: boolean;
  isAuthenticated: boolean;
  clientName?: string;
  handlers: WidgetHandlers;
  onSend: (message: string) => void;
}

export function ChatWindow({
  conversation,
  status,
  isProcessing,
  isAuthenticated,
  clientName,
  handlers,
  onSend,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [conversation.messages.length, isProcessing]);

  const showQuickActions = conversation.messages.length <= 2 && !isProcessing;
  const isClosed = status === "completed";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
          {isAuthenticated && (
            <div className="flex justify-center">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-success-soft px-3 py-1 text-xs font-medium text-success">
                <ShieldCheck className="size-3.5" />
                {clientName ? `Bem-vindo, ${clientName.split(" ")[0]}!` : "Cliente autenticado"}
              </span>
            </div>
          )}

          {conversation.messages.map((message) => (
            <ChatMessage key={message.id} message={message} handlers={handlers} />
          ))}

          {isProcessing && <TypingIndicator />}
          {showQuickActions && <QuickActions onSelect={onSend} disabled={isProcessing} />}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-border bg-background/80 px-4 py-4 backdrop-blur sm:px-6">
        <div className="mx-auto w-full max-w-3xl">
          <ChatInput
            onSend={onSend}
            disabled={isProcessing || isClosed}
            authenticating={status === "authenticating"}
            placeholder={
              isClosed
                ? "Atendimento encerrado — inicie uma nova conversa"
                : status === "authenticating"
                  ? "Digite seu CPF e data de nascimento... (ex: 123.456.789-00 e 15/03/1988)"
                  : "Digite sua mensagem..."
            }
          />
        </div>
      </div>
    </div>
  );
}