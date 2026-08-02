import { fetchAPI } from '@/lib/api';
import ClientDashboard from './ClientDashboard';

export default async function DashboardPage() {
  let initialCustomers = [];
  try {
    initialCustomers = await fetchAPI('/customers');
  } catch (e) {
    console.error('Failed to fetch customers:', e);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900">Churn Risk Dashboard</h1>
      <ClientDashboard initialCustomers={initialCustomers} />
    </div>
  );
}
