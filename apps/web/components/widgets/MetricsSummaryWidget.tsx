import { AlertTriangle, DollarSign, TrendingUp, Sparkles } from 'lucide-react';

interface MetricsSummaryWidgetProps {
  totalMrrAtRisk: number;
  criticalCount: number;
  avgRisk: string;
  customersCount: number;
}

export default function MetricsSummaryWidget({ totalMrrAtRisk, criticalCount, avgRisk, customersCount }: MetricsSummaryWidgetProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-full h-full">
      <div className="bg-white/95 dark:bg-slate-900/80 border border-slate-200/90 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm relative overflow-hidden transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">MRR at Risk</span>
          <div className="p-2.5 rounded-xl bg-red-500/10 text-red-600 dark:text-red-400">
            <DollarSign className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-3 text-2xl font-black text-slate-900 dark:text-white">${totalMrrAtRisk.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
        <div className="mt-1 text-xs text-red-600 dark:text-red-400 font-bold flex items-center space-x-1">
          <span>Critical & High Tier MRR</span>
        </div>
      </div>

      <div className="bg-white/95 dark:bg-slate-900/80 border border-slate-200/90 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm relative overflow-hidden transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Critical Customers</span>
          <div className="p-2.5 rounded-xl bg-red-500/10 text-red-600 dark:text-red-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-3 text-2xl font-black text-slate-900 dark:text-white">{criticalCount} Accounts</div>
        <div className="mt-1 text-xs text-slate-500 dark:text-slate-400 font-semibold">Require Immediate Intervention</div>
      </div>

      <div className="bg-white/95 dark:bg-slate-900/80 border border-slate-200/90 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm relative overflow-hidden transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Avg Churn Probability</span>
          <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
            <TrendingUp className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-3 text-2xl font-black text-slate-900 dark:text-white">{avgRisk}%</div>
        <div className="mt-1 text-xs text-emerald-600 dark:text-emerald-400 font-bold">Across {customersCount} Accounts</div>
      </div>

      <div className="bg-white/95 dark:bg-slate-900/80 border border-slate-200/90 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm relative overflow-hidden transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">AI Retention Engine</span>
          <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
            <Sparkles className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-3 text-2xl font-black text-slate-900 dark:text-white">XGBoost + Gemini</div>
        <div className="mt-1 text-xs text-purple-600 dark:text-purple-300 font-bold">SHAP Explainability Active</div>
      </div>
    </div>
  );
}
