import { MessageSquarePlus, Plus, ShieldCheck } from "lucide-react";

import { BrandMark } from "@/components/common/BrandMark";
import { Button } from "@/components/ui/button";
import { MOCK_CLIENT, MOCK_CONVERSATION_HISTORY } from "@/mocks/bancoAgil";
import { cn } from "@/lib/utils";
import type { Client } from "@/types";

interface SidebarProps {
  activeConversationId: string;
  client: Client | null;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
}

export function Sidebar({
  activeConversationId,
  client,
  onNewConversation,
  onSelectConversation,
}: SidebarProps) {
  return (
    <div className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-3 px-5 py-5">
        <BrandMark className="bg-sidebar-accent ring-sidebar-border" />
        <div className="min-w-0">
          <p className="truncate font-display text-base font-semibold">Banco Ágil</p>
          <p className="truncate text-xs text-sidebar-foreground/60">Atendimento inteligente</p>
        </div>
      </div>

      <div className="px-4">
        <Button
          onClick={onNewConversation}
          className="w-full justify-start gap-2 bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90"
        >
          <Plus className="size-4" />
          Nova conversa
        </Button>
      </div>

      <div className="mt-7 min-h-0 flex-1 overflow-y-auto px-4 pb-4">
        <p className="px-2 pb-2 text-[11px] font-semibold tracking-[0.14em] text-sidebar-foreground/45 uppercase">
          Histórico (Dados Estáticos)
        </p>
        <ul className="space-y-1">
          {MOCK_CONVERSATION_HISTORY.map((item) => {
            const isActive = item.id === activeConversationId;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelectConversation(item.id)}
                  className={cn(
                    "w-full rounded-xl px-3 py-2.5 text-left transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60",
                  )}
                >
                  <span className="flex items-center gap-2">
                    <MessageSquarePlus className="size-3.5 shrink-0 opacity-60" />
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">{item.title}</span>
                    <span className="shrink-0 text-[11px] text-sidebar-foreground/40">{item.updatedAt}</span>
                  </span>
                  <span className="mt-1 block truncate pl-5.5 text-xs text-sidebar-foreground/50">
                    {item.preview}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="border-t border-sidebar-border px-5 py-4">
        <div className="flex items-center gap-2 text-xs text-sidebar-foreground/70">
          <span className="size-2 rounded-full bg-success" />
          Atendimento online
        </div>
        <div className="mt-3 flex items-center gap-3">
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-sidebar-accent text-xs font-semibold">
            {(client?.name ?? MOCK_CLIENT.name)
              .split(" ")
              .map((part) => part[0])
              .slice(0, 2)
              .join("")}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{client?.name ?? "Visitante"}</p>
            <p className="flex items-center gap-1 truncate text-[11px] text-sidebar-foreground/55">
              {client ? (
                <>
                  <ShieldCheck className="size-3" />
                  {client.maskedDocument}
                </>
              ) : (
                "Sessão não autenticada"
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}