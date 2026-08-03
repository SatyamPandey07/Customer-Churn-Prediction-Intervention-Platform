"use client";

import { useState } from 'react';
import { Search, Bell, Sun, Moon, LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useTheme } from './ThemeProvider';

export default function Header({ userRole }: { userRole: string }) {
  const [showNotifications, setShowNotifications] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    router.push('/login');
  };

  const getRoleBadge = (role: string) => {
    switch (role.toLowerCase()) {
      case 'owner':
      case 'admin':
        return 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/30';
      case 'analyst':
        return 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/30';
      default:
        return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
    }
  };

  return (
    <header className="h-16 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800/80 px-8 flex items-center justify-between sticky top-0 z-30 transition-colors duration-300 shadow-xs">
      {/* Search Input */}
      <div className="flex items-center space-x-3 w-96">
        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search customers, campaigns, or MRR..."
            className="w-full bg-slate-100/80 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 rounded-xl pl-9 pr-4 py-1.5 text-xs text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all"
          />
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-3">
        {/* Sun/Moon Theme Toggle Switch */}
        <button
          onClick={toggleTheme}
          className="p-2 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-all flex items-center space-x-2 border border-slate-200 dark:border-slate-800 text-xs font-bold shadow-xs"
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? (
            <>
              <Moon className="w-4 h-4 text-indigo-600" />
              <span className="hidden sm:inline text-indigo-950 font-bold">Dark Mode</span>
            </>
          ) : (
            <>
              <Sun className="w-4 h-4 text-amber-400" />
              <span className="hidden sm:inline text-amber-300 font-bold">Light Mode</span>
            </>
          )}
        </button>

        {/* Live System Health Badge */}
        <div className="hidden sm:flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 rounded-full text-xs font-bold text-emerald-700 dark:text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
          <span>Realtime Ingestion Active</span>
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors relative border border-slate-200 dark:border-slate-800"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-blue-500 rounded-full" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl p-4 z-50">
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs font-bold text-slate-900 dark:text-slate-200 uppercase tracking-wider">System Alerts</span>
                <span className="text-[10px] text-blue-700 dark:text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded font-bold">2 New</span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="p-2.5 bg-slate-50 dark:bg-slate-950/80 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                  <div className="font-bold text-slate-900 dark:text-slate-200">Critical Risk Triggered</div>
                  <div className="text-slate-500 dark:text-slate-400 text-[11px]">Customer cus_8f93a210 reached 89% churn probability.</div>
                </div>
                <div className="p-2.5 bg-slate-50 dark:bg-slate-950/80 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                  <div className="font-bold text-slate-900 dark:text-slate-200">Campaign Executed</div>
                  <div className="text-slate-500 dark:text-slate-400 text-[11px]">Executive Save Offer email sent to 12 target recipients.</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* User Role Badge */}
        <div className={`px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase tracking-wider border ${getRoleBadge(userRole)}`}>
          {userRole}
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="flex items-center space-x-1.5 text-xs text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl"
          title="Sign Out"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
}
