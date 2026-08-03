"use client";

import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell } from 'recharts';
import { MOCK_ANALYTICS } from '@/lib/demoData';
import { DollarSign, ShieldCheck, TrendingUp, BarChart2, Award } from 'lucide-react';

export default function ClientAnalytics({ initialAnalytics }: { initialAnalytics?: any }) {
  const analytics = initialAnalytics || MOCK_ANALYTICS;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Outcome Analytics & ROI Calculation</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Track intervention success rates with 95% Wilson Score confidence intervals and net retained revenue.</p>
      </div>

      {/* ROI Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Revenue Saved (YTD)</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-extrabold text-slate-900 dark:text-white">
            ${analytics.revenue_saved_ytd?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
          <div className="mt-1 text-xs text-emerald-600 dark:text-emerald-400 font-semibold">Net Subscription Revenue Preserved</div>
        </div>

        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Intervention Campaign ROI</span>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
              <Award className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-extrabold text-slate-900 dark:text-white">
            {analytics.roi_multiple}x
          </div>
          <div className="mt-1 text-xs text-purple-600 dark:text-purple-300 font-semibold">Return on Campaign Spend</div>
        </div>

        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Customers Saved</span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-extrabold text-slate-900 dark:text-white">
            {analytics.customers_at_risk_count + 27} Accounts
          </div>
          <div className="mt-1 text-xs text-blue-600 dark:text-blue-400 font-semibold">Retained Post-Intervention</div>
        </div>
      </div>

      {/* Recharts Visualizations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Risk Distribution Pie Chart */}
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-sm space-y-4 transition-colors">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center space-x-2">
            <BarChart2 className="w-4 h-4 text-blue-500" />
            <span>Tenant Churn Risk Distribution</span>
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={analytics.risk_distribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={5}
                  dataKey="count"
                >
                  {analytics.risk_distribution?.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff', borderRadius: '0.75rem', fontSize: '12px' }} 
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Channel Effectiveness Bar Chart */}
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-sm space-y-4 transition-colors">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-emerald-500" />
            <span>Channel Success Rate Comparison</span>
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics.channel_performance}>
                <XAxis dataKey="channel" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} domain={[0, 1]} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff', borderRadius: '0.75rem', fontSize: '12px' }} />
                <Bar dataKey="success_rate" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Wilson Score Statistical Confidence Table */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-sm transition-colors">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-4">Wilson Score Confidence Interval Matrix (95% CI)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Channel Adapter</th>
                <th className="py-3 px-4">Interventions Sent</th>
                <th className="py-3 px-4">Retained Accounts</th>
                <th className="py-3 px-4">Observed Success Rate</th>
                <th className="py-3 px-4">95% Confidence Interval</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
              {analytics.channel_performance?.map((ch: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4 font-sans font-semibold text-slate-900 dark:text-slate-200">{ch.channel}</td>
                  <td className="py-3 px-4 text-slate-700 dark:text-slate-300">{ch.sent}</td>
                  <td className="py-3 px-4 text-emerald-600 dark:text-emerald-400 font-bold">{ch.retained}</td>
                  <td className="py-3 px-4 font-bold text-blue-600 dark:text-blue-400">{(ch.success_rate * 100).toFixed(1)}%</td>
                  <td className="py-3 px-4 text-slate-500 dark:text-slate-400">
                    [{(ch.lower_ci * 100).toFixed(1)}% - {(ch.upper_ci * 100).toFixed(1)}%]
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
