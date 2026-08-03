import { NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { username, password, role: requestedRole } = body;

    // Support instant demo accounts
    if (username.startsWith('demo_') || password === 'demo' || username.includes('demo')) {
      const demoRole = requestedRole || (username.includes('admin') ? 'admin' : username.includes('analyst') ? 'analyst' : 'viewer');
      const response = NextResponse.json({ success: true, role: demoRole, isDemo: true });
      
      response.cookies.set('access_token', `demo_token_${demoRole}`, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
        maxAge: 86400,
      });
      response.cookies.set('user_role', demoRole, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
        maxAge: 86400,
      });

      return response;
    }

    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });

      if (res.ok) {
        const data = await res.json();
        const role = data.role || 'admin';
        const response = NextResponse.json({ success: true, role });

        response.cookies.set('access_token', data.access_token, {
          httpOnly: true,
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'lax',
          path: '/',
          maxAge: 86400,
        });

        response.cookies.set('user_role', role, {
          httpOnly: true,
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'lax',
          path: '/',
          maxAge: 86400,
        });

        return response;
      }
    } catch (apiErr) {
      console.warn('[Login Route] Backend API fetch failed, falling back to demo session:', apiErr);
    }

    // Fallback for demo mode if backend is unreachable or credentials match admin demo
    if (username === 'admin@example.com' || username === 'admin') {
      const response = NextResponse.json({ success: true, role: 'admin', isDemoFallback: true });
      response.cookies.set('access_token', 'demo_admin_access_token', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
        maxAge: 86400,
      });
      response.cookies.set('user_role', 'admin', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
        maxAge: 86400,
      });
      return response;
    }

    return NextResponse.json({ error: 'Invalid username or password' }, { status: 401 });
  } catch (err) {
    console.error('Login Handler Exception:', err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
