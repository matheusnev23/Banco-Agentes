import { Gauge } from "lucide-react";

import { StatusBadge } from "@/components/common/StatusBadge";
import type { CreditScore } from "@/types";

const bandLabel = { low: "Score baixo", medium: "Score médio", high: "Score bom" } as const;

export function ScoreCard({ score }: { score: CreditScore }) {
  const percentage = Math.round((score.value / score.max) * 100);

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]">
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
        <div className="flex min-w-0 items-center gap-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
          <Gauge className="size-3.5" />
          Score de crédito
        </div>
        <StatusBadge label={bandLabel[score.band]} tone={score.band === "low" ? "warning" : "success"} />
      </div>

      <p className="mt-3 font-display text-3xl font-semibold">
        {score.value}
        <span className="ml-1 text-base font-medium text-muted-foreground">/ {score.max}</span>
      </p>

      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-success" style={{ width: `${percentage}%` }} />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">Atualizado agora</p>
    </div>
  );
}