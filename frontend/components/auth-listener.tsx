'use client';

import { useEffect } from 'react';
import { supabase } from '@/lib/supabase';

export default function AuthListener() {
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        // Check if this is the 'SIGNED_IN' event after our OAuth flow
        if (event === 'SIGNED_IN' && session?.provider_refresh_token) {
          // WE GOT IT!
          const refreshToken = session.provider_refresh_token;

          // Don't let this token sit in the client.
          // Immediately send it to your secure Edge Function.
          try {
            const { error } = await supabase.functions.invoke(
              'save-google-token',
              {
                body: {
                  app_name: 'gmail',
                  refresh_token: refreshToken
                }
              }
            );

            if (error) {
              console.error('Failed to save Gmail connection:', error);
              alert('Failed to save Gmail connection. Please try again.');
            } else {
              console.log("Gmail connected successfully!");
              alert('Gmail connected successfully!');
            }

          } catch (error) {
            console.error("Failed to save Gmail connection:", error);
            alert('Failed to save Gmail connection. Please try again.');
          }
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  return null; // This component doesn't render anything
}
