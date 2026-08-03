import { MOCK_CAMPAIGNS } from '@/lib/demoData';
import ClientCampaigns from './ClientCampaigns';

export default function CampaignsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900">Campaigns</h1>
      {/* userRole resolved client-side in ClientCampaigns */}
      <ClientCampaigns initialCampaigns={MOCK_CAMPAIGNS} userRole="admin" />
    </div>
  );
}
