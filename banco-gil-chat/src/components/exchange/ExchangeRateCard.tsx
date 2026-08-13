import { ArrowRight, TrendingDown, TrendingUp } from "lucide-react";

import { formatCurrency } from "@/lib/format";
import { MOCK_EXCHANGE_RATES } from "@/mocks/bancoAgil";
import { cn } from "@/lib/utils";
import type { ExchangeRate } from "@/types";

interface ExchangeRateCardProps {
  exchangeRate: ExchangeRate;
  onChangeCurrency?: (base: string) => void;
  disabled?: boolean;
}

export function ExchangeRateCard({ exchangeRate, onChangeCurrency, disabled }: ExchangeRateCardProps) {
  const positive = (exchangeRate.variation ?? 0) >= 0;
  const Trend = positive ? TrendingUp : TrendingDown;

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-center gap-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {exchangeRate.base}
        <ArrowRight className="size-3" />
        {exchangeRate.quote}
      </div>

      <p className="mt-3 font-display text-2xl font-semibold">
        {exchangeRate.base} 1,00 = {formatCurrency(exchangeRate.rate, exchangeRate.quote)}
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
        {exchangeRate.variation !== undefined && (
          <span className={cn("inline-flex items-center gap-1", positive ? "text-success" : "text-destructive")}>
            <Trend className="size-3.5" />
            {positive ? "+" : ""}
            {exchangeRate.variation.toFixed(2)}%
          </span>
        )}
        <span className="text-muted-foreground">Atualizado agora</span>
      </div>

      {onChangeCurrency && (
        <div className="mt-4 flex flex-wrap gap-2">
          {MOCK_EXCHANGE_RATES.map((rate) => (
            <button
              key={rate.base}
              type="button"
              disabled={disabled || rate.base === exchangeRate.base}
              onClick={() => onChangeCurrency(rate.base)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                rate.base === exchangeRate.base
                  ? "border-brand/40 bg-brand-soft text-brand"
                  : "border-border hover:border-brand/40 hover:text-brand",
                "disabled:pointer-events-none",
              )}
            >
              {rate.base}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}