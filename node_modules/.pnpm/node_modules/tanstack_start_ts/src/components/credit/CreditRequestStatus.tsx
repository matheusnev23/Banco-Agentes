import { CheckCircle2, Clock, Gauge, XCircle } from "lucide-react";

import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/format";
import type { CreditRequest } from "@/types";

interface CreditRequestStatusProps {
  creditRequest: CreditRequest;
  onUpdateScore?: () => void;
  disabled?: boolean;
}

const config = {
  pending: { icon: Clock, tone: "warning" as const, label: "Pedido pendente", title: "Solicitação em análise" },
  approved: { icon: CheckCircle2, tone: "success" as const, label: "Pedido aprovado", title: "Solicitação aprovada" },
  rejected: { icon: XCircle, tone: "danger" as const, label: "Pedido rejeitado", title: "Solicitação não aprovada" },
};

export function CreditRequestStatus({ creditRequest, onUpdateScore, disabled }: CreditRequestStatusProps) {
  const { icon: Icon, tone, label, title } = config[creditRequest.status];

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]">
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <Icon
            className={
              creditRequest.status === "approved"
                ? "mt-0.5 size-5 shrink-0 text-success"
                : creditRequest.status === "rejected"
                  ? "mt-0.5 size-5 shrink-0 text-destructive"
                  : "mt-0.5 size-5 shrink-0 text-muted-foreground"
            }
          />
          <div className="min-w-0">
            <p className="text-sm font-semibold">{title}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {creditRequest.message ?? "Acompanhe o andamento por aqui."}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Limite solicitado: {formatCurrency(creditRequest.requestedLimit, creditRequest.currency)}
            </p>
          </div>
        </div>
        <StatusBadge label={label} tone={tone} />
      </div>

      {creditRequest.status === "rejected" && onUpdateScore && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onUpdateScore} disabled={disabled}>
          <Gauge className="size-3.5" />
          Atualizar meu score
        </Button>
      )}
    </div>
  );
}