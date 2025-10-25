'use client';

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function AuthSuccessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const userId = searchParams.get('user_id');
    if (userId) {
      localStorage.setItem('userId', userId);
      router.push('/');
    } else {
      router.push('/');
    }
  }, [searchParams, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">Login Successful!</h1>
        <p>Redirecting to chat...</p>
      </div>
    </div>
  );
}

export default function AuthSuccess() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Login Successful!</h1>
          <p>Loading...</p>
        </div>
      </div>
    }>
      <AuthSuccessContent />
    </Suspense>
  );
}
