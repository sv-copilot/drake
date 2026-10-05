import { test, expect } from '@playwright/test';

/**
 * Routing smoke test.
 *
 * Every route that is supposed to work must actually render: the shell mounts,
 * the page returns a non-error status, and the main region is not blank. This is
 * the check that catches an unwired page (a component exists and passes unit
 * tests, but no route renders it) — the failure mode unit tests cannot see.
 *
 * The read-only screens fetch from the API. With no API running they render
 * their error state, which still counts as rendering: this test is about
 * routing, not data.
 */

const implementedRoutes = [
  '/portfolio',
  '/slices',
  '/runs',
  '/workers',
  '/dispatches',
  '/sync',
];

const notImplementedRoutes = ['/projects', '/mcp', '/ci-pr'];

test('home redirects to the portfolio overview', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/portfolio$/);
});

test('the shell renders on every implemented route', async ({ page }) => {
  for (const route of implementedRoutes) {
    const response = await page.goto(route);
    expect(response?.status(), `${route} status`).toBeLessThan(400);

    await expect(page.locator('aside'), `${route} shell`).toBeVisible();

    // Presence, not text: with no API running these screens legitimately show a
    // skeleton or an error state, and skeletons carry no text.
    const screen = page.locator('#screen');
    await expect(screen, `${route} screen container`).toBeVisible();
    await expect(
      screen.locator(':scope > *').first(),
      `${route} rendered nothing`,
    ).toBeVisible();
  }
});

test('unimplemented routes say so instead of rendering blank', async ({ page }) => {
  for (const route of notImplementedRoutes) {
    const response = await page.goto(route);
    expect(response?.status(), `${route} status`).toBeLessThan(400);
    await expect(
      page.getByText('Not implemented in this release'),
      `${route} placeholder copy`,
    ).toBeVisible();
  }
});

test('the sidebar links every implemented route', async ({ page }) => {
  await page.goto('/portfolio');
  const nav = page.getByRole('navigation', { name: 'Primary' });

  for (const route of implementedRoutes) {
    await expect(
      nav.locator(`a[href="${route}"]`),
      `nav link to ${route}`,
    ).toHaveCount(1);
  }
});
