import { ArrowUpRight, CircleDollarSign, Gauge, TrendingUp, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const QUICK_ACTIONS: { label: string; message: string; icon: LucideIcon }[] = [
  { label: "Consultar limite", message: "Quero consultar meu limite", icon: Wallet },
  { label: "Solicitar aumento de limite", message: "Quero solicitar aumento de limite", icon: TrendingUp },
  { label: "Consultar cotação", message: "Qual a cotação do dólar?", icon: CircleDollarSign },
  { label: "Atualizar meu score", message: "Quero atualizar meu score", icon: Gauge },
];

interface QuickActionsProps {
  onSelect: (message: string) => void;
  disabled?: boolean;
}

export function QuickActions({ onSelect, disabled }: QuickActionsProps) {
  return (
    <div className="animate-msg-in">
      <p className="mb-2 text-xs font-medium text-muted-foreground">Sugestões rápidas</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.label}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(action.message)}
            className="group flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3 text-left text-sm font-medium transition-all hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-[var(--shadow-soft)] disabled:pointer-events-none disabled:opacity-50"
          >
            <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
              <action.icon className="size-4" />
            </span>
            <span className="min-w-0 flex-1 truncate">{action.label}</span>
            <ArrowUpRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
          </button>
        ))}
      </div>
    </div>
  );
}