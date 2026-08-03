"use client";

import { useState } from 'react';
import { ShieldAlert, Download, Search, ShieldCheck, Filter, FileText, Lock } from 'lucide-react';

type AuditEntry = {
  id: string;
  timestamp: string;
  actor: string;
  role: string;
  action: string;
  resource: string;
  ip_address: string;
  compliance_status: 'SOC2 Compliant' | 'GDPR Verified';
};

const MOCK_AUDIT_LOGS: AuditEntry[] = [
  {
    id: 'aud_9901',
    timestamp: '2026-08-03T11:52:10Z',
    actor: 'admin@example.com',
    role: 'owner',
    action: 'CONFIGURE_INTEGRATION',
    resource: 'Stripe Billing API Key Update',
    ip_address: '192.168.1.104',
    compliance_status: 'SOC2 Compliant',
  },
  {
    id: 'aud_9902',
    timestamp: '2026-08-03T11:48:30Z',
    actor: 'analyst@example.com',
    role: 'analyst',
    action: 'TRIGGER_MANUAL_INTERVENTION',
    resource: 'Customer cus_8f93a210 (Email Discount)',
    ip_address: '192.168.1.112',
    compliance_status: 'SOC2 Compliant',
  },
  {
    id: 'aud_9903',
    timestamp: '2026-08-03T11:15:00Z',
    actor: 'admin@example.com',
    role: 'owner',
    action: 'DEPLOY_RETENTION_CAMPAIGN',
    resource: 'Executive Save Offer (Critical Risk)',
    ip_address: '192.168.1.104',
    compliance_status: 'GDPR Verified',
  },
  {
    id: 'aud_9904',
    timestamp: '2026-08-03T10:30:15Z',
    actor: 'viewer@example.com',
    role: 'viewer',
    action: 'EXPORT_CUSTOMER_DATA',
    resource: 'Telemetry CSV Export (Tenant Scope)',
    ip_address: '192.168.1.140',
    compliance_status: 'SOC2 Compliant',
  },
  {
    id: 'aud_9905',
    timestamp: '2026-08-03T09:12:00Z',
    actor: 'system_daemon',
    role: 'system',
    action: 'XGBOOST_MODEL_RETRAIN',
    resource: 'Feature Vector v2.1 Sync',
    ip_address: '10.0.4.12',
    compliance_status: 'SOC2 Compliant',
  },
];

export default function ClientAudit() {
  const [logs] = useState<AuditEntry[]>(MOCK_AUDIT_LOGS);
  const [search, setSearch] = useState('');

  const filteredLogs = logs.filter(l => 
    l.actor.toLowerCase().includes(search.toLowerCase()) ||
    l.action.toLowerCase().includes(search.toLowerCase()) ||
    l.resource.toLowerCase().includes(search.toLowerCase())
  );

  const handleExportCSV = () => {
    const csvContent = "data:text/csv;charset=utf-8," + 
      "Timestamp,Actor,Role,Action,Resource,IP Address,Compliance\n" +
      filteredLogs.map(e => `${e.timestamp},${e.actor},${e.role},${e.action},"${e.resource}",${e.ip_address},${e.compliance_status}`).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `soc2_audit_log_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">SOC2 & GDPR Compliance Audit Stream</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Immutable, tenant-scoped audit trail of all security actions, configuration edits, & data exports.</p>
        </div>

        <button
          onClick={handleExportCSV}
          className="py-2.5 px-4 bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 dark:hover:bg-slate-700 text-white rounded-xl text-xs font-semibold shadow-md transition-all flex items-center space-x-2"
        >
          <Download className="w-4 h-4" />
          <span>Export Audit Log (CSV)</span>
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Compliance Status</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold text-slate-900 dark:text-white">SOC2 Type II Certified</div>
          <div className="mt-1 text-xs text-emerald-600 dark:text-emerald-400 font-semibold">Encryption at Rest & in Transit</div>
        </div>

        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Audit Log Retention</span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold text-slate-900 dark:text-white">365 Days Retained</div>
          <div className="mt-1 text-xs text-blue-600 dark:text-blue-400 font-semibold">Immutable Append-Only Log</div>
        </div>

        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl backdrop-blur-xl shadow-sm transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Access Policy</span>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
              <Lock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-2xl font-bold text-slate-900 dark:text-white">Tenant-Isolated RBAC</div>
          <div className="mt-1 text-xs text-purple-600 dark:text-purple-300 font-semibold">AES-256 GCM Key Encryption</div>
        </div>
      </div>

      {/* Main Audit Table */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-sm transition-colors">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Security Event Log Stream</h3>
          <input
            type="text"
            placeholder="Search action, actor email, or target..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Actor Email</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Action Executed</th>
                <th className="py-3 px-4">Target Resource</th>
                <th className="py-3 px-4">IP Address</th>
                <th className="py-3 px-4 text-right">Compliance Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
              {filteredLogs.map(l => (
                <tr key={l.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3.5 px-4 text-slate-500 dark:text-slate-400 font-sans">{new Date(l.timestamp).toLocaleString()}</td>
                  <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-slate-200">{l.actor}</td>
                  <td className="py-3.5 px-4">
                    <span className="capitalize px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 font-sans text-[11px]">
                      {l.role}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-bold text-blue-600 dark:text-blue-400">{l.action}</td>
                  <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300 font-sans">{l.resource}</td>
                  <td className="py-3.5 px-4 text-slate-500 dark:text-slate-400">{l.ip_address}</td>
                  <td className="py-3.5 px-4 text-right">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                      {l.compliance_status}
                    </span>
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
