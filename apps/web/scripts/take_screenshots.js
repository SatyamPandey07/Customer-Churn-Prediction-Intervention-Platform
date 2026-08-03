const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const dir = path.join(__dirname, '../../../docs/screenshots');
  if (!fs.existsSync(dir)){
    fs.mkdirSync(dir, { recursive: true });
  }

  const browser = await chromium.launch();
  const context = await browser.newContext();
  
  await context.addCookies([
    { name: 'user_role', value: 'admin', domain: 'localhost', path: '/' },
    { name: 'access_token', value: 'demo_admin_access_token', domain: 'localhost', path: '/' }
  ]);

  const page = await context.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  console.log('Navigating directly to http://localhost:3000/dashboard...');
  
  try {
    await page.goto('http://localhost:3000/dashboard', { waitUntil: 'domcontentloaded' });
  } catch (e) {
    console.error('Failed to load dashboard:', e);
    await browser.close();
    process.exit(1);
  }

  try {
    await page.evaluate(() => {
      localStorage.setItem('churn_ai_theme', 'light');
      document.documentElement.classList.remove('dark');
    });
    
    await page.waitForSelector('text=Churn Risk Telemetry', { timeout: 10000 });
    await page.waitForTimeout(1500);

    console.log('Taking screenshot of Dashboard (Light Mode)...');
    await page.screenshot({ path: path.join(dir, 'dashboard_light.png') });

    console.log('Navigating to Campaigns page...');
    await page.click('text=Campaigns');
    await page.waitForSelector('text=Automated Retention Campaigns', { timeout: 10000 });
    await page.waitForTimeout(1500);

    console.log('Taking screenshot of Campaigns (Light Mode)...');
    await page.screenshot({ path: path.join(dir, 'campaigns_light.png') });

    console.log('Navigating to Audit Logs page...');
    await page.click('text=Audit Logs');
    await page.waitForSelector('text=SOC2 & GDPR Compliance Audit Stream', { timeout: 10000 });
    await page.waitForTimeout(1500);

    console.log('Taking screenshot of Audit Logs (Light Mode)...');
    await page.screenshot({ path: path.join(dir, 'audit_logs_light.png') });

    console.log('Navigating to Settings page...');
    await page.click('text=Settings');
    await page.waitForSelector('text=Tenant Settings & Access Control', { timeout: 10000 });
    await page.waitForTimeout(1500);

    console.log('Taking screenshot of Settings (Light Mode)...');
    await page.screenshot({ path: path.join(dir, 'settings_light.png') });
  } catch (e) {
    console.log('Error occurred, taking debug screenshot...');
    await page.screenshot({ path: path.join(dir, 'error.png') });
    console.error(e);
  }

  await browser.close();
  console.log('Screenshots saved successfully!');
})();
