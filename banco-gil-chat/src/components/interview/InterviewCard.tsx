import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { maskCurrencyInput } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { InterviewQuestion } from "@/types";

interface InterviewCardProps {
  questions: InterviewQuestion[];
  onComplete: (answers: Record<string, string>) => void;
  disabled?: boolean;
}

/** Conversational, one-question-at-a-time financial interview UI. */
export function InterviewCard({ questions, onComplete, disabled }: InterviewCardProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [index, setIndex] = useState(0);
  const [draft, setDraft] = useState("");
  const [finished, setFinished] = useState(false);

  const question = questions[index];
  const progress = useMemo(() => Math.round((index / questions.length) * 100), [index, questions.length]);

  const commit = (value: string) => {
    if (!question || !value.trim() || disabled) return;
    const next = { ...answers, [question.id]: value };
    setAnswers(next);
    setDraft("");
    if (index + 1 >= questions.length) {
      setFinished(true);
      onComplete(next);
      return;
    }
    setIndex(index + 1);
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="font-medium">Entrevista financeira</span>
        <span>
          {Math.min(index + (finished ? 0 : 1), questions.length)} de {questions.length}
        </span>
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-brand transition-all"
          style={{ width: `${finished ? 100 : progress}%` }}
        />
      </div>

      {Object.keys(answers).length > 0 && (
        <ul className="mt-4 space-y-2">
          {questions
            .filter((item) => answers[item.id])
            .map((item) => (
              <li key={item.id} className="rounded-xl bg-muted/60 px-3 py-2">
                <p className="text-xs text-muted-foreground">{item.label}</p>
                <p className="text-sm font-medium">
                  {item.kind === "currency" ? `R$ ${answers[item.id]}` : answers[item.id]}
                </p>
              </li>
            ))}
        </ul>
      )}

      {finished ? (
        <p className="mt-4 text-sm text-success">Respostas enviadas para análise.</p>
      ) : (
        question && (
          <div className="mt-4">
            <p className="text-sm font-semibold">{question.label}</p>

            {question.kind === "choice" ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {question.options?.map((option) => (
                  <button
                    key={option}
                    type="button"
                    disabled={disabled}
                    onClick={() => commit(option)}
                    className={cn(
                      "rounded-full border border-border px-3 py-1.5 text-sm transition-colors",
                      "hover:border-brand/50 hover:bg-brand-soft hover:text-brand disabled:opacity-50",
                    )}
                  >
                    {option}
                  </button>
                ))}
              </div>
            ) : (
              <form
                className="mt-3 flex flex-wrap items-center gap-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  commit(draft);
                }}
              >
                <label className="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-input bg-background px-3 py-2.5 focus-within:border-brand/50">
                  {question.kind === "currency" && (
                    <span className="text-sm text-muted-foreground">R$</span>
                  )}
                  <input
                    value={draft}
                    inputMode="numeric"
                    placeholder={question.placeholder ?? ""}
                    disabled={disabled}
                    onChange={(event) =>
                      setDraft(
                        question.kind === "currency"
                          ? maskCurrencyInput(event.target.value)
                          : event.target.value,
                      )
                    }
                    className="w-full min-w-0 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                    aria-label={question.label}
                  />
                </label>
                <Button type="submit" size="sm" disabled={disabled || !draft.trim()}>
                  Responder
                </Button>
              </form>
            )}
          </div>
        )
      )}
    </div>
  );
}