'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import LayoutWrapper from '@/components/layout-wrapper';
import DashboardWidgets from '@/components/dashboard-widgets';


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

      // Check if user has completed onboarding
      try {
        const { data: userData, error } = await supabase
          .from('users')
          .select('onboarding_completed')
          .eq('google_id', session.user.id)
          .single();

        if (!userData?.onboarding_completed) {
          router.push('/onboarding');
          return;
        }
      } catch (error) {
        console.error('Error checking onboarding status:', error);
        router.push('/onboarding');
        return;
      }

      setUser(session.user);
    };

    checkUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (!session) {
        router.push('/auth/login');
      } else {
        // Check onboarding status on auth state change
        supabase
          .from('users')
          .select('onboarding_completed')
          .eq('google_id', session.user.id)
          .single()
          .then(({ data: userData }) => {
            if (!userData?.onboarding_completed) {
              router.push('/onboarding');
            } else {
              setUser(session.user);
            }
          });
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
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/conversations`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
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
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        setIsRedirecting(false);
        return;
      }

      const title = prompt ? prompt.split(' ').slice(0, 5).join(' ') + '...' : 'New Chat';

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
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

  if (!user || isRedirecting) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Show professional dashboard
  return (
    <LayoutWrapper>
      <div className="container mx-auto p-6">
        <div className="mb-8 animate-fade-in">
          <div className="mb-2">
            <h1 className="text-4xl font-bold font-heading text-foreground">
              Welcome back, {user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Student'}!
            </h1>
            <p className="text-lg text-muted-foreground font-body">
              Here's your personalized learning dashboard
            </p>
          </div>
        </div>
        <DashboardWidgets />
      </div>
    </LayoutWrapper>
  );
}
