import { test, expect } from '@playwright/test';

test('Continuity Autopsy renders correctly', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Check scene navigator exists
  await expect(page.locator('text=STORYTRACE')).toBeVisible();
  await expect(page.getByText('Scene 3', { exact: true }).first()).toBeVisible();
  
  // Check main screenplay text renders
  await expect(page.locator('text=INT. WAREHOUSE - NIGHT')).toBeVisible();
  await expect(page.locator('text=It ends tonight.')).toBeVisible();

  // Check autopsy sidebar
  await expect(page.locator('text=Continuity Findings')).toBeVisible();
  await expect(page.locator('text=VERIFIED CONFLICT')).toBeVisible();
  
  // Check findings detail
  await expect(page.getByText('Silver Pistol', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('No screenplay evidence explains how John regained the gun.', { exact: true }).first()).toBeVisible();

  // Check intentional override button
  await expect(page.locator('text=Mark Intentional')).toBeVisible();
});
