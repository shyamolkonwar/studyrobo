'use client';

import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsGoogleAuth, setNeedsGoogleAuth] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Check if user is coming back from successful Google OAuth
    const authSuccess = searchParams.get('auth_success');
    if (authSuccess === 'true') {
      router.push('/');
      return;
    }

    // Check current session
    const checkSession = async () => {
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (session && !sessionError) {
        // User is authenticated with Supabase
        setLoading(true);
        setError(null);

        try {
          // Sync user with our database
          const syncResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/sync-user`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${session.access_token}`,
            },
          });

          if (syncResponse.ok) {
            // Check if user needs to connect Google account for Gmail access
            const tokensResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google-tokens`, {
              method: 'GET',
              headers: {
                'Authorization': `Bearer ${session.access_token}`,
              },
            });

            if (tokensResponse.status === 404) {
              // User needs to connect Google account for Gmail access
              setNeedsGoogleAuth(true);
              setLoading(false);
              return;
            } else if (tokensResponse.ok) {
              // User has Gmail access, redirect to main app
              router.push('/');
              return;
            }
          }

          // User is fully authenticated, redirect to main app
          router.push('/');

        } catch (err) {
          console.error('Error checking session:', err);
          setError('Authentication completed. Click below to connect Google services.');
          setNeedsGoogleAuth(true);
        } finally {
          if (!needsGoogleAuth) {
            setLoading(false);
          }
        }
      }
    };

    checkSession();
  }, [router, searchParams, needsGoogleAuth]);

  const handleSupabaseLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          // NO scopes here - just basic authentication
          redirectTo: `${window.location.origin}/auth/login`,
        }
      });

      if (error) {
        setError(error.message);
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to initiate login');
      console.error('Login error:', err);
      setLoading(false);
    }
  };

  const handleGoogleServicesConnect = async () => {
    setLoading(true);
    setError(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        setError('Please log in first');
        setLoading(false);
        return;
      }

      // Get Google OAuth URL for services
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google-auth-url`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const { auth_url } = await response.json();
        window.location.href = auth_url;
      } else {
        setError('Failed to generate Google services authorization URL');
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to connect Google services');
      console.error('Google services connection error:', err);
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <Card className="p-8 max-w-md w-full">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-4">Welcome to StudyRobo</h1>
          <p className="text-muted-foreground mb-8">Your AI-powered study assistant</p>

          {error && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-sm text-yellow-800">{error}</p>
            </div>
          )}

          {!needsGoogleAuth ? (
            <Button
              onClick={handleSupabaseLogin}
              size="lg"
              className="w-full"
              disabled={loading}
            >
              {loading ? 'Connecting...' : 'Login with Google'}
            </Button>
          ) : (
            <div className="space-y-4">
              <div className="p-4 bg-green-50 border border-green-200 rounded-md">
                <p className="text-sm text-green-800 mb-2">✓ Successfully logged in</p>
                <p className="text-xs text-green-700">Connect Google services to enable email and spreadsheet features</p>
              </div>

              <Button
                onClick={handleGoogleServicesConnect}
                size="lg"
                className="w-full"
                disabled={loading}
              >
                {loading ? 'Connecting...' : 'Connect Gmail & Google Sheets'}
              </Button>
            </div>
          )}

          <p className="mt-4 text-xs text-muted-foreground">
            By connecting your account, you agree to allow access to Gmail and Google Sheets for AI assistance.
          </p>
        </div>
      </Card>
    </div>
  );
}
