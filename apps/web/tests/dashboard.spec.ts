import { test, expect } from '@playwright/test';

test.describe('Dashboard E2E', () => {
  test('full user journey: login -> view churn -> customer detail -> campaign', async ({ page }) => {
    // 1. Mock Login API
    await page.route('**/api/auth/login', async route => {
      const json = { success: true, role: 'admin' };
      await route.fulfill({ json });
    });

    // Mock API requests for the server components / client components
    await page.route('**/customers', async route => {
      const json = [
        { id: '123e4567-e89b-12d3-a456-426614174000', plan: 'Enterprise', mrr: 1000, churn_probability: 0.85, churn_risk_tier: 'critical' },
        { id: '987e6543-e21b-12d3-a456-426614174000', plan: 'Pro', mrr: 200, churn_probability: 0.1, churn_risk_tier: 'low' }
      ];
      await route.fulfill({ json });
    });
    
    await page.route('**/customers/*/churn-explanation', async route => {
      const json = {
        risk_tier: 'critical',
        probability: 0.85,
        top_drivers: [
          { feature: 'usage_trend', shap_value: 0.4, human_readable: 'Feature usage down 40%' }
        ],
        recommended_intervention: 'Send a targeted 20% discount.'
      };
      await route.fulfill({ json });
    });
    
    await page.route('**/customers/*/interventions', async route => {
      await route.fulfill({ json: [] });
    });

    await page.route('**/campaigns', async route => {
      if (route.request().method() === 'POST') {
        const payload = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({ json: { id: 'camp-123', ...payload, status: 'draft' } });
      } else {
        await route.fulfill({ json: [] });
      }
    });

    // Act: Navigate to login
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'password');
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.locator('text=Churn Risk Dashboard')).toBeVisible();

    // Verify customers in table
    await expect(page.locator('text=Enterprise')).toBeVisible();
    await expect(page.locator('text=critical').first()).toBeVisible();

    // Click on customer row
    await page.click('text=123e4567-e89b-12d3-a456-426614174000');
    
    // View customer detail
    await expect(page).toHaveURL(/.*\/dashboard\/customers\/.*/);
    await expect(page.locator('text=Feature usage down 40%')).toBeVisible();
    await expect(page.locator('text=Send a targeted 20% discount.')).toBeVisible();

    // Go to Campaigns
    await page.click('text=Campaigns');
    await expect(page).toHaveURL(/.*\/dashboard\/campaigns/);
    
    // Create a new campaign
    await page.click('text=Create Campaign');
    await page.fill('input[type="text"]', 'Retention Campaign 2024');
    await page.fill('textarea', 'Here is a 20% discount');
    
    // Setup alert listener to handle window.alert
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('Mock Campaign created!');
      await dialog.accept();
    });

    await page.click('button[type="submit"]');
  });
  
  test('viewer role hides campaign creation', async ({ page }) => {
    await page.route('**/api/auth/login', async route => {
      const json = { success: true, role: 'viewer' };
      await route.fulfill({ json });
    });
    
    await page.route('**/campaigns', async route => {
      await route.fulfill({ json: [] });
    });

    await page.goto('/login');
    await page.fill('input[name="username"]', 'viewer');
    await page.fill('input[name="password"]', 'password');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/.*\/dashboard/);
    await page.click('text=Campaigns');
    
    // Ensure Create Campaign is hidden
    await expect(page.locator('text=Create Campaign')).not.toBeVisible();
  });
});
