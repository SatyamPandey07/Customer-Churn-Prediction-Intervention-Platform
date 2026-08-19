import { test, expect } from '@playwright/test';

test.describe('Responsive App Shell', () => {
  test.beforeEach(async ({ page }) => {
    // Basic setup: bypass auth with cookie
    await page.context().addCookies([
      { name: 'access_token', value: 'mock_token', domain: 'localhost', path: '/' },
      { name: 'user_role', value: 'admin', domain: 'localhost', path: '/' }
    ]);
  });

  test('Desktop layout (1440px): Sidebar is fully visible', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/dashboard');
    
    // Sidebar should be visible with text
    const sidebarText = page.locator('aside >> text=Platform Navigation');
    await expect(sidebarText).toBeVisible();
    
    // Hamburger menu should be hidden
    const hamburger = page.locator('header button:has(svg.lucide-menu)');
    await expect(hamburger).not.toBeVisible();
  });

  test('Tablet layout (820px): Sidebar is icon-only', async ({ page }) => {
    await page.setViewportSize({ width: 820, height: 1180 });
    await page.goto('/dashboard');
    
    // Hamburger should be hidden on tablet
    const hamburger = page.locator('header button:has(svg.lucide-menu)');
    await expect(hamburger).not.toBeVisible();

    // Sidebar text should be hidden
    const sidebarText = page.locator('aside >> text=Platform Navigation');
    await expect(sidebarText).not.toBeVisible();
    
    // Icons should still be visible
    const dashboardLink = page.locator('aside a[title="Dashboard"]');
    await expect(dashboardLink).toBeVisible();
  });

  test('Mobile layout (390px): Sidebar is slide-out drawer via hamburger menu', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/dashboard');
    
    // Hamburger menu should be visible
    const hamburger = page.locator('header button:has(svg.lucide-menu)');
    await expect(hamburger).toBeVisible();

    // Click hamburger to open
    await hamburger.click();
    
    // Now sidebar text should be visible in drawer
    const sidebarText = page.locator('aside >> text=Platform Navigation');
    await expect(sidebarText).toBeVisible();
    
    // Overlay should be visible
    const overlay = page.locator('.fixed.inset-0.bg-slate-950\\/50');
    await expect(overlay).toBeVisible();
    
    // Close sidebar
    await overlay.click();
    await expect(overlay).not.toBeVisible();
  });
});
