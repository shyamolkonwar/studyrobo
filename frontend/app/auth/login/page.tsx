'use client';

import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function LoginPage() {
  const handleGoogleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        scopes: 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/spreadsheets'
      }
    });
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <Card className="p-8 max-w-md w-full">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-4">Welcome to StudyRobo</h1>
          <p className="text-muted-foreground mb-8">Your AI-powered study assistant</p>
          <Button onClick={handleGoogleLogin} size="lg" className="w-full">
            Login with Google
          </Button>
        </div>
      </Card>
    </div>
  );
}
