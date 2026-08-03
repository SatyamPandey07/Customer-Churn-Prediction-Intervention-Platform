"use client";

import { useState } from 'react';
import { Users, Key, Bell, Shield, Plus, Trash2, CheckCircle2, Copy, Check } from 'lucide-react';

type Member = {
  id: string;
  name: string;
  email: string;
  role: 'owner' | 'admin' | 'analyst' | 'viewer';
  status: 'active' | 'pending';
};

type ApiKey = {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
};

export default function ClientSettings() {
  const [members, setMembers] = useState<Member[]>([
    { id: 'm1', name: 'Admin User', email: 'admin@example.com', role: 'owner', status: 'active' },
    { id: 'm2', name: 'Sarah Jenkins', email: 'analyst@example.com', role: 'analyst', status: 'active' },
    { id: 'm3', name: 'Dave Miller', email: 'viewer@example.com', role: 'viewer', status: 'pending' },
  ]);

  const [apiKeys, setApiKeys] = useState<ApiKey[]>([
    { id: 'k1', name: 'Production Telemetry Pipeline', prefix: 'churn_live_••••8901', created_at: '2026-07-10T08:00:00Z' },
    { id: 'k2', name: 'Segment Data Ingestion Key', prefix: 'churn_live_••••3312', created_at: '2026-07-20T14:30:00Z' },
  ]);

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'analyst' | 'viewer'>('analyst');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    const newMember: Member = {
      id: `m_${Date.now()}`,
      name: inviteEmail.split('@')[0],
      email: inviteEmail,
      role: inviteRole,
      status: 'pending',
    };
    setMembers([...members, newMember]);
    setShowInviteModal(false);
    setInviteEmail('');
    setSuccess(`Invitation email sent to ${inviteEmail}!`);
    setTimeout(() => setSuccess(null), 4000);
  };

  const handleGenerateApiKey = () => {
    const newKey: ApiKey = {
      id: `k_${Date.now()}`,
      name: 'New Custom Connector Key',
      prefix: `churn_live_••••${Math.floor(1000 + Math.random() * 9000)}`,
      created_at: new Date().toISOString(),
    };
    setApiKeys([newKey, ...apiKeys]);
    setSuccess('New API Secret Key generated successfully!');
    setTimeout(() => setSuccess(null), 4000);
  };

  const handleDeleteApiKey = (id: string) => {
    setApiKeys(apiKeys.filter(k => k.id !== id));
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Tenant Settings & Access Control</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Manage team member RBAC permissions, API secret keys, & platform webhook notifications.</p>
      </div>

      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 p-3.5 rounded-xl text-xs flex items-center space-x-2 font-semibold">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Team RBAC Section */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-sm transition-colors space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center space-x-2">
              <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Team Members & Role Permissions (RBAC)</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Control tenant access levels for CSMs, Analysts, and Owners.</p>
          </div>

          <button
            onClick={() => setShowInviteModal(true)}
            className="py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-500/20 transition-all flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Invite Team Member</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">User</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Assigned Role</th>
                <th className="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {members.map(m => (
                <tr key={m.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-slate-200">{m.name}</td>
                  <td className="py-3.5 px-4 text-slate-600 dark:text-slate-400 font-mono">{m.email}</td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                      m.role === 'owner' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30' :
                      m.role === 'analyst' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30' :
                      'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                    }`}>
                      {m.role}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right font-semibold">
                    <span className={`text-[11px] capitalize ${m.status === 'active' ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-500'}`}>
                      • {m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* API Key Management */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-sm transition-colors space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center space-x-2">
              <Key className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              <span>API Keys & Authentication Tokens</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Secret keys used by custom backend scripts and webhooks to ingest customer events.</p>
          </div>

          <button
            onClick={handleGenerateApiKey}
            className="py-2.5 px-4 bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 dark:hover:bg-slate-700 text-white rounded-xl text-xs font-semibold shadow-md transition-all flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Generate New API Key</span>
          </button>
        </div>

        <div className="space-y-3">
          {apiKeys.map(k => (
            <div key={k.id} className="p-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="text-xs font-bold text-slate-900 dark:text-slate-200">{k.name}</div>
                <div className="text-xs font-mono text-slate-500 dark:text-slate-400">{k.prefix}</div>
              </div>

              <div className="flex items-center space-x-3 text-xs">
                <span className="text-slate-400 hidden sm:inline">Created {new Date(k.created_at).toLocaleDateString()}</span>
                <button
                  onClick={() => handleDeleteApiKey(k.id)}
                  className="p-2 text-slate-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  title="Revoke Key"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl relative transition-colors">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Invite Team Member</h3>

            <form onSubmit={handleInvite} className="space-y-4 text-xs">
              <div>
                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-300 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={e => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-800 dark:text-slate-200 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-300 uppercase tracking-wider mb-1">
                  Role Level
                </label>
                <select
                  value={inviteRole}
                  onChange={e => setInviteRole(e.target.value as any)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-800 dark:text-slate-200 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="admin">Admin (Campaign & Model Read/Write)</option>
                  <option value="analyst">Analyst (Campaign Read/Write)</option>
                  <option value="viewer">Viewer (Read Only)</option>
                </select>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="py-2 px-4 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="py-2 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold shadow-md"
                >
                  Send Invite
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
