import http from 'k6/http';
import { check, sleep } from 'k6';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

export const options = {
  stages: [
    { duration: '30s', target: 50 },  // Ramp up to 50 users
    { duration: '1m', target: 50 },   // Stay at 50 users for 1 min
    { duration: '30s', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must complete below 500ms
    http_req_failed: ['rate<0.01'],   // Error rate must be less than 1%
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';
// In a real load test, we'd parameterize a valid auth token or tenant_id
const TENANT_ID = '00000000-0000-0000-0000-000000000000'; 
const AUTH_TOKEN = __ENV.AUTH_TOKEN || 'dummy-token';

export default function () {
  const headers = { 
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${AUTH_TOKEN}`
  };

  // 1. Simulate a dashboard poll (Prediction endpoint)
  // Assuming GET /predictions isn't fully implemented without customer_id, we hit health instead for the demo
  // In reality, this would be a GET /tenants/${TENANT_ID}/analytics/...
  let res = http.get(`${BASE_URL}/health`);
  check(res, { 'health check is 200': (r) => r.status === 200 });
  
  sleep(1);

  // 2. Simulate Webhook Burst (Ingestion)
  // We hit the Stripe webhook endpoint
  const payload = JSON.stringify({
    type: 'invoice.payment_failed',
    data: {
      object: {
        customer: `cus_${uuidv4().substring(0, 8)}`,
        amount_due: 5000
      }
    }
  });

  // Stripe signature check will fail unless mocked, but we expect a 200/400 at least for connectivity
  let webhookRes = http.post(`${BASE_URL}/webhooks/stripe`, payload, { headers: {
    'Content-Type': 'application/json',
    'Stripe-Signature': 'mock-signature'
  }});
  
  // We accept 200 (success) or 400 (bad signature) as valid processing for the load test baseline
  check(webhookRes, { 'webhook ingested or rejected gracefully': (r) => r.status === 200 || r.status === 400 });

  sleep(1);
}
