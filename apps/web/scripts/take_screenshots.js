const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  // Ensure the screenshots directory exists
  const dir = path.join(__dirname, '../../../docs/screenshots');
  if (!fs.existsSync(dir)){
    fs.mkdirSync(dir, { recursive: true });
  }

  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Set viewport for a nice desktop screenshot
  await page.setViewportSize({ width: 1440, height: 900 });

  console.log('Navigating to http://localhost:3000...');
  
  try {
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  } catch (e) {
    console.error('Failed to load page. Is the frontend running?', e);
    await browser.close();
    process.exit(1);
  }

  // We are probably at the login page.
  // Wait for the login form to be visible
  try {
    await page.waitForSelector('input[name="username"]', { timeout: 5000 });
    console.log('Logging in...');
    await page.fill('input[name="username"]', 'admin@example.com');
    await page.fill('input[name="password"]', 'Password123!');
    await page.click('button[type="submit"]');
    
    // Wait for navigation to dashboard
    await page.waitForURL('**/dashboard', { timeout: 10000 });
  } catch (e) {
    console.log('Could not find login form or already logged in, proceeding...');
  }

  try {
    // Ensure dashboard is loaded
    await page.waitForSelector('text=Churn Risk Dashboard', { timeout: 10000 });
    
    // Let animations settle
    await page.waitForTimeout(2000);

    console.log('Taking screenshot of Dashboard...');
    await page.screenshot({ path: path.join(dir, 'dashboard.png') });

    // Navigate to Campaigns page
    console.log('Navigating to Campaigns page...');
    await page.click('text=Campaigns');
    
    // Wait for campaigns page to load
    await page.waitForSelector('text=Create Campaign', { timeout: 10000 });
    await page.waitForTimeout(2000);

    console.log('Taking screenshot of Campaigns...');
    await page.screenshot({ path: path.join(dir, 'campaigns.png') });
  } catch (e) {
    console.log('Error occurred, taking debug screenshot...');
    await page.screenshot({ path: path.join(dir, 'error.png') });
    console.error(e);
  }

  await browser.close();
  console.log('Screenshots saved successfully!');
})();
