"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ShieldCheck, UserCheck, Eye, Sparkles, ArrowRight, CheckCircle2, Sun, Moon } from 'lucide-react';
import { useTheme } from '@/components/ThemeProvider';

export default function LoginPage() {
  const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('Password123!');
  const [tenantName, setTenantName] = useState('');
  const [subdomain, setSubdomain] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();

  // Set auth cookies directly client-side (static export compatible)
  const setAuthCookies = (role: string, token: string) => {
    const maxAge = 86400;
    document.cookie = `access_token=${token}; path=/; max-age=${maxAge}; SameSite=Strict`;
    document.cookie = `user_role=${role}; path=/; max-age=${maxAge}; SameSite=Strict`;
  };

  const handleLogin = async (e?: React.FormEvent, overrideEmail?: string, overridePassword?: string, overrideRole?: string) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);

    const loginEmail = overrideEmail || email;
    const loginPassword = overridePassword || password;
    const role = overrideRole || (loginEmail.includes('analyst') ? 'analyst' : loginEmail.includes('viewer') ? 'viewer' : 'admin');

    try {
      // Try backend API first if configured
      const apiBase = process.env.NEXT_PUBLIC_API_URL;
      if (apiBase) {
        const formData = new URLSearchParams();
        formData.append('username', loginEmail);
        formData.append('password', loginPassword);
        const res = await fetch(`${apiBase}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData.toString(),
        });
        if (res.ok) {
          const data = await res.json();
          setAuthCookies(data.role || role, data.access_token);
          router.push('/dashboard');
          return;
        }
      }
    } catch (_) {}

    // Demo / fallback: accept known demo credentials
    const validDemoEmails = ['admin@example.com', 'analyst@example.com', 'viewer@example.com'];
    if (validDemoEmails.includes(loginEmail) && loginPassword === 'Password123!') {
      setAuthCookies(role, `demo_token_${role}`);
      router.push('/dashboard');
    } else if (loginEmail && loginPassword) {
      // Accept any credentials in demo mode
      setAuthCookies(role, `demo_token_${role}`);
      router.push('/dashboard');
    } else {
      setError('Please enter your email and password.');
    }
    setLoading(false);
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    setAuthCookies('owner', 'demo_owner_token');
    router.push('/dashboard');
    setLoading(false);
  };

  const triggerDemoLogin = (role: 'admin' | 'analyst' | 'viewer') => {
    setAuthCookies(role, `demo_token_${role}`);
    router.push('/dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden font-sans transition-colors duration-300">
      {/* Top Header Controls: Theme Switcher */}
      <div className="absolute top-6 right-8 z-30">
        <button
          onClick={toggleTheme}
          className="px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-200 shadow-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition-all flex items-center space-x-2"
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? (
            <>
              <Moon className="w-4 h-4 text-indigo-600" />
              <span>Dark Mode</span>
            </>
          ) : (
            <>
              <Sun className="w-4 h-4 text-amber-400" />
              <span>Light Mode</span>
            </>
          )}
        </button>
      </div>

      {/* Dynamic Background Glow Elements */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/10 dark:bg-blue-600/15 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[400px] bg-indigo-500/10 dark:bg-indigo-600/10 blur-[100px] rounded-full pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center">
        <div className="inline-flex items-center justify-center space-x-2.5 bg-blue-500/10 dark:bg-gradient-to-r dark:from-blue-600/20 dark:to-indigo-600/20 border border-blue-500/20 dark:border-blue-500/30 px-4 py-1.5 rounded-full text-blue-600 dark:text-blue-400 text-xs font-bold uppercase tracking-widest mb-4">
          <ShieldCheck className="w-4 h-4 text-blue-500 animate-pulse" />
          <span>ChurnGuard.AI</span>
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white font-serif">
          ChurnGuard<span className="text-blue-600 dark:text-blue-500 font-sans">.AI</span>
        </h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Predict churn risk, generate SHAP explanations, & automate targeted retention campaigns.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-white/90 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200 dark:border-slate-800/80 py-8 px-6 shadow-xl dark:shadow-2xl rounded-2xl sm:px-10 transition-colors">
          
          {/* Tab Switcher */}
          <div className="flex bg-slate-100 dark:bg-slate-950/60 p-1 rounded-xl mb-6 border border-slate-200 dark:border-slate-800/60">
            <button
              onClick={() => setActiveTab('signin')}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${
                activeTab === 'signin'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setActiveTab('signup')}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${
                activeTab === 'signup'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              Create Tenant Account
            </button>
          </div>

          {error && (
            <div className="mb-4 bg-red-500/10 border border-red-500/30 p-3 rounded-xl text-xs text-red-600 dark:text-red-300 flex items-start space-x-2 font-medium">
              <span className="font-bold">•</span>
              <span>{error}</span>
            </div>
          )}

          {activeTab === 'signin' ? (
            <form className="space-y-4" onSubmit={handleLogin}>
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 rounded-xl text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                  placeholder="admin@example.com"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 rounded-xl text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                  placeholder="••••••••••••"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-blue-500/20 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
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
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                  Company / Tenant Name
                </label>
                <input
                  type="text"
                  required
                  value={tenantName}
                  onChange={(e) => setTenantName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 rounded-xl text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                  placeholder="Acme Inc."
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                  Subdomain Slug
                </label>
                <input
                  type="text"
                  required
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                  className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 rounded-xl text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                  placeholder="acme"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                  Owner Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 rounded-xl text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                  placeholder="owner@acme.com"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
                  Master Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 rounded-xl text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                  placeholder="Password123!"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-blue-500/20 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all flex items-center justify-center space-x-2"
              >
                <span>Create Tenant Account</span>
                <CheckCircle2 className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* 1-Click Instant Demo Login Access */}
          <div className="mt-8 pt-6 border-t border-slate-200 dark:border-slate-800/80">
            <div className="text-center text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
              ⚡ Instant 1-Click Demo Logins
            </div>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => triggerDemoLogin('admin')}
                className="py-2 px-2.5 bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-800/80 border border-blue-500/30 rounded-xl text-xs font-semibold text-blue-600 dark:text-blue-400 transition-all flex flex-col items-center justify-center space-y-1 hover:scale-[1.02]"
              >
                <ShieldCheck className="w-4 h-4 text-blue-500" />
                <span>Admin / Owner</span>
              </button>

              <button
                type="button"
                onClick={() => triggerDemoLogin('analyst')}
                className="py-2 px-2.5 bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-800/80 border border-purple-500/30 rounded-xl text-xs font-semibold text-purple-600 dark:text-purple-400 transition-all flex flex-col items-center justify-center space-y-1 hover:scale-[1.02]"
              >
                <UserCheck className="w-4 h-4 text-purple-500" />
                <span>CSM Analyst</span>
              </button>

              <button
                type="button"
                onClick={() => triggerDemoLogin('viewer')}
                className="py-2 px-2.5 bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-800/80 border border-emerald-500/30 rounded-xl text-xs font-semibold text-emerald-600 dark:text-emerald-400 transition-all flex flex-col items-center justify-center space-y-1 hover:scale-[1.02]"
              >
                <Eye className="w-4 h-4 text-emerald-500" />
                <span>Read-Only</span>
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
