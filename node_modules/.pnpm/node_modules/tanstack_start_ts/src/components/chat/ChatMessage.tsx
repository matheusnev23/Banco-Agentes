import { BrandMark } from "@/components/common/BrandMark";
import { MessageWidget, type WidgetHandlers } from "@/components/chat/MessageWidget";
import { formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Message } from "@/types";

interface ChatMessageProps {
  message: Message;
  handlers: WidgetHandlers;
}

export function ChatMessage({ message, handlers }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("animate-msg-in flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && <BrandMark className="size-8" />}

      <div className={cn("flex min-w-0 max-w-[min(38rem,88%)] flex-col gap-2", isUser && "items-end")}>
        <div
          className={cn(
            "w-fit px-4 py-2.5 text-sm leading-relaxed whitespace-pre-line",
            isUser
              ? "rounded-2xl rounded-br-md bg-primary text-primary-foreground"
              : "rounded-2xl rounded-bl-md border border-border bg-card text-card-foreground shadow-[var(--shadow-soft)]",
          )}
        >
          {message.content}
        </div>

        {message.widget && (
          <div className="w-full max-w-sm">
            <MessageWidget widget={message.widget} handlers={handlers} />
          </div>
        )}

        <span className="px-1 text-[11px] text-muted-foreground">{formatTime(message.createdAt)}</span>
      </div>
    </div>
  );
}