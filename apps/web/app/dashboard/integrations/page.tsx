import { MOCK_INTEGRATIONS } from '@/lib/demoData';
import ClientIntegrations from './ClientIntegrations';

export default function IntegrationsPage() {
  return <ClientIntegrations initialIntegrations={MOCK_INTEGRATIONS} />;
}
