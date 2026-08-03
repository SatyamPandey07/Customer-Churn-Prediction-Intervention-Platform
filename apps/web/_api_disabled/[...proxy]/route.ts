import { NextRequest, NextResponse } from 'next/server';

// Required for output: 'export' — unused in static mode
export function generateStaticParams() {
  return [];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function handleProxy(request: NextRequest, { params }: { params: { proxy: string[] } }) {
  const path = '/' + params.proxy.join('/');
  const token = request.cookies.get('access_token')?.value;

  const headers = new Headers();
  headers.set('Content-Type', request.headers.get('Content-Type') || 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let body = null;
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    body = await request.text();
  }

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: request.method,
      headers,
      body
    });

    const data = await res.text();
    let json = null;
    try {
      json = JSON.parse(data);
    } catch (e) {
      // not json
    }

    return NextResponse.json(json || data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ error: 'Proxy error' }, { status: 500 });
  }
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const DELETE = handleProxy;
export const PATCH = handleProxy;
