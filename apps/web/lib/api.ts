import { MOCK_CUSTOMERS, MOCK_CAMPAIGNS, MOCK_ANALYTICS, MOCK_INTEGRATIONS } from './demoData';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  // If no API URL configured, use demo data immediately
  if (!API_BASE) {
    return getDemoData(endpoint);
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      next: { revalidate: 0 },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (err) {
    console.warn(`[fetchAPI] Falling back to demo data for ${endpoint}:`, err);
    return getDemoData(endpoint);
  }
}

function getDemoData(endpoint: string) {
  if (endpoint.startsWith('/customers')) return MOCK_CUSTOMERS;
  if (endpoint.startsWith('/campaigns')) return MOCK_CAMPAIGNS;
  if (endpoint.startsWith('/analytics')) return MOCK_ANALYTICS;
  if (endpoint.startsWith('/integrations')) return MOCK_INTEGRATIONS;
  return [];
}
