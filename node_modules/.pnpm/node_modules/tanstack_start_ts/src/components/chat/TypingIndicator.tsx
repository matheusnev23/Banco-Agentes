import { BrandMark } from "@/components/common/BrandMark";
import { LoadingDots } from "@/components/common/LoadingState";

export function TypingIndicator({ label = "Analisando sua solicitação..." }: { label?: string }) {
  return (
    <div className="animate-msg-in flex items-end gap-3">
      <BrandMark className="size-8" />
      <div className="flex items-center gap-3 rounded-2xl rounded-bl-md border border-border bg-card px-4 py-3 shadow-[var(--shadow-soft)]">
        <span className="text-sm text-muted-foreground">{label}</span>
        <LoadingDots className="text-brand" />
      </div>
    </div>
  );
}