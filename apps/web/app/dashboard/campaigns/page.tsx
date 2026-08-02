import { cookies } from 'next/headers';
import { fetchAPI } from '@/lib/api';
import ClientCampaigns from './ClientCampaigns';

export default async function CampaignsPage() {
  const cookieStore = cookies();
  const role = cookieStore.get('user_role')?.value || 'viewer';
  
  let campaigns = [];
  try {
    campaigns = await fetchAPI('/campaigns');
  } catch (e) {
    console.error('Failed to fetch campaigns', e);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900">Campaigns</h1>
      <ClientCampaigns initialCampaigns={campaigns} userRole={role} />
    </div>
  );
}
