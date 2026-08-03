"use client";

import { useState } from 'react';
import { Search, Bell, Shield, User, LogOut, ExternalLink, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function Header({ userRole }: { userRole: string }) {
  const [showNotifications, setShowNotifications] = useState(false);
  const router = useRouter();

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    router.push('/login');
  };

  const getRoleBadge = (role: string) => {
    switch (role.toLowerCase()) {
      case 'owner':
      case 'admin':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'analyst':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    }
  };

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur-md border-b border-slate-800/80 px-8 flex items-center justify-between sticky top-0 z-30">
      {/* Search Input */}
      <div className="flex items-center space-x-3 w-96">
        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search customers, campaigns, or MRR..."
            className="w-full bg-slate-950/60 border border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-4">
        {/* Live System Health Badge */}
        <div className="hidden sm:flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full text-xs font-medium text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
          <span>Realtime Ingestion Active</span>
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors relative"
          >
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-blue-500 rounded-full" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-4 z-50">
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">System Alerts</span>
                <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">2 New</span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="p-2 bg-slate-950/80 rounded border border-slate-800 text-slate-300">
                  <div className="font-semibold text-slate-200">Critical Risk Triggered</div>
                  <div className="text-slate-400 text-[11px]">Customer cus_8f93a210 reached 89% churn probability.</div>
                </div>
                <div className="p-2 bg-slate-950/80 rounded border border-slate-800 text-slate-300">
                  <div className="font-semibold text-slate-200">Campaign Executed</div>
                  <div className="text-slate-400 text-[11px]">Executive Save Offer email sent to 12 target recipients.</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* User Role Badge */}
        <div className={`px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wider border ${getRoleBadge(userRole)}`}>
          {userRole}
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-red-400 transition-colors p-2 hover:bg-slate-800/60 rounded-lg"
          title="Sign Out"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
}
