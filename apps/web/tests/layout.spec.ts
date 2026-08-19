import { test, expect } from '@playwright/test';

test.describe('Configurable Dashboard Layout', () => {
  test('renders default system layout', async ({ page }) => {
    // Route mock for layout API
    await page.route('**/api/dashboard/layout', async (route) => {
      await route.fulfill({ json: { layout: null } }); // Forces system default
    });

    await page.goto('/dashboard');
    
    // Check if the dashboard title exists
    await expect(page.getByText('Churn Risk Dashboard')).toBeVisible();

    // Check if default widgets render
    await expect(page.getByText('MRR at Risk')).toBeVisible();
    await expect(page.getByText('Churn Risk Telemetry')).toBeVisible();
  });

  test('enters edit mode and allows adding widgets', async ({ page }) => {
    await page.route('**/api/dashboard/layout', async (route) => {
      await route.fulfill({ json: { layout: [] } }); // Empty layout
    });

    await page.goto('/dashboard');
    
    // Should see empty state
    await expect(page.getByText('Your dashboard is empty.')).toBeVisible();

    // Click "Start Building" or "Edit Layout"
    const editBtn = page.getByRole('button', { name: /start building/i });
    if (await editBtn.isVisible()) {
      await editBtn.click();
    } else {
      await page.getByRole('button', { name: /edit layout/i }).click();
    }

    // Now in edit mode, add a table
    await page.getByRole('button', { name: '+ Table' }).click();
    await expect(page.getByText('Churn Risk Telemetry')).toBeVisible();
  });
});
