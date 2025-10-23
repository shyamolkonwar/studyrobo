'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import Sidebar from '@/components/sidebar';
import EmptyState from '@/components/empty-state';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

export default function Home() {
  const [user, setUser] = useState<any>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/auth/login');
        return;
      }
      setUser(session.user);
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
    if (user) {
      loadConversations();
    }
  }, [user]);

  const loadConversations = async () => {
    try {
      const session = await supabase.auth.getSession();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/conversations`, {
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setConversations(data);
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  const createNewChat = async (prompt?: string) => {
    try {
      setIsRedirecting(true);

      // Create new conversation
      const session = await supabase.auth.getSession();
      const title = prompt ? prompt.split(' ').slice(0, 5).join(' ') + '...' : 'New Chat';

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ title }),
      });

      if (response.ok) {
        const data = await response.json();

        // If there's a prompt, send the first message
        if (prompt) {
          // Navigate to chat and send message
          router.push(`/chat/${data.conversation_id}?message=${encodeURIComponent(prompt)}`);
        } else {
          // Just navigate to empty chat
          router.push(`/chat/${data.conversation_id}`);
        }
      }
    } catch (error) {
      console.error('Error creating conversation:', error);
      setIsRedirecting(false);
    }
  };

  const handlePromptSelect = (prompt: string) => {
    createNewChat(prompt);
  };

  // If we have conversations, redirect to the most recent one
  useEffect(() => {
    if (conversations.length > 0 && !isRedirecting) {
      router.push(`/chat/${conversations[0].id}`);
    }
  }, [conversations, router, isRedirecting]);

  if (!user || isRedirecting) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  // If we have conversations, show loading/redirecting state
  if (conversations.length > 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Opening your chat...</p>
        </Card>
      </div>
    );
  }

  // No conversations - show empty state
  return (
    <div className="flex h-screen">
      <Sidebar />
      <EmptyState onPromptSelect={handlePromptSelect} />
    </div>
  );
}