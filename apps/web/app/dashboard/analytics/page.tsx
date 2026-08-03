import { fetchAPI } from '@/lib/api';
import ClientAnalytics from './ClientAnalytics';

export default async function AnalyticsPage() {
  let analyticsData = null;
  try {
    analyticsData = await fetchAPI('/analytics');
  } catch (e) {
    console.error('Failed to fetch analytics:', e);
  }

  return <ClientAnalytics initialAnalytics={analyticsData} />;
}
