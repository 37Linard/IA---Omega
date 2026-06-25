'use client'

import { useState, useEffect } from 'react'
import { Sidebar } from '@/components/Sidebar'
import { ChatArea } from '@/components/ChatArea'
import { Header } from '@/components/Header'
import { useChatStore } from '@/store/chatStore'

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { conversations, newConversation, activeId, setActive } = useChatStore()

  useEffect(() => {
    if (conversations.length === 0) {
      newConversation()
    } else if (!activeId || !conversations.find(c => c.id === activeId)) {
      setActive(conversations[0].id)
    }
  }, [conversations, activeId, newConversation, setActive])

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--chat-bg)',
      }}
    >
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
        <Header onToggleSidebar={() => setSidebarOpen(o => !o)} />
        <main style={{ flex: 1, overflow: 'hidden' }}>
          <ChatArea />
        </main>
      </div>
    </div>
  )
}
