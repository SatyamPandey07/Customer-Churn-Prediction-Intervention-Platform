import { cookies } from 'next/headers';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import RealtimeProvider from '@/components/RealtimeProvider';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = cookies();
  const role = cookieStore.get('user_role')?.value || 'viewer';

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 overflow-hidden font-sans transition-colors">
      <Sidebar userRole={role} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header userRole={role} />
        <main className="flex-1 overflow-y-auto bg-slate-50 dark:bg-slate-950 transition-colors">
          <RealtimeProvider>
            <div className="p-8 max-w-7xl mx-auto space-y-8">
              {children}
            </div>
          </RealtimeProvider>
        </main>
      </div>
    </div>
  );
}
