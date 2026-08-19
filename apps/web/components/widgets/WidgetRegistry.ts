import { FC } from 'react';

export enum WidgetType {
  METRICS_SUMMARY = 'METRICS_SUMMARY',
  CHURN_RISK_TABLE = 'CHURN_RISK_TABLE',
  ANOMALY_FEED = 'ANOMALY_FEED',
  INTERVENTIONS_FEED = 'INTERVENTIONS_FEED',
  ANALYTICS_ROI = 'ANALYTICS_ROI',
  ANALYTICS_INTERVENTIONS = 'ANALYTICS_INTERVENTIONS',
  ANALYTICS_COHORTS = 'ANALYTICS_COHORTS',
  ANALYTICS_RAR = 'ANALYTICS_RAR'
}

export const SUPPORTED_VISUALIZATIONS: Record<WidgetType, string[]> = {
  [WidgetType.METRICS_SUMMARY]: [],
  [WidgetType.CHURN_RISK_TABLE]: [],
  [WidgetType.ANOMALY_FEED]: [],
  [WidgetType.INTERVENTIONS_FEED]: [],
  [WidgetType.ANALYTICS_ROI]: ['stat', 'line', 'bar'],
  [WidgetType.ANALYTICS_INTERVENTIONS]: ['bar', 'pie', 'table'],
  [WidgetType.ANALYTICS_COHORTS]: ['pie', 'bar', 'table'],
  [WidgetType.ANALYTICS_RAR]: ['line', 'bar', 'stat', 'table']
};

export interface WidgetConfig {
  id: string; // unique instance id
  type: WidgetType;
  size?: 'small' | 'medium' | 'large' | 'full'; // legacy field
  config: Record<string, any>;
}

export interface WidgetProps {
  config: Record<string, any>;
  data?: any; // injected dashboard data
}

export const WIDGET_DEF = {
  [WidgetType.METRICS_SUMMARY]: { name: 'Metrics Summary Cards', minW: 4, minH: 2, defaultConfig: {} },
  [WidgetType.CHURN_RISK_TABLE]: { name: 'Churn Risk Telemetry Table', minW: 6, minH: 3, defaultConfig: { risk_tier_filter: 'all', row_limit: 10 } },
  [WidgetType.ANOMALY_FEED]: { name: 'Anomaly Feed', minW: 3, minH: 2, defaultConfig: { limit: 5 } },
  [WidgetType.INTERVENTIONS_FEED]: { name: 'Recent Interventions', minW: 3, minH: 2, defaultConfig: { limit: 5 } },
  [WidgetType.ANALYTICS_ROI]: { name: 'ROI Analytics', minW: 3, minH: 2, defaultConfig: { visualization_type: 'stat', time_range: 'ytd', granularity: 'monthly' } },
  [WidgetType.ANALYTICS_INTERVENTIONS]: { name: 'Intervention Performance', minW: 4, minH: 3, defaultConfig: { visualization_type: 'bar', time_range: '30d', granularity: 'daily' } },
  [WidgetType.ANALYTICS_COHORTS]: { name: 'Cohort Breakdown', minW: 4, minH: 3, defaultConfig: { visualization_type: 'pie' } },
  [WidgetType.ANALYTICS_RAR]: { name: 'Revenue at Risk', minW: 6, minH: 3, defaultConfig: { visualization_type: 'line', time_range: '90d', granularity: 'monthly' } }
};
