"use client";

import { MOCK_ANALYTICS } from '@/lib/demoData';
import { WidgetType, WIDGET_DEF } from '@/components/widgets/WidgetRegistry';
import AnalyticsWidget from '@/components/widgets/AnalyticsWidget';

export default function ClientAnalytics({ initialAnalytics }: { initialAnalytics?: any }) {
  const analytics = initialAnalytics || MOCK_ANALYTICS;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Outcome Analytics & ROI Calculation</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Track intervention success rates, outcomes, and revenue preserved over time.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* ROI Stats */}
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm h-64">
          <AnalyticsWidget 
            widgetConfig={{ id: 'roi-stat', type: WidgetType.ANALYTICS_ROI, size: 'medium', config: { visualization_type: 'stat' } }} 
            analyticsData={analytics} 
          />
        </div>
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm h-64">
          <AnalyticsWidget 
            widgetConfig={{ id: 'roi-bar', type: WidgetType.ANALYTICS_ROI, size: 'medium', config: { visualization_type: 'bar', time_range: 'ytd' } }} 
            analyticsData={analytics} 
          />
        </div>
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm h-64">
          <AnalyticsWidget 
            widgetConfig={{ id: 'rar-stat', type: WidgetType.ANALYTICS_RAR, size: 'medium', config: { visualization_type: 'stat' } }} 
            analyticsData={analytics} 
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm h-96">
          <AnalyticsWidget 
            widgetConfig={{ id: 'rar-line', type: WidgetType.ANALYTICS_RAR, size: 'large', config: { visualization_type: 'line', time_range: '90d' } }} 
            analyticsData={analytics} 
          />
        </div>
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm h-96">
          <AnalyticsWidget 
            widgetConfig={{ id: 'interventions-bar', type: WidgetType.ANALYTICS_INTERVENTIONS, size: 'large', config: { visualization_type: 'bar', time_range: 'all' } }} 
            analyticsData={analytics} 
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm h-96">
          <AnalyticsWidget 
            widgetConfig={{ id: 'cohorts-pie', type: WidgetType.ANALYTICS_COHORTS, size: 'medium', config: { visualization_type: 'pie' } }} 
            analyticsData={analytics} 
          />
        </div>
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm h-96">
          <AnalyticsWidget 
            widgetConfig={{ id: 'interventions-table', type: WidgetType.ANALYTICS_INTERVENTIONS, size: 'medium', config: { visualization_type: 'table' } }} 
            analyticsData={analytics} 
          />
        </div>
      </div>
    </div>
  );
}
