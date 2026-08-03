"use client";

import { useEffect, useState } from 'react';
import { useRealtime } from '@/components/RealtimeProvider';
import { useRouter } from 'next/navigation';
import { 
  AlertTriangle, DollarSign, Users, TrendingUp, Sparkles, Filter, 
  ArrowUpDown, ChevronRight, X, Mail, Send, MessageSquare, CheckCircle, ShieldAlert
} from 'lucide-react';
import { MOCK_EXPLANATIONS, Customer } from '@/lib/demoData';

export default function ClientDashboard({ initialCustomers }: { initialCustomers: Customer[] }) {
  const [customers, setCustomers] = useState<Customer[]>(initialCustomers);
  const [sortField, setSortField] = useState<keyof Customer>('churn_probability');
  const [sortDesc, setSortDesc] = useState(true);
  const [tierFilter, setTierFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [outreachSuccess, setOutreachSuccess] = useState<string | null>(null);

  const socket = useRealtime();

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

  const getTierBadge = (tier: string | null) => {
    switch (tier?.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'high':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
      case 'low':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  // Metric Stats
  const totalMrrAtRisk = customers
    .filter(c => c.churn_risk_tier === 'critical' || c.churn_risk_tier === 'high')
    .reduce((sum, c) => sum + (c.mrr || 0), 0);

  const criticalCount = customers.filter(c => c.churn_risk_tier === 'critical').length;
  const avgRisk = customers.length > 0 
    ? (customers.reduce((sum, c) => sum + (c.churn_probability || 0), 0) / customers.length * 100).toFixed(1)
    : '0';

  const filtered = customers.filter(c => {
    const matchesTier = tierFilter === 'all' || c.churn_risk_tier?.toLowerCase() === tierFilter.toLowerCase();
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
  });

  const handleSendOutreach = (channel: string) => {
    setOutreachSuccess(`Automated ${channel.toUpperCase()} outreach triggered successfully!`);
    setTimeout(() => setOutreachSuccess(null), 4000);
  };

  const explanation = selectedCustomer ? (MOCK_EXPLANATIONS[selectedCustomer.id] || {
    risk_tier: selectedCustomer.churn_risk_tier || 'medium',
    top_drivers: [
      { feature: 'usage_trend_30d', shap_value: 0.32, human_readable: 'Product login frequency dropped by 42% in past 30 days' },
      { feature: 'support_tickets_90d', shap_value: 0.24, human_readable: '3 billing inquiry tickets opened in past 45 days' },
      { feature: 'seat_shrinkage', shap_value: 0.15, human_readable: 'Active user seat allocation shrank by 30%' },
    ],
    intervention_recommendation: {
      strategy: 'Proactive Customer Success Check-In + Usage Review',
      copy: `Hi Support Team, We observed a drop in overall product activity for customer ${selectedCustomer.id.slice(0, 8)}. Recommend scheduling a 15-minute sync with their admin.`,
      recommended_channel: 'email',
    }
  }) : null;

  return (
    <div className="space-y-6">
      {/* Metric Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl backdrop-blur-xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">MRR at Risk</span>
            <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold text-white">${totalMrrAtRisk.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
          <div className="mt-1 text-xs text-red-400 flex items-center space-x-1">
            <span>Critical & High Tier MRR</span>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl backdrop-blur-xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Customers</span>
            <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold text-white">{criticalCount} Accounts</div>
          <div className="mt-1 text-xs text-slate-400">Require Immediate Intervention</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl backdrop-blur-xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg Churn Probability</span>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold text-white">{avgRisk}%</div>
          <div className="mt-1 text-xs text-emerald-400">Across {customers.length} Accounts</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl backdrop-blur-xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">AI Retention Engine</span>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
              <Sparkles className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold text-white">XGBoost + Gemini</div>
          <div className="mt-1 text-xs text-purple-300">SHAP Explainability Active</div>
        </div>
      </div>

      {/* Main Customers Table Container */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-xl">
        {/* Controls Bar */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Churn Risk Telemetry</h2>
            <p className="text-xs text-slate-400 mt-0.5">Real-time XGBoost risk predictions & automated SHAP driver rankings</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <input
              type="text"
              placeholder="Filter by ID or Plan..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />

            {/* Risk Tier Filter */}
            <select
              value={tierFilter}
              onChange={e => setTierFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All Tiers</option>
              <option value="critical">Critical (>75%)</option>
              <option value="high">High (50-75%)</option>
              <option value="medium">Medium (25-50%)</option>
              <option value="low">Low (&lt;25%)</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4 cursor-pointer hover:text-white" onClick={() => handleSort('id')}>Customer ID</th>
                <th className="py-3 px-4 cursor-pointer hover:text-white" onClick={() => handleSort('plan')}>Plan Tier</th>
                <th className="py-3 px-4 cursor-pointer hover:text-white" onClick={() => handleSort('mrr')}>Monthly Revenue</th>
                <th className="py-3 px-4 cursor-pointer hover:text-white" onClick={() => handleSort('churn_probability')}>Churn Risk Score</th>
                <th className="py-3 px-4">Risk Velocity Trend</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs">
              {sorted.map(c => (
                <tr 
                  key={c.id}
                  className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                  onClick={() => setSelectedCustomer(c)}
                >
                  <td className="py-3.5 px-4 font-mono text-slate-200 font-semibold flex items-center space-x-2">
                    <span>{c.id.slice(0, 18)}...</span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="capitalize px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300 font-medium">
                      {c.plan || 'basic'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-100 font-semibold">
                    ${(c.mrr || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase border ${getTierBadge(c.churn_risk_tier)}`}>
                        {c.churn_risk_tier || 'LOW'}
                      </span>
                      <span className="font-semibold text-slate-300">
                        {c.churn_probability !== null ? (c.churn_probability * 100).toFixed(1) + '%' : '--'}
                      </span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    {/* Visual Sparkline */}
                    <div className="h-5 w-24 bg-slate-950 rounded border border-slate-800/60 flex items-end p-0.5 space-x-0.5">
                      {(c.trend || [10, 20, 30, 40, 50, 60]).map((val, idx) => (
                        <div
                          key={idx}
                          className={`flex-1 rounded-t-xs transition-all ${
                            (c.churn_probability || 0) > 0.5 ? 'bg-red-500/80' : 'bg-emerald-500/80'
                          }`}
                          style={{ height: `${Math.max(15, val)}%` }}
                        />
                      ))}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedCustomer(c);
                      }}
                      className="px-3 py-1 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/30 text-blue-400 rounded-lg text-xs font-medium transition-all flex items-center space-x-1 ml-auto"
                    >
                      <span>Inspect Risk</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}

              {sorted.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">No matching customers found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SHAP & Gemini Risk Explanation Modal / Drawer */}
      {selectedCustomer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl relative">
            <button
              onClick={() => setSelectedCustomer(null)}
              className="absolute top-4 right-4 p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Header */}
            <div>
              <div className="flex items-center space-x-2 text-xs font-semibold text-blue-400 uppercase tracking-wider mb-1">
                <Sparkles className="w-4 h-4 text-blue-400" />
                <span>Gemini & SHAP Risk Analysis</span>
              </div>
              <h3 className="text-xl font-bold text-white font-mono">{selectedCustomer.id}</h3>
              <div className="flex items-center space-x-3 mt-2 text-xs">
                <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase border ${getTierBadge(selectedCustomer.churn_risk_tier)}`}>
                  {selectedCustomer.churn_risk_tier} Risk Tier
                </span>
                <span className="text-slate-300 font-semibold">
                  Probability: {((selectedCustomer.churn_probability || 0) * 100).toFixed(1)}%
                </span>
                <span className="text-slate-400">MRR: ${selectedCustomer.mrr.toFixed(2)}</span>
              </div>
            </div>

            {outreachSuccess && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-3 rounded-lg text-xs flex items-center space-x-2">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                <span>{outreachSuccess}</span>
              </div>
            )}

            {/* Top SHAP Drivers */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Top Churn Signal Drivers (SHAP Rankings)</h4>
              <div className="space-y-2">
                {explanation?.top_drivers?.map((driver: any, idx: number) => (
                  <div key={idx} className="p-3 bg-slate-950/80 border border-slate-800/80 rounded-xl flex items-start justify-between">
                    <div className="space-y-0.5">
                      <div className="text-xs font-semibold text-slate-200">{driver.human_readable}</div>
                      <div className="text-[10px] text-slate-500 font-mono">Feature ID: {driver.feature}</div>
                    </div>
                    <span className="text-xs font-mono font-bold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
                      +{(driver.shap_value * 100).toFixed(0)}% Impact
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Gemini Intervention Strategy */}
            <div className="p-4 bg-gradient-to-r from-blue-950/40 to-indigo-950/40 border border-blue-500/30 rounded-xl space-y-2">
              <div className="flex items-center space-x-2 text-xs font-bold text-blue-300">
                <Sparkles className="w-4 h-4 text-blue-400" />
                <span>Gemini Recommended Strategy</span>
              </div>
              <div className="text-xs font-semibold text-white">{explanation?.intervention_recommendation?.strategy}</div>
              <p className="text-xs text-slate-300 italic bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                "{explanation?.intervention_recommendation?.copy}"
              </p>
            </div>

            {/* 1-Click Automated Outreach */}
            <div className="pt-2">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Execute Immediate Retention Campaign</div>
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => handleSendOutreach('email')}
                  className="py-2.5 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition-all flex items-center justify-center space-x-2 shadow-lg shadow-blue-600/20"
                >
                  <Mail className="w-4 h-4" />
                  <span>Send Email Offer</span>
                </button>

                <button
                  onClick={() => handleSendOutreach('slack')}
                  className="py-2.5 px-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-semibold transition-all flex items-center justify-center space-x-2 shadow-lg shadow-purple-600/20"
                >
                  <Send className="w-4 h-4" />
                  <span>Slack Alert</span>
                </button>

                <button
                  onClick={() => handleSendOutreach('in_app')}
                  className="py-2.5 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition-all flex items-center justify-center space-x-2 shadow-lg shadow-emerald-600/20"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>In-App Banner</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
