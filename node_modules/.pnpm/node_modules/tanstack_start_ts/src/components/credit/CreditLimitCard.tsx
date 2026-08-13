import { TrendingUp, Wallet } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/format";
import type { CreditLimit } from "@/types";

interface CreditLimitCardProps {
  creditLimit: CreditLimit;
  onRequestIncrease?: () => void;
  disabled?: boolean;
}

export function CreditLimitCard({ creditLimit, onRequestIncrease, disabled }: CreditLimitCardProps) {
  const used = Math.max(creditLimit.total - creditLimit.available, 0);
  const percentage = creditLimit.total ? Math.round((creditLimit.available / creditLimit.total) * 100) : 0;

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-center gap-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
        <Wallet className="size-3.5" />
        Limite disponível
      </div>
      <p className="mt-3 font-display text-3xl font-semibold text-foreground">
        {formatCurrency(creditLimit.available, creditLimit.currency)}
      </p>
      <p className="mt-1 text-sm text-success">Disponível para utilização</p>

      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-brand" style={{ width: `${percentage}%` }} />
      </div>
      <div className="mt-2 flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
        <span>Utilizado {formatCurrency(used, creditLimit.currency)}</span>
        <span>Total {formatCurrency(creditLimit.total, creditLimit.currency)}</span>
      </div>

      {onRequestIncrease && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRequestIncrease} disabled={disabled}>
          <TrendingUp className="size-3.5" />
          Solicitar aumento
        </Button>
      )}
    </div>
  );
}