import { cookies } from 'next/headers';
import Sidebar from '@/components/Sidebar';
import RealtimeProvider from '@/components/RealtimeProvider';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = cookies();
  const role = cookieStore.get('user_role')?.value || 'viewer';

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar userRole={role} />
      <main className="flex-1 overflow-y-auto">
        <RealtimeProvider>
          <div className="p-8 max-w-7xl mx-auto">
            {children}
          </div>
        </RealtimeProvider>
      </main>
    </div>
  );
}
