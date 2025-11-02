/**
 * Critical Path Test #3: Smoke Tests
 *
 * Quick tests to verify the application is running and basic pages load.
 * Run these first to catch deployment issues quickly.
 */

const { test, expect } = require('@playwright/test');

test.describe('Smoke Tests', () => {
  test('home page loads successfully', async ({ page }) => {
    await page.goto('/');

    // Should see the main heading
    await expect(page.getByRole('heading', { name: /quorum/i })).toBeVisible();

    // Should see "Available Meetings" section
    await expect(page.getByText(/available meetings/i)).toBeVisible();
  });

  test('admin login page loads successfully', async ({ page }) => {
    await page.goto('/admin/login');

    // Wait for loading state to complete
    await page.waitForLoadState('networkidle');

    // Should see login form (h2 element)
    await expect(page.locator('h2').filter({ hasText: /admin login/i })).toBeVisible();

    // Should have password input (uses label, not placeholder)
    await expect(page.getByLabel('Password:')).toBeVisible();

    // Should have login button
    await expect(page.getByRole('button', { name: /login/i })).toBeVisible();
  });

  test('admin dashboard shows login when not authenticated', async ({ page }) => {
    // Try to access admin dashboard directly
    await page.goto('/admin');

    // Wait for loading state to complete
    await page.waitForLoadState('networkidle');

    // Should stay at /admin but show login form (no redirect)
    await expect(page).toHaveURL('/admin');
    await expect(page.locator('h2').filter({ hasText: /admin login/i })).toBeVisible();
  });

  test('QR code generation works', async ({ page, request }) => {
    // Create a meeting first via API
    const loginResponse = await request.post('http://localhost:8000/api/v1/auth/admin/login', {
      data: { password: process.env.ADMIN_PASSWORD }
    });
    const cookies = loginResponse.headers()['set-cookie'];

    const now = new Date();
    const meetingResponse = await request.post('http://localhost:8000/api/v1/meetings', {
      headers: { Cookie: cookies },
      data: {
        start_time: new Date(now.getTime() - 300000).toISOString(),
        end_time: new Date(now.getTime() + 7200000).toISOString()
      }
    });
    const meeting = await meetingResponse.json();

    // Now login via UI
    await page.goto('/admin/login');
    await page.waitForLoadState('networkidle');

    // Fill in password and submit - wait for navigation to happen
    await page.getByLabel('Password:').fill(process.env.ADMIN_PASSWORD);

    await Promise.all([
      page.waitForURL('/admin', { timeout: 15000 }),
      page.getByRole('button', { name: /login/i }).click()
    ]);

    // QR code is always visible (no button to click)
    // Find the meeting code in the dashboard
    const meetingCodeElement = page.locator('.meeting-code').filter({ hasText: meeting.meeting_code });
    await expect(meetingCodeElement).toBeVisible();

    // QR code canvas should be visible
    await expect(page.locator('canvas')).toBeVisible({ timeout: 3000 });

    // Cleanup: Delete the meeting
    await request.delete(`http://localhost:8000/api/v1/admin/meetings/${meeting.meeting_id}`, {
      headers: { Cookie: cookies }
    });
  });
});
