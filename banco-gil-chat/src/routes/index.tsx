import { createFileRoute } from "@tanstack/react-router";

import { ChatPage } from "@/pages/ChatPage";

const title = "Banco Ágil — Atendimento inteligente";
const description =
  "Converse com o assistente do Banco Ágil para consultar limite, solicitar aumento de crédito, atualizar seu score e ver cotações de moedas.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: Index,
});

function Index() {
  return <ChatPage />;
}
