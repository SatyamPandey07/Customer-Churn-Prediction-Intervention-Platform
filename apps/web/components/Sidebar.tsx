"use client";

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { 
  LayoutDashboard, Megaphone, BarChart3, Plug, LogOut, 
  ShieldCheck, Zap, ShieldAlert, Settings, X
} from 'lucide-react';

import { useTenantBranding } from '@/components/TenantBrandingProvider';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Campaigns', href: '/dashboard/campaigns', icon: Megaphone },
  { name: 'Analytics', href: '/dashboard/analytics', icon: BarChart3 },
  { name: 'Integrations', href: '/dashboard/integrations', icon: Plug },
  { name: 'Audit Logs', href: '/dashboard/audit', icon: ShieldAlert },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export default function Sidebar({ userRole, isOpen, setIsOpen }: { userRole: string, isOpen: boolean, setIsOpen: (val: boolean) => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { branding } = useTenantBranding();

  const handleLogout = () => {
    // Clear auth cookies client-side
    document.cookie = 'access_token=; path=/; max-age=0; SameSite=Strict';
    document.cookie = 'user_role=; path=/; max-age=0; SameSite=Strict';
    router.push('/login');
  };

  return (
    <>
      {/* Mobile Drawer Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-slate-950/50 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside className={`fixed md:static inset-y-0 left-0 z-50 flex flex-col bg-white/90 dark:bg-slate-900/90 border-r border-slate-200/90 dark:border-slate-800/80 text-slate-800 dark:text-slate-100 h-[100dvh] md:h-auto md:min-h-screen select-none transition-all duration-300 backdrop-blur-md shadow-xl md:shadow-sm w-64 md:w-20 lg:w-64 transform ${isOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}>
        {/* Brand Logo */}
        <div className="p-4 lg:p-6 border-b border-slate-200/60 dark:border-slate-800/60 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center space-x-3 overflow-hidden">
            {branding?.logo_url ? (
              <img src={branding.logo_url} alt="Logo" className="w-9 h-9 object-contain" />
            ) : (
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-tenant-primary to-tenant-secondary flex items-center justify-center shadow-md shadow-blue-500/20 flex-shrink-0">
                <ShieldCheck className="w-5 h-5 text-white" />
              </div>
            )}
            <div className="md:hidden lg:block">
              <h1 className="text-xl font-black tracking-tight text-slate-900 dark:text-white leading-none whitespace-nowrap">
                {branding?.product_display_name ? (
                  <span className="font-sans">{branding.product_display_name}</span>
                ) : (
                  <>ChurnGuard<span className="text-tenant-primary font-sans">.AI</span></>
                )}
              </h1>
            </div>
          </Link>
          <button onClick={() => setIsOpen(false)} className="md:hidden p-1 text-slate-400 hover:text-slate-900 dark:hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto overflow-x-hidden">
        <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest px-3 mb-3 md:hidden lg:block">
          Platform Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={() => setIsOpen(false)}
              className={`flex items-center md:justify-center lg:justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 ${
                isActive
                  ? 'bg-blue-600/10 border border-blue-500/30 text-blue-700 dark:text-blue-400 shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-100 border border-transparent'
              }`}
              title={item.name}
            >
              <div className="flex items-center space-x-3">
                <Icon className={`w-5 h-5 md:w-6 md:h-6 lg:w-4 lg:h-4 ${isActive ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400'}`} />
                <span className="md:hidden lg:block">{item.name}</span>
              </div>
              {isActive && <span className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-blue-400 animate-pulse md:hidden lg:block" />}
            </Link>
          );
        })}
      </nav>

      {/* Active Role Indicator Card */}
      <div className="p-4 mx-4 mb-4 bg-slate-50 dark:bg-slate-950/80 border border-slate-200/80 dark:border-slate-800/80 rounded-2xl shadow-xs md:hidden lg:block">
        <div className="flex items-center space-x-2 text-xs text-slate-800 dark:text-slate-200 font-bold mb-1">
          <ShieldCheck className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <span>Active Role</span>
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400 font-mono capitalize">
          {userRole} Mode
        </div>
      </div>

      {/* Footer / Sign out */}
      <div className="p-4 border-t border-slate-200/60 dark:border-slate-800/60 flex justify-center">
        <button
          onClick={handleLogout}
          className="flex items-center md:justify-center lg:justify-start space-x-3 px-3 py-2.5 w-full rounded-xl text-xs font-semibold text-slate-500 dark:text-slate-400 hover:bg-red-500/10 hover:text-red-600 dark:hover:text-red-400 transition-colors"
          title="Sign Out"
        >
          <LogOut className="w-5 h-5 md:w-6 md:h-6 lg:w-4 lg:h-4 flex-shrink-0" />
          <span className="md:hidden lg:inline">Sign Out</span>
        </button>
      </div>
    </aside>
    </>
  );
}
