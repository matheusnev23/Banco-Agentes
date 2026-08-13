import { SendHorizonal } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  /** Quando true, mantém o campo de mensagem ativo — a IA extrai CPF e data do texto. */
  authenticating?: boolean;
}

export function ChatInput({
  onSend,
  disabled,
  placeholder = "Digite sua mensagem...",
  authenticating = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus();
    }
  }, [disabled, authenticating]);

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    setValue("");
    onSend(text);
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className="rounded-2xl border border-border bg-card p-2 shadow-[var(--shadow-soft)] focus-within:border-brand/40"
    >
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-60"
        />
        <Button type="submit" size="icon" disabled={disabled || !value.trim()} aria-label="Enviar mensagem">
          <SendHorizonal className="size-4" />
        </Button>
      </div>
      <p className="px-2 pb-1 text-[11px] text-muted-foreground">
        Pressione Enter para enviar • Shift + Enter para quebrar linha
      </p>
    </form>
  );
}