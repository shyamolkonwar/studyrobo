'use client';

import { usePathname } from 'next/navigation';
import DashboardSidebar from '@/components/dashboard-sidebar';
import Sidebar from '@/components/sidebar';

interface LayoutWrapperProps {
  children: React.ReactNode;
}

export default function LayoutWrapper({ children }: LayoutWrapperProps) {
  const pathname = usePathname();

  // Check if we're on a chat page
  const isChatPage = pathname.startsWith('/chat/');

  // Check if we're on the main dashboard
  const isDashboardPage = pathname === '/';

  return (
    <div className="flex h-screen">
      {/* Sidebar selection based on route */}
      {isChatPage ? (
        <Sidebar />
      ) : isDashboardPage ? (
        <DashboardSidebar />
      ) : (
        // Default to dashboard sidebar for other pages (like onboarding)
        <DashboardSidebar />
      )}

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        {children}
      </div>
    </div>
  );
}