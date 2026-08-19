"use client";

import { useState, useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import RealtimeProvider from '@/components/RealtimeProvider';

export default function DashboardClientLayout({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState('admin');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    // Client-side auth guard (works in static export on Netlify)
    const tokenMatch = document.cookie.match(/(?:^|;\s*)access_token=([^;]*)/);
    if (!tokenMatch || !tokenMatch[1]) {
      window.location.replace('/login/');
      return;
    }
    // Read role from cookie
    const roleMatch = document.cookie.match(/(?:^|;\s*)user_role=([^;]*)/);
    if (roleMatch) setRole(decodeURIComponent(roleMatch[1]));
  }, []);

  return (
    <div className="flex h-screen bg-slate-100/70 dark:bg-slate-950 text-slate-900 dark:text-slate-100 overflow-hidden font-sans transition-colors duration-300 relative">
      <Sidebar userRole={role} isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header userRole={role} onMenuClick={() => setIsSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto bg-gradient-to-br from-slate-100/90 via-zinc-100/50 to-slate-100/90 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 transition-colors duration-300">
          <RealtimeProvider>
            <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6 md:space-y-8">
              {children}
            </div>
          </RealtimeProvider>
        </main>
      </div>
    </div>
  );
}
