import { fetchAPI } from '@/lib/api';
import ClientIntegrations from './ClientIntegrations';

export default async function IntegrationsPage() {
  let initialIntegrations = [];
  try {
    initialIntegrations = await fetchAPI('/integrations');
  } catch (e) {
    console.error('Failed to fetch integrations:', e);
  }

  return <ClientIntegrations initialIntegrations={initialIntegrations} />;
}
