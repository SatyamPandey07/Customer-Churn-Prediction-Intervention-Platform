export type Customer = {
  id: string;
  external_ids: { stripe?: string; segment?: string; zendesk?: string };
  plan: 'enterprise' | 'premium' | 'basic';
  mrr: number;
  churn_probability: number;
  churn_risk_tier: 'critical' | 'high' | 'medium' | 'low';
  first_seen_at: string;
  last_seen_at: string;
  trend: number[];
};

export type Campaign = {
  id: string;
  name: string;
  trigger_rule: { risk_tier: string; mrr_gt?: number };
  intervention_type: string;
  channel: 'email' | 'sms' | 'slack' | 'in_app';
  template: string;
  status: 'active' | 'paused' | 'draft';
  created_at: string;
  sent_count: number;
  retained_count: number;
};

export type Integration = {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: string;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
  events_count_24h: number;
  config: Record<string, string>;
};

export const MOCK_CUSTOMERS: Customer[] = [
  {
    id: 'cus_8f93a210-4b11-4a7b-8910-c119284fa901',
    external_ids: { stripe: 'cus_stripe_99', zendesk: 'zen_102' },
    plan: 'enterprise',
    mrr: 4500.0,
    churn_probability: 0.89,
    churn_risk_tier: 'critical',
    first_seen_at: '2025-01-15T08:00:00Z',
    last_seen_at: '2026-08-01T14:22:00Z',
    trend: [12, 25, 45, 60, 78, 89],
  },
  {
    id: 'cus_3c9210aa-7e12-4211-9012-d8123984fa02',
    external_ids: { stripe: 'cus_stripe_88' },
    plan: 'enterprise',
    mrr: 3200.0,
    churn_probability: 0.76,
    churn_risk_tier: 'critical',
    first_seen_at: '2025-03-10T08:00:00Z',
    last_seen_at: '2026-08-02T09:15:00Z',
    trend: [10, 15, 30, 52, 68, 76],
  },
  {
    id: 'cus_1b829402-9a01-4c12-8812-e7123948fa03',
    external_ids: { stripe: 'cus_stripe_77' },
    plan: 'premium',
    mrr: 1200.0,
    churn_probability: 0.64,
    churn_risk_tier: 'high',
    first_seen_at: '2025-05-20T08:00:00Z',
    last_seen_at: '2026-08-02T11:45:00Z',
    trend: [8, 12, 20, 35, 50, 64],
  },
  {
    id: 'cus_5d910283-1192-4f22-9901-a6128492fa04',
    external_ids: { stripe: 'cus_stripe_66' },
    plan: 'premium',
    mrr: 950.0,
    churn_probability: 0.58,
    churn_risk_tier: 'high',
    first_seen_at: '2025-06-01T08:00:00Z',
    last_seen_at: '2026-08-02T16:00:00Z',
    trend: [5, 10, 18, 30, 42, 58],
  },
  {
    id: 'cus_7e102934-2283-4a11-8823-b5192840fa05',
    external_ids: { stripe: 'cus_stripe_55' },
    plan: 'basic',
    mrr: 250.0,
    churn_probability: 0.35,
    churn_risk_tier: 'medium',
    first_seen_at: '2025-08-12T08:00:00Z',
    last_seen_at: '2026-08-03T08:30:00Z',
    trend: [10, 15, 22, 28, 30, 35],
  },
  {
    id: 'cus_9a102945-3394-4b22-9934-c4192851fa06',
    external_ids: { stripe: 'cus_stripe_44' },
    plan: 'basic',
    mrr: 199.0,
    churn_probability: 0.12,
    churn_risk_tier: 'low',
    first_seen_at: '2025-09-01T08:00:00Z',
    last_seen_at: '2026-08-03T10:00:00Z',
    trend: [5, 8, 10, 11, 12, 12],
  },
  {
    id: 'cus_2b102956-4405-4c33-1045-d3192862fa07',
    external_ids: { stripe: 'cus_stripe_33' },
    plan: 'enterprise',
    mrr: 5000.0,
    churn_probability: 0.08,
    churn_risk_tier: 'low',
    first_seen_at: '2024-11-15T08:00:00Z',
    last_seen_at: '2026-08-03T11:15:00Z',
    trend: [4, 5, 6, 7, 8, 8],
  },
];

export const MOCK_EXPLANATIONS: Record<string, any> = {
  'cus_8f93a210-4b11-4a7b-8910-c119284fa901': {
    risk_tier: 'critical',
    top_drivers: [
      { feature: 'usage_trend_30d', shap_value: 0.38, human_readable: 'Feature adoption dropped by 54% over the last 30 days' },
      { feature: 'failed_payments_90d', shap_value: 0.29, human_readable: '2 failed invoice payments recorded in the last 60 days' },
      { feature: 'support_ticket_spike', shap_value: 0.18, human_readable: '4 unresolved urgent support tickets opened in 14 days' },
      { feature: 'seat_shrinkage', shap_value: 0.12, human_readable: 'Active seat count shrank from 24 down to 10 seats' },
    ],
    intervention_recommendation: {
      strategy: 'Executive Sponsor Outreach + 15% Invoice Discount',
      copy: 'Hi Executive Team, We noticed seat utilization dropped over the last month. We would love to offer a complimentary technical review with our Lead Architect to get your team unblocked, plus lock in a 15% renewal discount.',
      recommended_channel: 'email',
    },
  },
};

export const MOCK_CAMPAIGNS: Campaign[] = [
  {
    id: 'cmp_101',
    name: 'Executive Save Offer - Enterprise Critical Risk',
    trigger_rule: { risk_tier: 'critical', mrr_gt: 1000 },
    intervention_type: 'executive_outreach',
    channel: 'email',
    template: 'Hi {{customer_name}}, We noticed usage changes on your account and want to offer a complimentary dedicated CSM session...',
    status: 'active',
    created_at: '2026-07-01T10:00:00Z',
    sent_count: 42,
    retained_count: 31,
  },
  {
    id: 'cmp_102',
    name: 'Payment Recovery & Slack Alert',
    trigger_rule: { risk_tier: 'high' },
    intervention_type: 'payment_retry_prompt',
    channel: 'slack',
    template: '⚠️ Customer {{customer_id}} has 2 failed payment attempts. Automatic retry scheduled in 48h.',
    status: 'active',
    created_at: '2026-07-15T14:30:00Z',
    sent_count: 88,
    retained_count: 65,
  },
  {
    id: 'cmp_103',
    name: 'In-App Onboarding Re-Engagement',
    trigger_rule: { risk_tier: 'medium' },
    intervention_type: 'feature_walkthrough',
    channel: 'in_app',
    template: 'Unlock advanced analytics! Schedule 15 minutes with our product specialist.',
    status: 'paused',
    created_at: '2026-07-20T09:15:00Z',
    sent_count: 120,
    retained_count: 74,
  },
];

export const MOCK_INTEGRATIONS: Integration[] = [
  {
    id: 'stripe',
    name: 'Stripe Billing & Subscriptions',
    category: 'Billing & Payments',
    description: 'Ingests subscription creation, plan upgrades, downgrades, invoice payments, and failed payment events.',
    icon: 'stripe',
    status: 'connected',
    last_sync: '2026-08-03T11:45:00Z',
    events_count_24h: 1420,
    config: { api_key: 'sk_live_stripe_••••••••9821', webhook_secret: 'whsec_••••••••4412' }
  },
  {
    id: 'segment',
    name: 'Segment Customer Data Platform',
    category: 'Product Analytics',
    description: 'Ingests real-time user track events, page views, feature adoption, and user identify calls.',
    icon: 'segment',
    status: 'connected',
    last_sync: '2026-08-03T11:50:00Z',
    events_count_24h: 8940,
    config: { write_key: 'seg_write_••••••••1102' }
  },
  {
    id: 'amplitude',
    name: 'Amplitude Behavioral Analytics',
    category: 'Product Analytics',
    description: 'Tracks session frequency, feature retention curves, and active user drop-off trends.',
    icon: 'amplitude',
    status: 'connected',
    last_sync: '2026-08-03T11:30:00Z',
    events_count_24h: 5120,
    config: { api_key: 'amp_api_••••••••8819', secret_key: 'amp_sec_••••••••3311' }
  },
  {
    id: 'zendesk',
    name: 'Zendesk Customer Support',
    category: 'Customer Success',
    description: 'Ingests support ticket spikes, urgent ticket volume, resolution times, and CSAT scores.',
    icon: 'zendesk',
    status: 'connected',
    last_sync: '2026-08-03T10:15:00Z',
    events_count_24h: 340,
    config: { subdomain: 'acme-support', api_token: 'zen_tok_••••••••5519' }
  },
  {
    id: 'salesforce',
    name: 'Salesforce CRM',
    category: 'Sales & Accounts',
    description: 'Syncs seat contract changes, renewal dates, executive contacts, and opportunity health.',
    icon: 'salesforce',
    status: 'disconnected',
    last_sync: null,
    events_count_24h: 0,
    config: {}
  },
  {
    id: 'hubspot',
    name: 'HubSpot CRM & Marketing',
    category: 'Sales & Accounts',
    description: 'Tracks account lifecycle stages, email engagement, and deal status changes.',
    icon: 'hubspot',
    status: 'disconnected',
    last_sync: null,
    events_count_24h: 0,
    config: {}
  },
  {
    id: 'webhook',
    name: 'Custom HTTP Webhook Endpoint',
    category: 'Realtime API',
    description: 'Stream custom JSON event payloads directly to ChurnGuard.AI\'s real-time ingestion pipeline.',
    icon: 'webhook',
    status: 'connected',
    last_sync: '2026-08-03T11:52:00Z',
    events_count_24h: 12800,
    config: { endpoint_url: 'https://api.churnguard.ai/webhooks/v1/ingest', signing_secret: 'wh_sign_••••••••9901' }
  }
];

export const MOCK_ANALYTICS = {
  total_mrr_at_risk: 9850.0,
  customers_at_risk_count: 4,
  avg_churn_risk: 0.49,
  revenue_saved_ytd: 42800.0,
  roi_multiple: 8.4,
  channel_performance: [
    { channel: 'Email', sent: 140, retained: 96, success_rate: 0.686, lower_ci: 0.60, upper_ci: 0.76 },
    { channel: 'Slack Webhook', sent: 92, retained: 71, success_rate: 0.771, lower_ci: 0.67, upper_ci: 0.85 },
    { channel: 'SMS Alert', sent: 50, retained: 32, success_rate: 0.640, lower_ci: 0.50, upper_ci: 0.76 },
    { channel: 'In-App Dialog', sent: 210, retained: 135, success_rate: 0.642, lower_ci: 0.57, upper_ci: 0.70 },
  ],
  risk_distribution: [
    { name: 'Critical (>75%)', count: 2, mrr: 7700.0, fill: '#ef4444' },
    { name: 'High (50-75%)', count: 2, mrr: 2150.0, fill: '#f97316' },
    { name: 'Medium (25-50%)', count: 1, mrr: 250.0, fill: '#eab308' },
    { name: 'Low (<25%)', count: 2, mrr: 5199.0, fill: '#22c55e' },
  ],
};
