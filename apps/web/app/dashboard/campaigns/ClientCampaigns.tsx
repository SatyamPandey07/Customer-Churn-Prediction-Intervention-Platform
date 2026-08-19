"use client";

import { useState, useEffect } from 'react';
import { Megaphone, Plus, Mail, MessageSquare, Send, Sparkles, Check, Play, Pause, Trash2, Filter } from 'lucide-react';
import { MOCK_CAMPAIGNS, Campaign } from '@/lib/demoData';

export default function ClientCampaigns({ initialCampaigns = [], userRole: initialRole }: { initialCampaigns?: Campaign[]; userRole: string }) {
  const [campaigns, setCampaigns] = useState<Campaign[]>(
    initialCampaigns.length > 0 ? initialCampaigns : MOCK_CAMPAIGNS
  );
  const [userRole, setUserRole] = useState(initialRole || 'admin');
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [riskTier, setRiskTier] = useState('critical');
  const [mrrGt, setMrrGt] = useState('500');
  const [channel, setChannel] = useState<'email' | 'sms' | 'slack' | 'in_app'>('email');
  const [template, setTemplate] = useState('Hi {{customer_name}}, We noticed seat changes on your subscription. Connect with your dedicated CSM to unlock 15% renewal discount.');
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    const match = document.cookie.match(/(?:^|;\s*)user_role=([^;]*)/);
    if (match) setUserRole(decodeURIComponent(match[1]));
  }, []);

  const canEdit = userRole === 'owner' || userRole === 'admin' || userRole === 'analyst';

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    const newCamp: Campaign = {
      id: `cmp_${Date.now().toString().slice(-4)}`,
      name,
      trigger_rule: { risk_tier: riskTier, mrr_gt: Number(mrrGt) },
      intervention_type: 'executive_discount',
      channel,
      template,
      status: 'active',
      created_at: new Date().toISOString(),
      sent_count: 0,
      retained_count: 0,
    };

    setCampaigns([newCamp, ...campaigns]);
    setShowForm(false);
    setName('');
    setSuccessMsg('Campaign deployed successfully!');
    setTimeout(() => setSuccessMsg(''), 4000);
  };

  const toggleStatus = (id: string) => {
    setCampaigns(campaigns.map(c => {
      if (c.id === id) {
        return { ...c, status: c.status === 'active' ? 'paused' : 'active' };
      }
      return c;
    }));
  };

  const getChannelIcon = (ch: string) => {
    switch (ch) {
      case 'email': return <Mail className="w-4 h-4 text-blue-500" />;
      case 'slack': return <Send className="w-4 h-4 text-purple-500" />;
      case 'sms': return <MessageSquare className="w-4 h-4 text-emerald-500" />;
      default: return <Sparkles className="w-4 h-4 text-amber-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Automated Retention Campaigns</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Configure automated outreach triggers for customers matching specific XGBoost risk thresholds.</p>
        </div>

        {canEdit && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-500/20 transition-all flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Create New Campaign</span>
          </button>
        )}
      </div>

      {successMsg && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 p-3.5 rounded-xl text-xs flex items-center space-x-2 font-semibold">
          <Check className="w-4 h-4 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Campaign Builder Form */}
      {showForm && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-xl space-y-4 transition-colors">
          <div className="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-blue-500" />
              <span>Campaign Builder Workflow</span>
            </h3>
            <button onClick={() => setShowForm(false)} className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white">Cancel</button>
          </div>

          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 dark:text-slate-300 uppercase tracking-wider mb-1">Campaign Title</label>
              <input
                type="text"
                required
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. Enterprise Save Offer - Critical Churn Risk"
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-300 uppercase tracking-wider mb-1">Target Risk Tier</label>
                <select
                  value={riskTier}
                  onChange={e => setRiskTier(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-800 dark:text-slate-100 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="critical">Critical Risk (&gt;75%)</option>
                  <option value="high">High Risk (50-75%)</option>
                  <option value="medium">Medium Risk (25-50%)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-300 uppercase tracking-wider mb-1">Min. Monthly Revenue ($)</label>
                <input
                  type="number"
                  value={mrrGt}
                  onChange={e => setMrrGt(e.target.value)}
                  placeholder="500"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-800 dark:text-slate-100 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 dark:text-slate-300 uppercase tracking-wider mb-1">Outreach Channel Adapter</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: 'email', label: 'Email', icon: Mail },
                  { id: 'slack', label: 'Slack Webhook', icon: Send },
                  { id: 'sms', label: 'SMS Alert', icon: MessageSquare },
                  { id: 'in_app', label: 'In-App Dialog', icon: Sparkles },
                ].map(ch => {
                  const Icon = ch.icon;
                  const isSel = channel === ch.id;
                  return (
                    <button
                      type="button"
                      key={ch.id}
                      onClick={() => setChannel(ch.id as any)}
                      className={`py-2 px-3 rounded-xl text-xs font-medium border flex items-center justify-center space-x-2 transition-all ${
                        isSel 
                          ? 'bg-blue-500/10 border-blue-500 text-blue-600 dark:text-blue-400 font-semibold' 
                          : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{ch.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 dark:text-slate-300 uppercase tracking-wider mb-1">Intervention Message Template</label>
              <textarea
                rows={3}
                value={template}
                onChange={e => setTemplate(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3 text-xs text-slate-800 dark:text-slate-100 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              className="py-2.5 px-5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-500/20 transition-all flex items-center space-x-2"
            >
              <span>Deploy Active Campaign</span>
              <Check className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}

      {/* Active Campaigns List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {campaigns.map(cmp => (
          <div key={cmp.id} className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 backdrop-blur-xl space-y-4 shadow-sm transition-colors">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="p-1.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                    {getChannelIcon(cmp.channel)}
                  </span>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">{cmp.name}</h3>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                  Trigger: Risk = <span className="text-red-600 dark:text-red-400 uppercase font-semibold">{cmp.trigger_rule.risk_tier}</span> 
                  {cmp.trigger_rule.mrr_gt ? ` & MRR > $${cmp.trigger_rule.mrr_gt}` : ''}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                  cmp.status === 'active' 
                    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30' 
                    : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30'
                }`}>
                  {cmp.status}
                </span>

                {canEdit && (
                  <button
                    onClick={() => toggleStatus(cmp.id)}
                    className="p-1.5 bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-500 transition-colors"
                    title={cmp.status === 'active' ? 'Pause' : 'Activate'}
                  >
                    {cmp.status === 'active' ? <Pause className="w-3.5 h-3.5 text-amber-500" /> : <Play className="w-3.5 h-3.5 text-emerald-500" />}
                  </button>
                )}
              </div>
            </div>

            <p className="text-xs text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-950/60 p-3 rounded-xl border border-slate-200 dark:border-slate-800/80 italic">
              &quot;{cmp.template}&quot;
            </p>

            <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-100 dark:border-slate-800/60 text-slate-500 dark:text-slate-400">
              <div>
                Outreach Executed: <span className="font-semibold text-slate-900 dark:text-slate-200">{cmp.sent_count}</span>
              </div>
              <div>
                Retention Rate: <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                  {cmp.sent_count > 0 ? ((cmp.retained_count / cmp.sent_count) * 100).toFixed(0) + '%' : '74%'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
