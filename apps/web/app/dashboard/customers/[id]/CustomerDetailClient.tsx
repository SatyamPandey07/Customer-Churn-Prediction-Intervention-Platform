"use client";


import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Sparkles, AlertTriangle, ShieldCheck, Mail, Send, MessageSquare, CheckCircle, Calendar, CreditCard, Activity } from 'lucide-react';
import { MOCK_CUSTOMERS, MOCK_EXPLANATIONS } from '@/lib/demoData';
import { useState } from 'react';

export default function CustomerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const customerId = params.id as string;
  const [success, setSuccess] = useState<string | null>(null);

  const customer = MOCK_CUSTOMERS.find(c => c.id === customerId) || {
    id: customerId || 'cus_8f93a210-4b11-4a7b-8910-c119284fa901',
    plan: 'enterprise',
    mrr: 4500.0,
    churn_probability: 0.89,
    churn_risk_tier: 'critical',
    first_seen_at: '2025-01-15T08:00:00Z',
    last_seen_at: '2026-08-01T14:22:00Z',
    external_ids: { stripe: 'cus_stripe_99', zendesk: 'zen_102' },
    trend: [12, 25, 45, 60, 78, 89],
  };

  const explanation = MOCK_EXPLANATIONS[customer.id] || MOCK_EXPLANATIONS['cus_8f93a210-4b11-4a7b-8910-c119284fa901'];

  const triggerOutreach = (channel: string) => {
    setSuccess(`Manual ${channel.toUpperCase()} outreach queued for customer.`);
    setTimeout(() => setSuccess(null), 4000);
  };

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.back()}
        className="flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Risk Dashboard</span>
      </button>

      {/* Hero Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <h1 className="text-xl font-bold font-mono text-white">{customer.id}</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase bg-red-500/10 text-red-400 border border-red-500/30">
              {customer.churn_risk_tier} Risk
            </span>
          </div>
          <p className="text-xs text-slate-400">First seen: {new Date(customer.first_seen_at).toLocaleDateString()} • Last activity: {new Date(customer.last_seen_at).toLocaleString()}</p>
        </div>

        <div className="flex items-center space-6 text-right">
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Monthly Revenue</div>
            <div className="text-xl font-extrabold text-white">${customer.mrr.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Churn Probability</div>
            <div className="text-xl font-extrabold text-red-400">{(customer.churn_probability * 100).toFixed(1)}%</div>
          </div>
        </div>
      </div>

      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-3.5 rounded-xl text-xs flex items-center space-x-2">
          <CheckCircle className="w-4 h-4" />
          <span>{success}</span>
        </div>
      )}

      {/* SHAP & Gemini Intervention Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* SHAP Feature Signals */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl space-y-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <Activity className="w-4 h-4 text-red-400" />
            <span>SHAP Feature Contribution Rankings</span>
          </h2>
          <div className="space-y-3">
            {explanation?.top_drivers?.map((driver: any, idx: number) => (
              <div key={idx} className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-200">{driver.human_readable}</span>
                  <span className="font-mono text-red-400 font-bold">+{(driver.shap_value * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-red-500 h-full rounded-full" style={{ width: `${driver.shap_value * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Gemini Generated Recommendation & Manual Override */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl space-y-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <span>Gemini AI Recommended Intervention</span>
          </h2>

          <div className="p-4 bg-blue-950/30 border border-blue-500/30 rounded-xl space-y-2">
            <div className="text-xs font-bold text-blue-300">{explanation?.intervention_recommendation?.strategy}</div>
            <p className="text-xs text-slate-300 italic bg-slate-950 p-3 rounded-lg border border-slate-800">
              &quot;{explanation?.intervention_recommendation?.copy}&quot;
            </p>
          </div>

          <div className="pt-2 space-y-2">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Execute Outreach Override</div>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => triggerOutreach('email')}
                className="py-2 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all"
              >
                <Mail className="w-3.5 h-3.5" />
                <span>Email</span>
              </button>
              <button
                onClick={() => triggerOutreach('slack')}
                className="py-2 px-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Slack</span>
              </button>
              <button
                onClick={() => triggerOutreach('in_app')}
                className="py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>In-App</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
