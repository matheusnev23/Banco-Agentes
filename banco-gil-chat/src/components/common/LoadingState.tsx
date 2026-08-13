import { cn } from "@/lib/utils";

export function LoadingDots({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1", className)}>
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="animate-dot size-1.5 rounded-full bg-current"
          style={{ animationDelay: `${index * 0.15}s` }}
        />
      ))}
    </span>
  );
}

export function LoadingState({ label = "Analisando sua solicitação..." }: { label?: string }) {
  return (
    <div className="inline-flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3 text-sm text-muted-foreground shadow-[var(--shadow-soft)]">
      <span>{label}</span>
      <LoadingDots className="text-brand" />
    </div>
  );
}