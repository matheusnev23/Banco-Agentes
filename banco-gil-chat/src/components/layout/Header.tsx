import { EllipsisVertical, Menu, Plus, RefreshCcw, XCircle } from "lucide-react";

import { BrandMark } from "@/components/common/BrandMark";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ServiceStatus } from "@/types";

interface HeaderProps {
  status: ServiceStatus;
  onOpenMenu: () => void;
  onNewConversation: () => void;
  onEndConversation: () => void;
}

const statusLabel: Record<ServiceStatus, string> = {
  unauthenticated: "Atendimento online",
  authenticating: "Confirmando identidade",
  authenticated: "Atendimento online",
  processing: "Analisando solicitação",
  completed: "Atendimento encerrado",
  error: "Instabilidade temporária",
};

export function Header({ status, onOpenMenu, onNewConversation, onEndConversation }: HeaderProps) {
  const tone = status === "error" ? "danger" : status === "completed" ? "neutral" : "success";

  return (
    <header className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-border bg-card/80 px-4 py-3 backdrop-blur sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onOpenMenu} aria-label="Abrir menu">
          <Menu className="size-5" />
        </Button>
        <BrandMark className="hidden sm:grid" />
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold">Banco Ágil</h1>
          <p className="hidden truncate text-xs text-muted-foreground sm:block">
            Assistente virtual de atendimento
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <StatusBadge label={statusLabel[status]} tone={tone} withDot />
        <Button variant="outline" size="sm" className="hidden sm:inline-flex" onClick={onNewConversation}>
          <Plus className="size-3.5" />
          Nova conversa
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Opções">
              <EllipsisVertical className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuItem onSelect={onNewConversation}>
              <RefreshCcw className="size-4" />
              Reiniciar conversa
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={onEndConversation}>
              <XCircle className="size-4" />
              Encerrar atendimento
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}