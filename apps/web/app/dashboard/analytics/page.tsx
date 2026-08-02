import { fetchAPI } from '@/lib/api';
import ClientAnalytics from './ClientAnalytics';

export default async function AnalyticsPage() {
  let performance = [];
  let roi = null;
  
  try {
    performance = await fetchAPI('/analytics/intervention-performance');
  } catch (e) {
    console.error('Failed to fetch performance', e);
  }

  try {
    roi = await fetchAPI('/analytics/roi-report');
  } catch (e) {
    console.error('Failed to fetch roi', e);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900">Analytics & ROI</h1>
      <ClientAnalytics performance={performance} roi={roi} />
    </div>
  );
}
