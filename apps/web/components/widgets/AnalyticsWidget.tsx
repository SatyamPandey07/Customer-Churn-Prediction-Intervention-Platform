import React from 'react';
import { WidgetConfig } from './WidgetRegistry';
import AnalyticsChartRenderer, { ChartConfig } from './AnalyticsChartRenderer';

interface AnalyticsWidgetProps {
  widgetConfig: WidgetConfig;
  analyticsData: any;
}

export default function AnalyticsWidget({ widgetConfig, analyticsData }: AnalyticsWidgetProps) {
  // Map standard data formats to what the ChartRenderer expects
  
  let data: any[] = [];
  let chartConfig: ChartConfig = {
    visualization_type: widgetConfig.config.visualization_type || 'bar',
    xAxisKey: 'name',
    dataKeys: ['value'],
    time_range: widgetConfig.config.time_range,
    granularity: widgetConfig.config.granularity
  };
  let title = '';

  switch (widgetConfig.type) {
    case 'ANALYTICS_ROI':
      title = 'ROI & Revenue Saved';
      // For ROI, the data might be a single object, we can array-ify it or use 'stat'
      if (chartConfig.visualization_type === 'stat') {
        data = [{ value: analyticsData.revenue_saved_ytd }];
        chartConfig.dataKeys = ['value'];
      } else {
        // Mock a trend for line/bar charts
        data = [
          { name: 'Q1', value: analyticsData.revenue_saved_ytd * 0.2 },
          { name: 'Q2', value: analyticsData.revenue_saved_ytd * 0.3 },
          { name: 'Q3', value: analyticsData.revenue_saved_ytd * 0.5 }
        ];
        chartConfig.dataKeys = ['value'];
      }
      break;

    case 'ANALYTICS_INTERVENTIONS':
      title = 'Intervention Channel Performance';
      data = analyticsData.channel_performance || [];
      chartConfig.xAxisKey = 'channel';
      
      if (chartConfig.visualization_type === 'pie') {
        chartConfig.dataKeys = ['retained']; // Pie charts usually need one key to sum
      } else {
        chartConfig.dataKeys = ['success_rate'];
      }
      break;

    case 'ANALYTICS_COHORTS':
      title = 'Cohort Risk Distribution';
      data = analyticsData.risk_distribution || [];
      chartConfig.xAxisKey = 'name';
      chartConfig.dataKeys = ['count'];
      break;

    case 'ANALYTICS_RAR':
      title = 'Revenue at Risk Horizon';
      // Mock some time-series data for RAR
      data = [
        { date: '2023-01', rar: 12000 },
        { date: '2023-02', rar: 15000 },
        { date: '2023-03', rar: 9000 },
        { date: '2023-04', rar: 11000 },
        { date: '2023-05', rar: 8500 }
      ];
      chartConfig.xAxisKey = 'date';
      chartConfig.dataKeys = ['rar'];
      break;

    default:
      return <div>No analytics mapping for this widget type</div>;
  }

  return (
    <div className="w-full h-full p-2">
      <AnalyticsChartRenderer data={data} config={chartConfig} title={title} />
    </div>
  );
}
