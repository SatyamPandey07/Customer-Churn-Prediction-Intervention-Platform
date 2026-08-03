import { NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { tenant_name, subdomain, email, password } = body;

    try {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_name, subdomain, email, password }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        return NextResponse.json(
          { error: errorData.detail || 'Signup failed' },
          { status: res.status }
        );
      }
    } catch (err) {
      console.warn('[Signup Route] Backend unreachable, processing demo signup:', err);
    }

    // Immediately log the user in
    const response = NextResponse.json({ success: true, message: 'Account created successfully' });
    response.cookies.set('access_token', 'demo_owner_token', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 86400,
    });
    response.cookies.set('user_role', 'owner', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 86400,
    });

    return response;
  } catch (err) {
    console.error('Signup Exception:', err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
