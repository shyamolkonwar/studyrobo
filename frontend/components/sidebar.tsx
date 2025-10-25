'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

interface AppConnection {
  id: string;
  name: string;
  description: string;
  icon: string;
  connected: boolean;
  connecting: boolean;
}

export default function Sidebar({ currentConversationId }: { currentConversationId?: string }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [user, setUser] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [apps, setApps] = useState<AppConnection[]>([
    {
      id: 'gmail',
      name: 'Gmail',
      description: 'Access your emails and manage your inbox',
      icon: '📧',
      connected: false,
      connecting: false,
    },
  ]);
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user || null);
      if (session?.user) {
        loadConversations();
      } else {
        setIsLoading(false);
      }
    };

    checkUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user || null);
      if (session?.user) {
        loadConversations();
      } else {
        setConversations([]);
        setIsLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const loadConversations = async () => {
    try {
      setIsLoading(true);
      const { data: { session } } = await supabase.auth.getSession();
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
    } finally {
      setIsLoading(false);
    }
  };

  const createNewConversation = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ title: 'New Chat' }),
      });

      if (response.ok) {
        const data = await response.json();
        router.push(`/chat/${data.conversation_id}`);
      }
    } catch (error) {
      console.error('Error creating conversation:', error);
    }
  };

  const deleteConversation = async (conversationId: string) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
        },
      });

      if (response.ok) {
        setConversations(conversations.filter(conv => conv.id !== conversationId));
        if (currentConversationId === conversationId) {
          router.push('/');
        }
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const checkAppConnections = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      // Check Gmail connection
      const tokensResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google-tokens`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      setApps(prevApps =>
        prevApps.map(app => ({
          ...app,
          connected: app.id === 'gmail' ? tokensResponse.ok : app.connected,
        }))
      );
    } catch (error) {
      console.error('Error checking app connections:', error);
    }
  };

  const connectApp = async (appId: string) => {
    if (appId === 'gmail') {
      try {
        setApps(prevApps =>
          prevApps.map(app =>
            app.id === appId ? { ...app, connecting: true } : app
          )
        );

        // Use Supabase OAuth with Gmail scopes and offline access
        const { error } = await supabase.auth.signInWithOAuth({
          provider: 'google',
          options: {
            // Ask for the Gmail scopes
            scopes: 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose',
            // CRITICAL: Ask for offline access to get the Refresh Token
            queryParams: {
              access_type: 'offline',
              prompt: 'consent' // Forces Google to show the consent screen again
            }
          }
        });

        if (error) {
          alert('Failed to initiate Gmail connection. Please try again.');
          setApps(prevApps =>
            prevApps.map(app =>
              app.id === appId ? { ...app, connecting: false } : app
            )
          );
        }
        // Note: No need to handle success here - the auth state change listener will handle it
      } catch (error) {
        console.error('Error connecting Gmail:', error);
        alert('Failed to connect Gmail. Please try again.');
        setApps(prevApps =>
          prevApps.map(app =>
            app.id === appId ? { ...app, connecting: false } : app
          )
        );
      }
    }
  };

  if (!user) {
    return null;
  }

  return (
    <div className="w-64 h-full bg-card border-r border-border flex flex-col">
      <div className="p-4 border-b border-border space-y-2">
        <Button
          onClick={() => router.push('/')}
          className="w-full flex items-center gap-2"
          variant="outline"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Dashboard
        </Button>
        <Button
          onClick={createNewConversation}
          className="w-full flex items-center gap-2"
          variant="default"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Chat
        </Button>
        <Button
          onClick={() => router.push('/upload')}
          className="w-full flex items-center gap-2"
          variant="outline"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          Upload Resources
        </Button>
        <Button
          onClick={() => router.push('/attendance')}
          className="w-full flex items-center gap-2"
          variant="outline"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          Mark Attendance
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center text-muted-foreground">
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs mt-2">Start a new chat to begin</p>
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conversation) => (
              <Card
                key={conversation.id}
                className={`p-3 cursor-pointer transition-colors hover:bg-accent ${
                  currentConversationId === conversation.id ? 'bg-accent' : ''
                }`}
              >
                <div
                  className="group"
                  onClick={() => router.push(`/chat/${conversation.id}`)}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium truncate">
                        {conversation.title}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-muted-foreground">
                          {conversation.message_count || 0} messages
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(conversation.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConversation(conversation.id);
                      }}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div className="p-4 border-t border-border space-y-2">
        <Dialog>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={checkAppConnections}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              Connect Apps
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Connect Your Apps</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              {apps.map((app) => (
                <Card key={app.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{app.icon}</span>
                      <div>
                        <h3 className="font-medium">{app.name}</h3>
                        <p className="text-sm text-muted-foreground">{app.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {app.connected && (
                        <span className="text-sm text-green-600 font-medium">Connected</span>
                      )}
                      <Button
                        size="sm"
                        variant={app.connected ? "outline" : "default"}
                        disabled={app.connecting}
                        onClick={() => connectApp(app.id)}
                      >
                        {app.connecting ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                            Connecting...
                          </>
                        ) : app.connected ? (
                          'Reconnect'
                        ) : (
                          'Connect'
                        )}
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </DialogContent>
        </Dialog>

        <Button
          variant="outline"
          size="sm"
          onClick={() => supabase.auth.signOut()}
          className="w-full"
        >
          Logout
        </Button>
      </div>
    </div>
  );
}
