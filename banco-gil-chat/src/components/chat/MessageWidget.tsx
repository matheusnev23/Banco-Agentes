import { PartyPopper, Plus } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { CreditLimitCard } from "@/components/credit/CreditLimitCard";
import { CreditRequestStatus } from "@/components/credit/CreditRequestStatus";
import { ExchangeRateCard } from "@/components/exchange/ExchangeRateCard";
import { InterviewCard } from "@/components/interview/InterviewCard";
import { ScoreCard } from "@/components/interview/ScoreCard";
import { Button } from "@/components/ui/button";
import type {
  CreditLimit,
  CreditRequest,
  CreditScore,
  ExchangeRate,
  InterviewQuestion,
  MessageWidget as Widget,
} from "@/types";

export interface WidgetHandlers {
  disabled: boolean;
  onRequestIncreaseForm: () => void;
  onStartInterview: () => void;
  onChangeCurrency: (base: string) => void;
  onRetry: () => void;
  onNewConversation: () => void;
  onSubmitInterview: (answers: Record<string, string>) => void;
}

export function MessageWidget({ widget, handlers }: { widget: Widget; handlers: WidgetHandlers }) {
  const { disabled } = handlers;

  switch (widget.kind) {
    case "credit_limit":
      return (
        <CreditLimitCard
          creditLimit={widget.creditLimit as CreditLimit}
          onRequestIncrease={handlers.onRequestIncreaseForm}
          disabled={disabled}
        />
      );
    case "credit_request":
      return (
        <CreditRequestStatus
          creditRequest={widget.creditRequest as CreditRequest}
          onUpdateScore={handlers.onStartInterview}
          disabled={disabled}
        />
      );
    case "exchange_rate":
      return (
        <ExchangeRateCard
          exchangeRate={widget.exchangeRate as ExchangeRate}
          onChangeCurrency={handlers.onChangeCurrency}
          disabled={disabled}
        />
      );
    case "interview":
      return (
        <InterviewCard
          questions={widget.questions as InterviewQuestion[]}
          onComplete={handlers.onSubmitInterview}
          disabled={disabled}
        />
      );
    case "score":
      return <ScoreCard score={widget.score as CreditScore} />;
    case "error":
      return <ErrorState error={widget.error} onRetry={handlers.onRetry} disabled={disabled} />;
    case "closing":
      return (
        <div className="rounded-2xl border border-border bg-card p-5 text-center shadow-[var(--shadow-card)]">
          <PartyPopper className="mx-auto size-5 text-brand" />
          <p className="mt-2 text-sm font-semibold">Atendimento encerrado</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Foi um prazer ajudar. Sempre que precisar, estaremos por aqui.
          </p>
          <Button className="mt-4" onClick={handlers.onNewConversation}>
            <Plus className="size-4" />
            Nova conversa
          </Button>
        </div>
      );
    default:
      return null;
  }
}