'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import LayoutWrapper from '@/components/layout-wrapper';
import Sidebar from '@/components/sidebar';

interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  created_at: string;
}

interface LoadingIndicator {
  type: 'gmail' | 'search' | 'general';
  message: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingIndicators, setLoadingIndicators] = useState<LoadingIndicator[]>([]);
  const [user, setUser] = useState<any>(null);
  const [conversation, setConversation] = useState<any>(null);

  const params = useParams();
  const router = useRouter();
  const conversationId = params.id as string;

  // Check for initial message from URL
  useEffect(() => {
    if (typeof window !== 'undefined' && conversationId) {
      const urlParams = new URLSearchParams(window.location.search);
      const initialMessage = urlParams.get('message');

      if (initialMessage && messages.length === 0 && !isLoading) {
        // Auto-send the initial message
        setTimeout(() => {
          const form = document.querySelector('form');
          if (form) {
            const input = form.querySelector('input[type="text"]') as HTMLInputElement;
            if (input) {
              input.value = decodeURIComponent(initialMessage);
              const submitEvent = new Event('submit', { cancelable: true });
              form.dispatchEvent(submitEvent);
            }
          }
        }, 500);
      }
    }
  }, [conversationId, messages.length, isLoading]);

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/auth/login');
        return;
      }
      setUser(session.user);

      // Check if user has Gmail access
      try {
        const tokensResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google-tokens`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        });

        if (tokensResponse.status === 404) {
          // User needs Gmail OAuth - redirect to login for Gmail setup
          alert('Gmail access required. Please connect your Gmail account.');
          router.push('/auth/login');
          return;
        }
      } catch (error) {
        console.error('Error checking Gmail tokens:', error);
      }
    };

    checkUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (!session) {
        router.push('/auth/login');
      } else {
        setUser(session.user);
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  useEffect(() => {
    if (user && conversationId) {
      loadMessages();
    }
  }, [user, conversationId]);

  const loadMessages = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/conversations/${conversationId}/messages`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(data || []);
      }
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const addLoadingIndicator = (type: LoadingIndicator['type'], message: string) => {
    setLoadingIndicators(prev => [...prev, { type, message }]);
  };

  const removeLoadingIndicator = (type: LoadingIndicator['type']) => {
    setLoadingIndicators(prev => prev.filter(ind => ind.type !== type));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || !user) return;

    // Get session
    const { data: { session }, error } = await supabase.auth.refreshSession();
    if (!session || error) {
      alert("Session expired. Please log in again.");
      router.push('/auth/login');
      return;
    }

    // Add user message to local state
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputText,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      // Send to backend (tokens are now retrieved from secure database storage)
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          message: inputText,
          conversation_id: conversationId
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const data = await response.json();

      // Process AI response with formatting
      await processAIResponse(data.reply);

    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: 'Sorry, something went wrong. Please try again.',
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setLoadingIndicators([]);
    }
  };

  const processAIResponse = async (response: string) => {
    // Parse the response for any special formatting
    let processedResponse = response;

    // Check if response contains email data or other structured data
    if (response.includes('📧') || response.includes('EMAILS:')) {
      addLoadingIndicator('gmail', 'Checking your emails...');

      // Simulate processing time
      setTimeout(() => {
        removeLoadingIndicator('gmail');
        addFormattedMessage(processedResponse, 'emails');
      }, 1000);
    } else if (response.includes('🔍') || response.includes('SEARCH RESULTS:')) {
      addLoadingIndicator('search', 'Searching for resources...');

      setTimeout(() => {
        removeLoadingIndicator('search');
        addFormattedMessage(processedResponse, 'resources');
      }, 1500);
    } else {
      addLoadingIndicator('general', 'Thinking...');

      setTimeout(() => {
        removeLoadingIndicator('general');
        addFormattedMessage(processedResponse, 'text');
      }, 800);
    }
  };

  const addFormattedMessage = (content: string, type: 'text' | 'emails' | 'resources') => {
    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'ai',
      content: content,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, aiMessage]);
  };

  const formatEmailContent = (content: string) => {
    // Parse and format email content into cards
    const emailLines = content.split('\n');
    const emails = [];

    let currentEmail = null;

    for (const line of emailLines) {
      if (line.startsWith('From:')) {
        if (currentEmail) emails.push(currentEmail);
        currentEmail = { from: line.replace('From:', '').trim(), subject: '', body: '' };
      } else if (line.startsWith('Subject:') && currentEmail) {
        currentEmail.subject = line.replace('Subject:', '').trim();
      } else if (currentEmail && line.trim()) {
        currentEmail.body += line + '\n';
      }
    }

    if (currentEmail) emails.push(currentEmail);

    return (
      <div className="space-y-3">
        {emails.map((email, index) => (
          <Card key={index} className="p-4 border border-border">
            <div className="flex justify-between items-start mb-2">
              <span className="font-medium text-sm">{email.from}</span>
              <span className="text-xs text-muted-foreground">
                {new Date().toLocaleDateString()}
              </span>
            </div>
            <h4 className="font-medium mb-2">{email.subject}</h4>
            <p className="text-sm text-muted-foreground">{email.body}</p>
          </Card>
        ))}
      </div>
    );
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <LayoutWrapper>
      <div className="flex flex-col h-full">
        <header className="border-b border-border bg-card p-4">
          <h1 className="text-xl font-semibold truncate">
            {conversation?.title || 'Chat'}
          </h1>
        </header>

        <main className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <Card className="p-8 max-w-2xl w-full text-center">
                <h2 className="text-xl font-semibold mb-4">
                  Start a conversation
                </h2>
                <p className="text-muted-foreground">
                  Ask me anything about your studies, or choose from the suggestions on the main page.
                </p>
              </Card>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <Card
                    className={`max-w-[70%] p-4 ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-card'
                    }`}
                  >
                    {message.content.includes('📧') && message.role === 'ai' ? (
                      formatEmailContent(message.content)
                    ) : (
                      <div className="prose prose-sm max-w-none">
                        {message.content.split('\n').map((paragraph, index) => (
                          <p key={index} className="mb-2 last:mb-0">
                            {paragraph}
                          </p>
                        ))}
                      </div>
                    )}
                  </Card>
                </div>
              ))}

              {/* Loading Indicators */}
              {loadingIndicators.map((indicator, index) => (
                <div key={index} className="flex justify-start">
                  <Card className="p-4 bg-card">
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                      <span className="text-sm text-muted-foreground">
                        {indicator.message}
                      </span>
                    </div>
                  </Card>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <Card className="p-4 bg-card">
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                      <span className="text-sm text-muted-foreground">Thinking...</span>
                    </div>
                  </Card>
                </div>
              )}
            </div>
          )}
        </main>

        <footer className="border-t border-border bg-card p-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type your message..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={isLoading || !inputText.trim()}
            >
              Send
            </Button>
          </form>
        </footer>
      </div>
    </LayoutWrapper>
  );
}
