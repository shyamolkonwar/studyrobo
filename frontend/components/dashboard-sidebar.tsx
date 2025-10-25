'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import {
  MessageSquare,
  Home,
  BookOpen,
  CheckCircle,
  Flame,
  Link,
  LogOut,
  User,
  Loader2
} from 'lucide-react';

interface AppConnection {
  id: string;
  name: string;
  description: string;
  icon: string;
  connected: boolean;
  connecting: boolean;
}

interface UserStats {
  totalDocuments: number;
  attendancePercentage: number;
  studyStreak: number;
}

export default function DashboardSidebar() {
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
    {
      id: 'calendar',
      name: 'Google Calendar',
      description: 'View your schedule and upcoming events',
      icon: '📅',
      connected: false,
      connecting: false,
    },
  ]);
  const [userStats, setUserStats] = useState<UserStats>({
    totalDocuments: 0,
    attendancePercentage: 0,
    studyStreak: 0,
  });
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user || null);
      if (session?.user) {
        loadUserStats();
        checkAppConnections();
      } else {
        setIsLoading(false);
      }
    };

    checkUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user || null);
      if (session?.user) {
        loadUserStats();
        checkAppConnections();
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const loadUserStats = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      // Load user documents count
      const docsResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/user`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (docsResponse.ok) {
        const documents = await docsResponse.json();
        const totalDocuments = documents?.length || 0;

        // Load attendance stats
        const attendanceResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/attendance/stats`, {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        });

        let attendancePercentage = 0;
        if (attendanceResponse.ok) {
          const attendanceData = await attendanceResponse.json();
          attendancePercentage = attendanceData?.percentage || 0;
        }

        setUserStats({
          totalDocuments,
          attendancePercentage,
          studyStreak: Math.floor(Math.random() * 10) + 1, // Mock data for now
        });
      }
    } catch (error) {
      console.error('Error loading user stats:', error);
    } finally {
      setIsLoading(false);
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

        const { error } = await supabase.auth.signInWithOAuth({
          provider: 'google',
          options: {
            scopes: 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose',
            queryParams: {
              access_type: 'offline',
              prompt: 'consent'
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

  const createNewChat = async () => {
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

  if (!user) {
    return null;
  }

  return (
    <div className="w-64 h-full bg-card border-r border-border flex flex-col">
      {/* User Profile Section */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-brand-blue rounded-full flex items-center justify-center text-white font-semibold font-heading animate-fade-in">
            {user?.user_metadata?.full_name?.[0] || user?.email?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold font-heading truncate text-foreground">
              {user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User'}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              {user?.email}
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="p-4 border-b border-border space-y-2">
        <Button
          onClick={createNewChat}
          className="w-full flex items-center gap-2"
          variant="brand"
          size="lg"
        >
          <MessageSquare className="w-4 h-4" />
          Start Chat
        </Button>

        <Button
          onClick={() => router.push('/')}
          className="w-full flex items-center gap-2"
          variant="outline"
          size="lg"
        >
          <Home className="w-4 h-4" />
          Dashboard
        </Button>
      </div>

      {/* User Stats */}
      <div className="p-4 border-b border-border">
        <h3 className="text-sm font-semibold font-heading mb-3">Your Progress</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <BookOpen className="w-4 h-4 text-brand-violet" />
              <span className="text-sm font-body">Documents</span>
            </div>
            <Badge variant="secondary" className="font-semibold">{userStats.totalDocuments}</Badge>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-4 h-4 text-brand-green" />
              <span className="text-sm font-body">Attendance</span>
            </div>
            <Badge
              variant={userStats.attendancePercentage >= 80 ? "default" : "secondary"}
              className={userStats.attendancePercentage >= 80 ? "bg-brand-green" : ""}
            >
              {userStats.attendancePercentage}%
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Flame className="w-4 h-4 text-brand-yellow" />
              <span className="text-sm font-body">Study Streak</span>
            </div>
            <Badge variant="secondary" className="font-semibold">{userStats.studyStreak} days</Badge>
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-sm font-semibold font-heading mb-3">Quick Links</h3>
        <div className="space-y-2">
          <Button
            variant="ghost"
            className="w-full justify-start hover:bg-brand-violet/10"
            onClick={() => {
              const element = document.getElementById('library-widget');
              element?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            <BookOpen className="w-4 h-4 mr-2" />
            <span className="font-body">My Library</span>
          </Button>

          <Button
            variant="ghost"
            className="w-full justify-start hover:bg-brand-green/10"
            onClick={() => {
              const element = document.getElementById('attendance-widget');
              element?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            <CheckCircle className="w-4 h-4 mr-2" />
            <span className="font-body">Attendance</span>
          </Button>

          <Button
            variant="ghost"
            className="w-full justify-start hover:bg-brand-blue/10"
            onClick={() => {
              const element = document.getElementById('apps-widget');
              element?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            <Link className="w-4 h-4 mr-2" />
            <span className="font-body">Connected Apps</span>
          </Button>
        </div>
      </div>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-border space-y-2">
        <Dialog>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={checkAppConnections}
            >
              <Link className="w-4 h-4 mr-2" />
              Connect Apps
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="font-heading">Connect Your Apps</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              {apps.map((app) => (
                <Card key={app.id} className="p-4 animate-fade-in">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{app.icon}</span>
                      <div>
                        <h3 className="font-medium font-heading">{app.name}</h3>
                        <p className="text-sm text-muted-foreground font-body">{app.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {app.connected && (
                        <span className="text-sm text-brand-green font-medium font-body">Connected</span>
                      )}
                      <Button
                        size="sm"
                        variant={app.connected ? "outline" : "brand"}
                        disabled={app.connecting}
                        onClick={() => connectApp(app.id)}
                      >
                        {app.connecting ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
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
          className="w-full hover:bg-brand-red/10"
        >
          <LogOut className="w-4 h-4 mr-2" />
          <span className="font-body">Logout</span>
        </Button>
      </div>
    </div>
  );
}