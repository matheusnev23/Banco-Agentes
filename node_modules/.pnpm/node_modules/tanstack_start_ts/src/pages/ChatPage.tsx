import { useState } from "react";

import { ChatWindow } from "@/components/chat/ChatWindow";
import type { WidgetHandlers } from "@/components/chat/MessageWidget";
import { Header } from "@/components/layout/Header";
import { MainLayout } from "@/components/layout/MainLayout";
import { Sidebar } from "@/components/layout/Sidebar";
import { useChat } from "@/hooks/useChat";

export function ChatPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const chat = useChat();

  const closeMenu = () => setMobileMenuOpen(false);

  const handlers: WidgetHandlers = {
    disabled: chat.isProcessing,
    onRequestIncreaseForm: () => void chat.showCreditIncreaseForm(),
    onStartInterview: () => void chat.startInterview(),
    onChangeCurrency: (base) => void chat.changeCurrency(base),
    onRetry: () => void chat.retryLastMessage(),
    onNewConversation: chat.startNewConversation,
    onSubmitInterview: (answers) => void chat.submitInterview(answers),
  };

  const startNew = () => {
    chat.startNewConversation();
    closeMenu();
  };

  return (
    <MainLayout
      mobileMenuOpen={mobileMenuOpen}
      onMobileMenuChange={setMobileMenuOpen}
      sidebar={
        <Sidebar
          activeConversationId={chat.conversation.id}
          client={chat.client}
          onNewConversation={startNew}
          onSelectConversation={closeMenu}
        />
      }
      header={
        <Header
          status={chat.status}
          onOpenMenu={() => setMobileMenuOpen(true)}
          onNewConversation={startNew}
          onEndConversation={() => void chat.endConversation()}
        />
      }
    >
      <ChatWindow
        conversation={chat.conversation}
        status={chat.status}
        isProcessing={chat.isProcessing}
        isAuthenticated={Boolean(chat.client?.authenticated)}
        {...(chat.client?.name ? { clientName: chat.client.name } : {})}
        handlers={handlers}
        onSend={(message) => void chat.sendMessage(message)}
      />
    </MainLayout>
  );
}