import logo from "@/assets/banco-agil-logo.png";
import { cn } from "@/lib/utils";

export function BrandMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "grid size-9 shrink-0 place-items-center rounded-xl bg-brand-soft ring-1 ring-brand/15",
        className,
      )}
    >
      <img src={logo} alt="Banco Ágil" className="size-5 object-contain" />
    </span>
  );
}