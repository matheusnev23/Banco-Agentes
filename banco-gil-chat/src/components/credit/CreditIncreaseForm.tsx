import { useState } from "react";

import { Button } from "@/components/ui/button";
import { formatCurrency, maskCurrencyInput, parseCurrencyInput } from "@/lib/format";
import type { CreditLimit } from "@/types";

interface CreditIncreaseFormProps {
  creditLimit: CreditLimit;
  onSubmit: (amount: number) => void;
  disabled?: boolean;
}

export function CreditIncreaseForm({ creditLimit, onSubmit, disabled }: CreditIncreaseFormProps) {
  const [value, setValue] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const amount = parseCurrencyInput(value);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (!amount || disabled || submitted) return;
        setSubmitted(true);
        onSubmit(amount);
      }}
      className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]"
    >
      <p className="text-sm font-semibold">Novo limite desejado</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Limite atual: {formatCurrency(creditLimit.total, creditLimit.currency)}
      </p>

      <label className="mt-4 flex items-center gap-2 rounded-xl border border-input bg-background px-3 py-2.5 focus-within:border-brand/50">
        <span className="text-sm font-medium text-muted-foreground">R$</span>
        <input
          value={value}
          inputMode="numeric"
          placeholder="0,00"
          disabled={disabled || submitted}
          onChange={(event) => setValue(maskCurrencyInput(event.target.value))}
          className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          aria-label="Novo limite desejado"
        />
      </label>

      <Button type="submit" className="mt-4 w-full sm:w-auto" disabled={disabled || submitted || !amount}>
        Solicitar aumento
      </Button>
    </form>
  );
}