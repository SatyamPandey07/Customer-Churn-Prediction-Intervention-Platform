"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ShieldCheck, UserCheck, Eye, Sparkles, Activity, Layers, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function LoginPage() {
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('Password123!');
  const [tenantName, setTenantName] = useState('');
  const [subdomain, setSubdomain] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e?: React.FormEvent, overrideEmail?: string, overridePassword?: string, overrideRole?: string) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);

    const loginEmail = overrideEmail || email;
    const loginPassword = overridePassword || password;

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginEmail, password: loginPassword, role: overrideRole }),
      });

      if (res.ok) {
        router.push('/dashboard');
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || 'Login failed. Check your credentials or try a Demo Account below.');
      }
    } catch (err) {
      setError('Connection error. Please try one of the instant Demo Accounts.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_name: tenantName, subdomain, email, password }),
      });

      if (res.ok) {
        router.push('/dashboard');
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || 'Signup failed.');
      }
    } catch (err) {
      setError('Signup failed. Trying demo mode session...');
      router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const triggerDemoLogin = (role: 'admin' | 'analyst' | 'viewer') => {
    if (role === 'admin') {
      setEmail('admin@example.com');
      setPassword('Password123!');
      handleLogin(undefined, 'admin@example.com', 'Password123!', 'admin');
    } else if (role === 'analyst') {
      setEmail('analyst@example.com');
      setPassword('Password123!');
      handleLogin(undefined, 'analyst@example.com', 'Password123!', 'analyst');
    } else {
      setEmail('viewer@example.com');
      setPassword('Password123!');
      handleLogin(undefined, 'viewer@example.com', 'Password123!', 'viewer');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden font-sans">
      {/* Dynamic Background Glow Elements */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-600/15 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[400px] bg-indigo-600/10 blur-[100px] rounded-full pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center">
        <div className="inline-flex items-center justify-center space-x-3 bg-gradient-to-r from-blue-600/20 to-indigo-600/20 border border-blue-500/30 px-4 py-1.5 rounded-full text-blue-400 text-xs font-semibold uppercase tracking-widest mb-4">
          <Sparkles className="w-4 h-4 text-blue-400 animate-pulse" />
          <span>Enterprise AI Churn Intelligence</span>
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-white font-serif">
          Churn<span className="text-blue-500 font-sans">Platform</span>
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Predict churn risk, generate SHAP explanations, & automate targeted retention campaigns.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 py-8 px-6 shadow-2xl rounded-2xl sm:px-10">
          
          {/* Tab Switcher */}
          <div className="flex bg-slate-950/60 p-1 rounded-xl mb-6 border border-slate-800/60">
            <button
              onClick={() => setActiveTab('signin')}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
                activeTab === 'signin'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setActiveTab('signup')}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
                activeTab === 'signup'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Create Tenant Account
            </button>
          </div>

          {error && (
            <div className="mb-4 bg-red-950/80 border border-red-500/40 p-3 rounded-lg text-xs text-red-300 flex items-start space-x-2">
              <span className="font-bold">•</span>
              <span>{error}</span>
            </div>
          )}

          {activeTab === 'signin' ? (
            <form className="space-y-4" onSubmit={handleLogin}>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                  placeholder="admin@example.com"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                  placeholder="••••••••••••"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-sm rounded-lg shadow-lg shadow-blue-500/20 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {loading ? (
                  <span>Authenticating...</span>
                ) : (
                  <>
                    <span>Sign In to Dashboard</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={handleSignup}>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Company / Tenant Name
                </label>
                <input
                  type="text"
                  required
                  value={tenantName}
                  onChange={(e) => setTenantName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                  placeholder="Acme Inc."
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Subdomain Slug
                </label>
                <input
                  type="text"
                  required
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                  className="w-full px-3.5 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                  placeholder="acme"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Owner Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                  placeholder="owner@acme.com"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Master Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                  placeholder="Password123!"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-sm rounded-lg shadow-lg shadow-blue-500/20 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all flex items-center justify-center space-x-2"
              >
                <span>Create Tenant Account</span>
                <CheckCircle2 className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* 1-Click Instant Demo Login Access */}
          <div className="mt-8 pt-6 border-t border-slate-800/80">
            <div className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              ⚡ Instant 1-Click Demo Logins
            </div>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => triggerDemoLogin('admin')}
                className="py-2 px-2.5 bg-slate-950 hover:bg-slate-800/80 border border-blue-500/30 rounded-lg text-xs font-medium text-blue-300 transition-all flex flex-col items-center justify-center space-y-1 hover:scale-[1.02]"
              >
                <ShieldCheck className="w-4 h-4 text-blue-400" />
                <span>Admin / Owner</span>
              </button>

              <button
                type="button"
                onClick={() => triggerDemoLogin('analyst')}
                className="py-2 px-2.5 bg-slate-950 hover:bg-slate-800/80 border border-purple-500/30 rounded-lg text-xs font-medium text-purple-300 transition-all flex flex-col items-center justify-center space-y-1 hover:scale-[1.02]"
              >
                <UserCheck className="w-4 h-4 text-purple-400" />
                <span>CSM Analyst</span>
              </button>

              <button
                type="button"
                onClick={() => triggerDemoLogin('viewer')}
                className="py-2 px-2.5 bg-slate-950 hover:bg-slate-800/80 border border-emerald-500/30 rounded-lg text-xs font-medium text-emerald-300 transition-all flex flex-col items-center justify-center space-y-1 hover:scale-[1.02]"
              >
                <Eye className="w-4 h-4 text-emerald-400" />
                <span>Read-Only</span>
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
