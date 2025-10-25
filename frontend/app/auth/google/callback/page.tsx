'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { supabase } from '@/lib/supabase';

export default function GoogleCallbackPage() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const handleCallback = async () => {
      try {
        console.log('Google OAuth callback started');
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        console.log('Callback params:', { code: code?.substring(0, 20) + '...', state, error });

        if (error) {
          setStatus('error');
          setMessage(`OAuth error: ${error}`);
          return;
        }

        if (!code || !state) {
          setStatus('error');
          setMessage('Missing authorization code or state parameter');
          return;
        }

        // Get current session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        console.log('Session check:', { hasSession: !!session, sessionError });

        if (!session) {
          setStatus('error');
          setMessage('No active session found. Please log in first.');
          setTimeout(() => router.push('/auth/login'), 3000);
          return;
        }

        console.log('Exchanging code for tokens...');
        // Exchange code for tokens via backend
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google-callback?code=${code}&state=${state}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        });

        console.log('Token exchange response:', { ok: response.ok, status: response.status });

        if (response.ok) {
          const data = await response.json();
          console.log('Token exchange successful:', data);

          // Store tokens in backend
          console.log('Storing tokens...');
          const storeResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google-tokens`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${session.access_token}`,
            },
            body: JSON.stringify(data),
          });

          console.log('Token storage response:', { ok: storeResponse.ok, status: storeResponse.status });

          if (storeResponse.ok) {
            setStatus('success');
            setMessage('Google services connected successfully!');

            // Redirect to main app after a short delay
            setTimeout(() => {
              router.push('/');
            }, 2000);
          } else {
            const storeError = await storeResponse.text();
            console.error('Token storage failed:', storeError);
            setStatus('error');
            setMessage('Failed to store Google tokens');
          }
        } else {
          const errorData = await response.text();
          console.error('Token exchange failed:', errorData);
          setStatus('error');
          setMessage(`Failed to exchange code for tokens: ${errorData}`);
        }

      } catch (err) {
        console.error('Callback error:', err);
        setStatus('error');
        setMessage(`An unexpected error occurred: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    };

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="p-8 max-w-md w-full text-center">
        <h1 className="text-2xl font-bold mb-4">Connecting Google Services</h1>

        {status === 'loading' && (
          <div className="space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="text-muted-foreground">Processing your Google authorization...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4">
            <div className="text-green-600 text-4xl">✓</div>
            <p className="text-green-800 font-medium">{message}</p>
            <p className="text-sm text-muted-foreground">Redirecting to StudyRobo...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4">
            <div className="text-red-600 text-4xl">✗</div>
            <p className="text-red-800 font-medium">Connection Failed</p>
            <p className="text-sm text-muted-foreground">{message}</p>
            <button
              onClick={() => router.push('/auth/login')}
              className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
