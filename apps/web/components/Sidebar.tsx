"use client";

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LayoutDashboard, Megaphone, BarChart3, LogOut, Sparkles, ShieldCheck, Zap } from 'lucide-react';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Campaigns', href: '/dashboard/campaigns', icon: Megaphone },
  { name: 'Analytics', href: '/dashboard/analytics', icon: BarChart3 },
];

export default function Sidebar({ userRole }: { userRole: string }) {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    router.push('/login');
  };

  return (
    <aside className="flex flex-col w-64 bg-slate-950 border-r border-slate-800/80 text-slate-100 min-h-screen select-none">
      {/* Brand Logo */}
      <div className="p-6 border-b border-slate-900">
        <Link href="/dashboard" className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-extrabold tracking-tight text-white font-serif">
              Churn<span className="text-blue-500 font-sans">AI</span>
            </h1>
            <div className="text-[10px] text-slate-400 font-mono">ENTERPRISE SAAS</div>
          </div>
        </Link>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-4 py-6 space-y-1.5">
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-3 mb-2">
          Platform Core
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 ${
                isActive
                  ? 'bg-blue-600/15 border border-blue-500/30 text-blue-400 shadow-sm'
                  : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                <span>{item.name}</span>
              </div>
              {isActive && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />}
            </Link>
          );
        })}
      </nav>

      {/* Active Role Indicator Card */}
      <div className="p-4 m-4 bg-slate-900/80 border border-slate-800 rounded-xl">
        <div className="flex items-center space-x-2 text-xs text-slate-300 font-medium mb-1">
          <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
          <span>Tenant Role</span>
        </div>
        <div className="text-xs text-slate-400 font-mono capitalize">
          {userRole} Mode
        </div>
      </div>

      {/* Footer / Sign out */}
      <div className="p-4 border-t border-slate-900">
        <button
          onClick={handleLogout}
          className="flex items-center space-x-3 px-3 py-2 w-full rounded-lg text-xs font-medium text-slate-400 hover:bg-red-500/10 hover:text-red-400 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
