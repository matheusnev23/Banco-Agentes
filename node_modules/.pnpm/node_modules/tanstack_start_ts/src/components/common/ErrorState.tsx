import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ServiceError } from "@/types";

interface ErrorStateProps {
  error: ServiceError;
  onRetry?: () => void;
  disabled?: boolean;
}

export function ErrorState({ error, onRetry, disabled }: ErrorStateProps) {
  return (
    <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">{error.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">{error.description}</p>
        </div>
      </div>
      {error.retryable && onRetry && (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry} disabled={disabled}>
          <RotateCcw className="size-3.5" />
          Tentar novamente
        </Button>
      )}
    </div>
  );
}