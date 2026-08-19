import { useState } from 'react';
import { Customer } from '@/lib/demoData';
import { ChevronRight } from 'lucide-react';

interface ChurnRiskTableWidgetProps {
  customers: Customer[];
  onSelectCustomer: (c: Customer) => void;
  config: Record<string, any>;
}

export default function ChurnRiskTableWidget({ customers, onSelectCustomer, config }: ChurnRiskTableWidgetProps) {
  const [sortField, setSortField] = useState<keyof Customer>('churn_probability');
  const [sortDesc, setSortDesc] = useState(true);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Extract config
  const riskFilter = config?.risk_tier_filter || 'all';
  const rowLimit = config?.row_limit || 10;

  const handleSort = (field: keyof Customer) => {
    if (sortField === field) {
      setSortDesc(!sortDesc);
    } else {
      setSortField(field);
      setSortDesc(true);
    }
  };

  const getTierBadge = (tier: string | null) => {
    switch (tier?.toLowerCase()) {
      case 'critical': return 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30';
      case 'high': return 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/30';
      case 'medium': return 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30';
      case 'low': return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
      default: return 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border-slate-200 dark:border-slate-700';
    }
  };

  const filtered = customers.filter(c => {
    const matchesTier = riskFilter === 'all' || c.churn_risk_tier?.toLowerCase() === riskFilter.toLowerCase();
    const matchesSearch = c.id.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          (c.plan && c.plan.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesTier && matchesSearch;
  });

  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    if (aVal === bVal) return 0;
    if (aVal === null) return 1;
    if (bVal === null) return -1;
    const modifier = sortDesc ? -1 : 1;
    return aVal < bVal ? -1 * modifier : 1 * modifier;
  }).slice(0, rowLimit);

  return (
    <div className="w-full h-full flex flex-col">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">Churn Risk Telemetry</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-medium">Real-time XGBoost risk predictions & SHAP driver rankings</p>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Filter by ID or Plan..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800 rounded-xl px-3.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Mobile Stacked Cards */}
      <div className="md:hidden flex flex-col space-y-3">
        {sorted.map(c => (
          <div key={c.id} className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-4 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors shadow-sm" onClick={() => onSelectCustomer(c)}>
            <div className="flex justify-between items-start mb-2">
              <div>
                <div className="font-mono text-slate-900 dark:text-slate-200 font-bold text-sm">{c.id.slice(0, 18)}...</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-0.5 capitalize">{c.plan || 'basic'} Plan</div>
              </div>
              <div className="text-right">
                <div className="text-slate-900 dark:text-slate-100 font-bold text-sm">${(c.mrr || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase border ${getTierBadge(c.churn_risk_tier)}`}>
                  {c.churn_risk_tier || 'LOW'}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between pt-3 border-t border-slate-200 dark:border-slate-800/60">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-slate-600 dark:text-slate-400">Risk:</span>
                <span className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                  {c.churn_probability !== null ? (c.churn_probability * 100).toFixed(1) + '%' : '--'}
                </span>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); onSelectCustomer(c); }}
                className="px-3 py-1.5 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/30 text-blue-700 dark:text-blue-400 rounded-lg text-xs font-bold transition-all flex items-center space-x-1"
              >
                <span>Inspect</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Desktop Table */}
      <div className="hidden md:block overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-extrabold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              <th className="py-3 px-4 cursor-pointer hover:text-slate-900 dark:hover:text-white" onClick={() => handleSort('id')}>Customer ID</th>
              <th className="py-3 px-4 cursor-pointer hover:text-slate-900 dark:hover:text-white" onClick={() => handleSort('plan')}>Plan Tier</th>
              <th className="py-3 px-4 cursor-pointer hover:text-slate-900 dark:hover:text-white" onClick={() => handleSort('mrr')}>Monthly Revenue</th>
              <th className="py-3 px-4 cursor-pointer hover:text-slate-900 dark:hover:text-white" onClick={() => handleSort('churn_probability')}>Churn Risk Score</th>
              <th className="py-3 px-4">Risk Velocity Trend</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
            {sorted.map(c => (
              <tr 
                key={c.id}
                className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors group cursor-pointer"
                onClick={() => onSelectCustomer(c)}
              >
                <td className="py-3.5 px-4 font-mono text-slate-900 dark:text-slate-200 font-bold">{c.id.slice(0, 18)}...</td>
                <td className="py-3.5 px-4">
                  <span className="capitalize px-2.5 py-0.5 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-300 font-semibold text-[11px]">
                    {c.plan || 'basic'}
                  </span>
                </td>
                <td className="py-3.5 px-4 text-slate-900 dark:text-slate-100 font-bold">${(c.mrr || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                <td className="py-3.5 px-4">
                  <div className="flex items-center space-x-2">
                    <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-extrabold uppercase border ${getTierBadge(c.churn_risk_tier)}`}>
                      {c.churn_risk_tier || 'LOW'}
                    </span>
                    <span className="font-bold text-slate-800 dark:text-slate-200">
                      {c.churn_probability !== null ? (c.churn_probability * 100).toFixed(1) + '%' : '--'}
                    </span>
                  </div>
                </td>
                <td className="py-3.5 px-4">
                  <div className="h-5 w-24 bg-slate-100 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800/60 flex items-end p-0.5 space-x-0.5">
                    {(c.trend || [10, 20, 30, 40, 50, 60]).map((val, idx) => (
                      <div
                        key={idx}
                        className={`flex-1 rounded-t-xs transition-all ${
                          (c.churn_probability || 0) > 0.5 ? 'bg-red-500' : 'bg-emerald-500'
                        }`}
                        style={{ height: `${Math.max(15, val)}%` }}
                      />
                    ))}
                  </div>
                </td>
                <td className="py-3.5 px-4 text-right">
                  <button
                    onClick={(e) => { e.stopPropagation(); onSelectCustomer(c); }}
                    className="px-3 py-1 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/30 text-blue-700 dark:text-blue-400 rounded-lg text-xs font-bold transition-all flex items-center space-x-1 ml-auto"
                  >
                    <span>Inspect Risk</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
