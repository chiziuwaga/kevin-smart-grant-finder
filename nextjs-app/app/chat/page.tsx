'use client';

import { useChat } from 'ai/react';
import { useEffect, useState } from 'react';
import { Send, Settings, Menu, X, CreditCard, LogOut } from 'lucide-react';
import { toast } from 'sonner';

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [balance, setBalance] = useState<number | null>(null);
  const [chatHistories, setChatHistories] = useState<any[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);

  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',
    body: { chatId: currentChatId },
    onError: (error) => {
      if (error.message.includes('402')) {
        toast.error('Insufficient credits. Please top up to continue.');
      } else if (error.message.includes('429')) {
        toast.error('Message limit reached. Please start a new chat.');
      } else {
        toast.error('Failed to send message');
      }
    },
  });

  // Fetch credit balance
  useEffect(() => {
    fetch('/api/credits/balance')
      .then((res) => res.json())
      .then((data) => setBalance(data.balance))
      .catch(() => toast.error('Failed to load balance'));
  }, [messages]);

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'w-64' : 'w-0'
        } transition-all duration-300 bg-muted border-r flex flex-col overflow-hidden`}
      >
        <div className="p-4 border-b">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Chat History</h2>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 hover:bg-background rounded"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <button
            onClick={() => {
              setCurrentChatId(null);
              window.location.reload();
            }}
            className="w-full px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
          >
            + New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {chatHistories.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No chat history yet
            </p>
          ) : (
            <div className="space-y-2">
              {chatHistories.map((chat: any) => (
                <button
                  key={chat.id}
                  onClick={() => setCurrentChatId(chat.id)}
                  className={`w-full text-left px-3 py-2 rounded text-sm hover:bg-background ${
                    currentChatId === chat.id ? 'bg-background' : ''
                  }`}
                >
                  <div className="font-medium truncate">{chat.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {chat.messageCount}/50 messages
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t text-sm text-muted-foreground">
          <div className="mb-2">Max 10 threads</div>
          <div>50 messages per thread</div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-muted rounded lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="text-xl font-bold">Smart Grant Finder</h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Credit Balance */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-full">
              <CreditCard className="h-4 w-4" />
              <span className="font-medium">
                {balance !== null ? `$${balance.toFixed(2)}` : '---'}
              </span>
            </div>

            {/* Settings Dropdown */}
            <div className="relative group">
              <button className="p-2 hover:bg-muted rounded">
                <Settings className="h-5 w-5" />
              </button>
              <div className="absolute right-0 mt-2 w-48 bg-card border rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                <a
                  href="/settings"
                  className="block px-4 py-2 hover:bg-muted"
                >
                  Settings
                </a>
                <a
                  href="/api/auth/signout"
                  className="block px-4 py-2 hover:bg-muted text-destructive flex items-center gap-2"
                >
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <h2 className="text-2xl font-bold mb-2">
                  Welcome to Smart Grant Finder
                </h2>
                <p className="text-muted-foreground mb-6">
                  Ask me to find grants, explain requirements, or help with applications.
                </p>
                <div className="grid grid-cols-1 gap-3 text-sm">
                  <button
                    onClick={() =>
                      handleInputChange({
                        target: {
                          value: 'Find grants for nonprofit organizations in NYC',
                        },
                      } as any)
                    }
                    className="px-4 py-3 border rounded-lg hover:bg-muted text-left"
                  >
                    💰 Find grants for my nonprofit
                  </button>
                  <button
                    onClick={() =>
                      handleInputChange({
                        target: {
                          value: 'What grants are available for research projects?',
                        },
                      } as any)
                    }
                    className="px-4 py-3 border rounded-lg hover:bg-muted text-left"
                  >
                    🔬 Research grants
                  </button>
                  <button
                    onClick={() =>
                      handleInputChange({
                        target: {
                          value: 'Help me apply to a grant',
                        },
                      } as any)
                    }
                    className="px-4 py-3 border rounded-lg hover:bg-muted text-left"
                  >
                    📝 Application assistance
                  </button>
                </div>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                </div>
              </div>
            ))
          )}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-lg px-4 py-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-foreground rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-foreground rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-foreground rounded-full animate-bounce delay-200" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t p-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              value={input}
              onChange={handleInputChange}
              placeholder="Ask about grants..."
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Send className="h-4 w-4" />
              Send
            </button>
          </form>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Powered by DeepSeek AI • {messages.length}/50 messages in this thread
          </p>
        </div>
      </div>
    </div>
  );
}
