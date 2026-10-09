import { test, expect } from '@playwright/test';

test('Packaged assets support touch navigation, sliders and chart inspection under CSP', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(`${msg.text()} (${msg.location().url})`); });
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore offline demo', exact: true }).click();
  await expect(page.getByRole('heading', { name: /A little clarity/ })).toBeVisible();
  await expect(page.locator('meta[http-equiv="Content-Security-Policy"]')).toHaveAttribute('content', /connect-src 'self'/);
  await page.screenshot({ path: 'test-results/android-home-touch.png', fullPage: true });
  const quick = page.getByRole('navigation', { name: 'Quick navigation' });
  await quick.getByRole('link', { name: 'What-if', exact: true }).tap();
  const slider = page.getByRole('slider', { name: /Emergency expense/ });
  await slider.scrollIntoViewIfNeeded();
  const box = await slider.boundingBox();
  await page.touchscreen.tap(box.x + box.width * .6, box.y + box.height / 2);
  await expect.poll(() => slider.inputValue()).not.toBe('0');
  await expect(page.getByText('Below your emergency reserve')).toBeVisible();
  const chart = page.locator('.recharts-wrapper').first();
  await chart.scrollIntoViewIfNeeded();
  const chartBox = await chart.boundingBox();
  await page.touchscreen.tap(chartBox.x + chartBox.width * .55, chartBox.y + chartBox.height * .4);
  await expect(page.locator('.recharts-tooltip-wrapper').first()).toBeVisible();
  await expect(page.locator('.recharts-tooltip-wrapper').first()).toContainText('₹');
  await page.screenshot({ path: 'test-results/android-simulator-touch.png', fullPage: true });
  await quick.getByRole('link', { name: 'Autopilot', exact: true }).tap();
  await page.getByRole('button', { name: 'Add to plan' }).first().tap();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Confirm', exact: true }).tap();
  await expect(page.getByText(/Planned ·/)).toBeVisible();
  for (const name of ['Transactions', 'Financial Insights', 'How It Works', 'Privacy Center']) {
    await quick.getByRole('button', { name: 'More pages' }).tap();
    await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name, exact: true }).tap();
    await expect(page.locator('main h1')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  }
  await expect(page.getByText('No API configured for the offline demo.', { exact: false })).toBeVisible();
  expect(errors).toEqual([]);
});

test('Small phone, landscape and safe-area padding retain accessible navigation', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/#Dashboard');
  await page.getByRole('button', { name: 'Explore offline demo', exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const nav = page.getByRole('navigation', { name: 'Quick navigation' });
  const link = nav.getByRole('link', { name: 'Goals', exact: true });
  const size = await link.boundingBox();
  expect(size.height).toBeGreaterThanOrEqual(44); expect(size.width).toBeGreaterThanOrEqual(44);
  await page.evaluate(() => { document.documentElement.style.setProperty('--safe-area-inset-top', '24px'); document.documentElement.style.setProperty('--safe-area-inset-bottom', '24px'); });
  await expect(nav).toHaveCSS('padding-bottom', '32px');
  await page.screenshot({ path: 'test-results/android-safe-area-before-tap.png' });
  await link.tap();
  await page.getByRole('button', { name: 'Toggle light and dark theme' }).tap();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.screenshot({ path: 'test-results/android-small-phone.png', fullPage: true });
  await page.setViewportSize({ width: 844, height: 390 });
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'How It Works', exact: true }).tap();
  await expect(page.getByRole('heading', { name: /From everyday spending/ })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});
