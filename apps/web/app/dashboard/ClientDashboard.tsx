"use client";

import { useEffect, useState } from 'react';
import { useRealtime } from '@/components/RealtimeProvider';
import { useRouter } from 'next/navigation';

type Customer = {
  id: string;
  plan: string | null;
  mrr: number;
  churn_probability: number | null;
  churn_risk_tier: string | null;
};

export default function ClientDashboard({ initialCustomers }: { initialCustomers: Customer[] }) {
  const [customers, setCustomers] = useState<Customer[]>(initialCustomers);
  const [sortField, setSortField] = useState<keyof Customer>('churn_probability');
  const [sortDesc, setSortDesc] = useState(true);
  const [tierFilter, setTierFilter] = useState<string>('all');
  const socket = useRealtime();
  const router = useRouter();

  useEffect(() => {
    if (!socket) return;
    
    const handleUpdate = (data: any) => {
      setCustomers(prev => prev.map(c => {
        if (c.id === data.customer_id) {
          return {
            ...c,
            churn_probability: data.churn_probability,
            churn_risk_tier: data.churn_risk_tier
          };
        }
        return c;
      }));
    };
    
    socket.on('churn_update', handleUpdate);
    return () => {
      socket.off('churn_update', handleUpdate);
    };
  }, [socket]);

  const handleSort = (field: keyof Customer) => {
    if (sortField === field) {
      setSortDesc(!sortDesc);
    } else {
      setSortField(field);
      setSortDesc(true);
    }
  };

  const getTierColor = (tier: string | null) => {
    switch (tier?.toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const filtered = customers.filter(c => tierFilter === 'all' || c.churn_risk_tier?.toLowerCase() === tierFilter.toLowerCase());
  
  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    if (aVal === bVal) return 0;
    if (aVal === null) return 1;
    if (bVal === null) return -1;
    
    const modifier = sortDesc ? -1 : 1;
    return aVal < bVal ? -1 * modifier : 1 * modifier;
  });

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-medium text-gray-900">Active Customers</h2>
        <div>
          <select 
            value={tierFilter} 
            onChange={e => setTierFilter(e.target.value)}
            className="border-gray-300 rounded-md shadow-sm text-sm focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Tiers</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort('id')}>Customer ID</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort('plan')}>Plan</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort('mrr')}>MRR</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100" onClick={() => handleSort('churn_probability')}>Churn Risk</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trend</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sorted.map((customer) => (
              <tr 
                key={customer.id} 
                className="hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => router.push(`/dashboard/customers/${customer.id}`)}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 font-mono text-xs">{customer.id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{customer.plan || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${customer.mrr.toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full border ${getTierColor(customer.churn_risk_tier)}`}>
                      {customer.churn_risk_tier || 'UNKNOWN'}
                    </span>
                    <span className="text-sm text-gray-500">
                      {customer.churn_probability !== null ? (customer.churn_probability * 100).toFixed(1) + '%' : '--'}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {/* Mock Sparkline visually */}
                  <div className="h-4 w-16 bg-gray-100 flex items-end space-x-0.5 rounded overflow-hidden">
                    {Array.from({length: 6}).map((_, i) => (
                       <div key={i} className={`w-2 rounded-t-sm ${customer.churn_probability && customer.churn_probability > 0.5 ? 'bg-red-400' : 'bg-green-400'}`} style={{height: `${Math.max(10, Math.random() * 100)}%`}} />
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">No customers found matching the criteria.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
