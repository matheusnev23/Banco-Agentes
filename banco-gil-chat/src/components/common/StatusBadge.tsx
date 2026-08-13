import { cn } from "@/lib/utils";

type Tone = "success" | "neutral" | "brand" | "warning" | "danger";

const toneClasses: Record<Tone, string> = {
  success: "bg-success-soft text-success",
  neutral: "bg-muted text-muted-foreground",
  brand: "bg-brand-soft text-brand",
  warning: "bg-accent text-accent-foreground",
  danger: "bg-destructive/10 text-destructive",
};

interface StatusBadgeProps {
  label: string;
  tone?: Tone;
  withDot?: boolean;
  className?: string;
}

export function StatusBadge({ label, tone = "neutral", withDot = false, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        toneClasses[tone],
        className,
      )}
    >
      {withDot && <span className="size-1.5 rounded-full bg-current" />}
      {label}
    </span>
  );
}