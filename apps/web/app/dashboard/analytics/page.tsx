import { MOCK_ANALYTICS } from '@/lib/demoData';
import ClientAnalytics from './ClientAnalytics';

export default function AnalyticsPage() {
  // Render instantly with high-performance initial analytics data
  return <ClientAnalytics initialAnalytics={MOCK_ANALYTICS} />;
}
