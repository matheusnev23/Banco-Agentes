import { ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { maskBirthDateInput, maskDocumentInput } from "@/lib/format";
import type { AuthenticationPayload } from "@/types";

interface AuthenticationFormProps {
  onSubmit: (payload: AuthenticationPayload) => void;
  disabled?: boolean;
}

/** Presentation only — validation belongs to the backend. */
export function AuthenticationForm({ onSubmit, disabled }: AuthenticationFormProps) {
  const [document, setDocument] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const ready = document.length > 0 && birthDate.length > 0;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (!ready || disabled || submitted) return;
        setSubmitted(true);
        onSubmit({ document, birthDate });
      }}
      className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]"
    >
      <div className="flex items-center gap-2 text-sm font-semibold">
        <ShieldCheck className="size-4 text-brand" />
        Confirmação de identidade
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        Seus dados são usados apenas para validar o atendimento.
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs font-medium text-muted-foreground">CPF</span>
          <input
            value={document}
            inputMode="numeric"
            placeholder="000.000.000-00"
            disabled={disabled || submitted}
            onChange={(event) => setDocument(maskDocumentInput(event.target.value))}
            className="mt-1 w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none focus:border-brand/50"
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-muted-foreground">Data de nascimento</span>
          <input
            value={birthDate}
            inputMode="numeric"
            placeholder="dd/mm/aaaa"
            disabled={disabled || submitted}
            onChange={(event) => setBirthDate(maskBirthDateInput(event.target.value))}
            className="mt-1 w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none focus:border-brand/50"
          />
        </label>
      </div>

      <Button type="submit" className="mt-4 w-full sm:w-auto" disabled={disabled || submitted || !ready}>
        Continuar
      </Button>
    </form>
  );
}