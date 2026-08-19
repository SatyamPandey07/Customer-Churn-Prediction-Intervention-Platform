"use client";

import React, { useState, useEffect } from 'react';
import { ShieldCheck, CheckCircle2, Globe, Plus, Link as LinkIcon, ExternalLink } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useTenantBranding } from '@/components/TenantBrandingProvider';

interface BrandingForm {
  logo_url: string;
  primary_color: string;
  secondary_color: string;
  favicon_url: string;
  product_display_name: string;
  support_contact_email: string;
}

interface Domain {
  id: string;
  domain: string;
  verification_status: string;
  verification_token: string;
}

export default function ClientBrandingSettings() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [form, setForm] = useState<BrandingForm>({
    logo_url: '',
    primary_color: '#2563eb',
    secondary_color: '#1e40af',
    favicon_url: '',
    product_display_name: '',
    support_contact_email: ''
  });
  
  const [domains, setDomains] = useState<Domain[]>([]);
  const [newDomain, setNewDomain] = useState('');
  const [addingDomain, setAddingDomain] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
        if (!token) return;

        const [brandingRes, domainsRes] = await Promise.all([
          fetch('http://localhost:8000/branding', { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch('http://localhost:8000/domains', { headers: { 'Authorization': `Bearer ${token}` } })
        ]);

        if (brandingRes.ok) {
          const data = await brandingRes.json();
          if (data) {
            setForm({
              logo_url: data.logo_url || '',
              primary_color: data.primary_color || '#2563eb',
              secondary_color: data.secondary_color || '#1e40af',
              favicon_url: data.favicon_url || '',
              product_display_name: data.product_display_name || '',
              support_contact_email: data.support_contact_email || ''
            });
          }
        }
        
        if (domainsRes.ok) {
          const data = await domainsRes.json();
          setDomains(data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleSaveBranding = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
      const res = await fetch('http://localhost:8000/branding', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(form)
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to save branding');
      }
      setSuccess('Branding updated successfully! Refresh to apply changes.');
      setTimeout(() => setSuccess(null), 4000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAddDomain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDomain) return;
    setAddingDomain(true);
    setError(null);
    try {
      const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
      const res = await fetch('http://localhost:8000/domains', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ domain: newDomain })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to add domain');
      }
      const data = await res.json();
      setDomains([...domains, data]);
      setNewDomain('');
      setSuccess('Domain added. Please verify DNS records.');
      setTimeout(() => setSuccess(null), 4000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAddingDomain(false);
    }
  };

  const handleVerifyDomain = async (id: string) => {
    setError(null);
    try {
      const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
      const res = await fetch(`http://localhost:8000/domains/${id}/verify`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Verification failed');
      }
      const data = await res.json();
      setDomains(domains.map(d => d.id === id ? data : d));
      setSuccess('Domain verified successfully!');
      setTimeout(() => setSuccess(null), 4000);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRemoveDomain = async (id: string) => {
    setError(null);
    try {
      const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
      const res = await fetch(`http://localhost:8000/domains/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) {
        throw new Error('Failed to delete domain');
      }
      setDomains(domains.filter(d => d.id !== id));
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return <div className="p-8 text-slate-500">Loading settings...</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center space-x-2">
          <Link href="/dashboard/settings" className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors text-sm font-semibold">Settings</Link>
          <span className="text-slate-400">/</span>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Enterprise White-Labeling</h2>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Configure your custom brand appearance and domains (Tier 3 feature).</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 p-3.5 rounded-xl text-xs font-semibold">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 p-3.5 rounded-xl text-xs flex items-center space-x-2 font-semibold">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Branding Form */}
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-4">Brand Appearance</h3>
          
          <form onSubmit={handleSaveBranding} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Product Display Name</label>
              <input 
                type="text" 
                value={form.product_display_name} 
                onChange={e => setForm({...form, product_display_name: e.target.value})}
                placeholder="e.g. Acme Retention Console"
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-tenant-primary/50 transition-all"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Primary Color</label>
                <div className="flex space-x-2">
                  <input 
                    type="color" 
                    value={form.primary_color} 
                    onChange={e => setForm({...form, primary_color: e.target.value})}
                    className="h-9 w-9 rounded border border-slate-200 dark:border-slate-800 cursor-pointer"
                  />
                  <input 
                    type="text" 
                    value={form.primary_color} 
                    onChange={e => setForm({...form, primary_color: e.target.value})}
                    className="flex-1 px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-tenant-primary/50"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Secondary Color</label>
                <div className="flex space-x-2">
                  <input 
                    type="color" 
                    value={form.secondary_color} 
                    onChange={e => setForm({...form, secondary_color: e.target.value})}
                    className="h-9 w-9 rounded border border-slate-200 dark:border-slate-800 cursor-pointer"
                  />
                  <input 
                    type="text" 
                    value={form.secondary_color} 
                    onChange={e => setForm({...form, secondary_color: e.target.value})}
                    className="flex-1 px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-tenant-primary/50"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Logo URL</label>
              <input 
                type="url" 
                value={form.logo_url} 
                onChange={e => setForm({...form, logo_url: e.target.value})}
                placeholder="https://example.com/logo.png"
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-tenant-primary/50 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Favicon URL</label>
              <input 
                type="url" 
                value={form.favicon_url} 
                onChange={e => setForm({...form, favicon_url: e.target.value})}
                placeholder="https://example.com/favicon.ico"
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-tenant-primary/50 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Support Email</label>
              <input 
                type="email" 
                value={form.support_contact_email} 
                onChange={e => setForm({...form, support_contact_email: e.target.value})}
                placeholder="support@example.com"
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-tenant-primary/50 transition-all"
              />
            </div>

            <button 
              type="submit" 
              disabled={saving}
              className="w-full py-2.5 bg-tenant-primary hover:opacity-90 text-white font-semibold text-sm rounded-xl transition-all shadow-md mt-4 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Appearance'}
            </button>
          </form>
        </div>

        {/* Live Preview */}
        <div className="bg-slate-100 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 relative overflow-hidden flex flex-col">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-4">Live Preview</h3>
          <div 
            className="flex-1 border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 flex overflow-hidden shadow-inner"
            style={{ 
              ['--tenant-primary' as any]: form.primary_color,
              ['--tenant-secondary' as any]: form.secondary_color
            }}
          >
            {/* Mock Sidebar */}
            <div className="w-16 sm:w-48 border-r border-slate-100 dark:border-slate-800 p-3 sm:p-4 flex flex-col">
              <div className="flex items-center space-x-2 mb-6">
                {form.logo_url ? (
                  <img src={form.logo_url} alt="Logo" className="w-8 h-8 object-contain" />
                ) : (
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-tenant-primary to-tenant-secondary flex items-center justify-center flex-shrink-0">
                    <ShieldCheck className="w-4 h-4 text-white" />
                  </div>
                )}
                <div className="hidden sm:block text-sm font-bold truncate">
                  {form.product_display_name || 'ChurnGuard.AI'}
                </div>
              </div>
              <div className="space-y-2">
                <div className="h-8 rounded bg-tenant-primary/10 border border-tenant-primary/20" />
                <div className="h-8 rounded hover:bg-slate-50 dark:hover:bg-slate-800" />
                <div className="h-8 rounded hover:bg-slate-50 dark:hover:bg-slate-800" />
              </div>
            </div>
            {/* Mock Content */}
            <div className="flex-1 p-4 sm:p-6 flex flex-col space-y-4">
              <div className="h-6 w-32 rounded bg-slate-200 dark:bg-slate-800" />
              <div className="flex-1 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 flex items-center justify-center">
                <button className="px-4 py-2 bg-tenant-primary text-white rounded-lg text-xs font-bold shadow-md opacity-90 hover:opacity-100">
                  Primary Action
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Custom Domains */}
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-sm">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center space-x-2">
              <Globe className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Custom Domains</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Host your platform on your own branded domain.</p>
          </div>
        </div>

        <form onSubmit={handleAddDomain} className="my-4 flex items-center space-x-2">
          <input 
            type="text" 
            value={newDomain}
            onChange={e => setNewDomain(e.target.value)}
            placeholder="e.g. app.acme.com"
            className="flex-1 max-w-sm px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-tenant-primary/50 transition-all"
          />
          <button 
            type="submit" 
            disabled={addingDomain || !newDomain}
            className="py-2 px-4 bg-tenant-primary hover:opacity-90 text-white rounded-lg text-sm font-semibold shadow-md transition-all flex items-center space-x-2 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            <span>Add Domain</span>
          </button>
        </form>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Domain</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Configuration</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {domains.map(d => (
                <tr key={d.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-slate-200 flex items-center space-x-2">
                    <LinkIcon className="w-3.5 h-3.5 text-slate-400" />
                    <span>{d.domain}</span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                      d.verification_status === 'verified' 
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30' 
                        : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30'
                    }`}>
                      {d.verification_status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    {d.verification_status === 'pending' ? (
                      <div className="font-mono text-[10px] text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded inline-block">
                        TXT: {d.verification_token}
                      </div>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-right space-x-2">
                    {d.verification_status === 'pending' && (
                      <button 
                        onClick={() => handleVerifyDomain(d.id)}
                        className="text-xs font-semibold text-tenant-primary hover:underline"
                      >
                        Verify
                      </button>
                    )}
                    <button 
                      onClick={() => handleRemoveDomain(d.id)}
                      className="text-xs font-semibold text-red-500 hover:text-red-600 hover:underline"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
              {domains.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500 dark:text-slate-400">
                    No custom domains configured.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
