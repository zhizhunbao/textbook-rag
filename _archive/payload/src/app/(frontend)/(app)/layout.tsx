import AppLayout from '@/features/layout/AppLayout'
import { ChatHistoryProvider } from '@/features/chat/history/ChatHistoryContext'

export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  return (
    <ChatHistoryProvider>
      <AppLayout>
        {children}
      </AppLayout>
    </ChatHistoryProvider>
  )
}

