import { test, expect } from '@playwright/test';

test('has sidebar', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('aside')).toBeVisible();
});
