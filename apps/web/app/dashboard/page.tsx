import { MOCK_CUSTOMERS } from '@/lib/demoData';
import ClientDashboard from './ClientDashboard';

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900">Churn Risk Dashboard</h1>
      <ClientDashboard initialCustomers={MOCK_CUSTOMERS} />
    </div>
  );
}
