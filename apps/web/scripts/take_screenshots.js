const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const dir = path.join(__dirname, '../../../docs/screenshots');
  if (!fs.existsSync(dir)){
    fs.mkdirSync(dir, { recursive: true });
  }

  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  await page.setViewportSize({ width: 1440, height: 900 });

  console.log('Navigating to http://localhost:3000...');
  
  try {
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  } catch (e) {
    console.error('Failed to load page. Is the frontend running?', e);
    await browser.close();
    process.exit(1);
  }

  try {
    await page.waitForSelector('text=Admin / Owner', { timeout: 5000 });
    console.log('Clicking 1-Click Admin Demo Login...');
    await page.click('text=Admin / Owner');
    
    await page.waitForURL('**/dashboard', { timeout: 10000 });
  } catch (e) {
    console.log('Could not find demo button or already logged in, proceeding...');
  }

  try {
    await page.waitForSelector('text=Churn Risk Telemetry', { timeout: 10000 });
    await page.waitForTimeout(1500);

    console.log('Taking screenshot of Dashboard...');
    await page.screenshot({ path: path.join(dir, 'dashboard.png') });

    console.log('Navigating to Campaigns page...');
    await page.click('text=Campaigns');
    await page.waitForSelector('text=Automated Retention Campaigns', { timeout: 10000 });
    await page.waitForTimeout(1500);

    console.log('Taking screenshot of Campaigns...');
    await page.screenshot({ path: path.join(dir, 'campaigns.png') });

    console.log('Navigating to Integrations page...');
    await page.click('text=Integrations');
    await page.waitForSelector('text=Data Source Connectors', { timeout: 10000 });
    await page.waitForTimeout(1500);

    console.log('Taking screenshot of Integrations...');
    await page.screenshot({ path: path.join(dir, 'integrations.png') });
  } catch (e) {
    console.log('Error occurred, taking debug screenshot...');
    await page.screenshot({ path: path.join(dir, 'error.png') });
    console.error(e);
  }

  await browser.close();
  console.log('Screenshots saved successfully!');
})();
