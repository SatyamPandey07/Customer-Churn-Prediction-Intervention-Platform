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

  // 1. Capture Login Light & Dark
  const page = await context.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  console.log('Navigating to http://localhost:3000/login...');
  try {
    await page.goto('http://localhost:3000/login', { waitUntil: 'domcontentloaded' });
    
    // Light Mode Login
    await page.evaluate(() => {
      localStorage.setItem('churn_ai_theme', 'light');
      document.documentElement.classList.remove('dark');
    });
    await page.waitForTimeout(1000);
    console.log('Taking screenshot of Login (Light Mode)...');
    await page.screenshot({ path: path.join(dir, 'login_light.png') });

    // Dark Mode Login
    await page.evaluate(() => {
      localStorage.setItem('churn_ai_theme', 'dark');
      document.documentElement.classList.add('dark');
    });
    await page.waitForTimeout(1000);
    console.log('Taking screenshot of Login (Dark Mode)...');
    await page.screenshot({ path: path.join(dir, 'login_dark.png') });
  } catch (e) {
    console.error('Login screenshot error:', e);
  }

  // 2. Inject Auth Cookies for Dashboard
  await context.addCookies([
    { name: 'user_role', value: 'admin', domain: 'localhost', path: '/' },
    { name: 'access_token', value: 'demo_admin_access_token', domain: 'localhost', path: '/' }
  ]);

  console.log('Navigating to http://localhost:3000/dashboard...');
  try {
    await page.goto('http://localhost:3000/dashboard', { waitUntil: 'domcontentloaded' });
    
    // Light Mode Dashboard
    await page.evaluate(() => {
      localStorage.setItem('churn_ai_theme', 'light');
      document.documentElement.classList.remove('dark');
    });
    await page.waitForSelector('text=Churn Risk Telemetry', { timeout: 10000 });
    await page.waitForTimeout(1000);
    console.log('Taking screenshot of Dashboard (Light Mode)...');
    await page.screenshot({ path: path.join(dir, 'dashboard_light.png') });

    // Dark Mode Dashboard
    await page.evaluate(() => {
      localStorage.setItem('churn_ai_theme', 'dark');
      document.documentElement.classList.add('dark');
    });
    await page.waitForTimeout(1000);
    console.log('Taking screenshot of Dashboard (Dark Mode)...');
    await page.screenshot({ path: path.join(dir, 'dashboard_dark.png') });
  } catch (e) {
    console.error('Dashboard screenshot error:', e);
  }

  await browser.close();
  console.log('Screenshots saved successfully!');
})();
