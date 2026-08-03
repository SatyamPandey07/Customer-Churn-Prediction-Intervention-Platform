import { cookies } from 'next/headers';
import { MOCK_CUSTOMERS, MOCK_CAMPAIGNS, MOCK_ANALYTICS, MOCK_INTEGRATIONS } from './demoData';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const cookieStore = cookies();
  const token = cookieStore.get('access_token')?.value;

  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      next: { revalidate: 0 },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (err) {
    console.warn(`[fetchAPI] Falling back to demo data for ${endpoint}:`, err);
    if (endpoint.startsWith('/customers')) {
      return MOCK_CUSTOMERS;
    }
    if (endpoint.startsWith('/campaigns')) {
      return MOCK_CAMPAIGNS;
    }
    if (endpoint.startsWith('/analytics')) {
      return MOCK_ANALYTICS;
    }
    if (endpoint.startsWith('/integrations')) {
      return MOCK_INTEGRATIONS;
    }
    return [];
  }
}
