/**
 * Critical Path Test #1: User Check-in and Voting
 *
 * This test verifies the core user journey:
 * 1. User accesses the home page
 * 2. User checks into a meeting
 * 3. User votes on a poll
 * 4. User sees confirmation
 */

const { test, expect } = require('@playwright/test');

test.describe('User Voting Flow', () => {
  let meetingCode;
  let meetingId;
  let pollId;
  let adminCookies;

  // Setup: Create meeting and poll via API before test
  test.beforeAll(async ({ request }) => {
    // Admin login
    const loginResponse = await request.post('http://localhost:8000/api/v1/auth/admin/login', {
      data: { password: process.env.ADMIN_PASSWORD }
    });
    adminCookies = loginResponse.headers()['set-cookie'];

    // Create meeting
    const now = new Date();
    const startTime = new Date(now.getTime() - 5 * 60000).toISOString(); // 5 min ago
    const endTime = new Date(now.getTime() + 2 * 3600000).toISOString(); // 2 hours from now

    const meetingResponse = await request.post('http://localhost:8000/api/v1/meetings', {
      headers: { Cookie: adminCookies },
      data: {
        start_time: startTime,
        end_time: endTime
      }
    });
    const meeting = await meetingResponse.json();
    meetingCode = meeting.meeting_code;
    meetingId = meeting.meeting_id;

    // Create poll
    const pollResponse = await request.post(`http://localhost:8000/api/v1/meetings/${meetingId}/polls`, {
      headers: { Cookie: adminCookies },
      data: { name: 'Should we approve the budget?' }
    });
    const poll = await pollResponse.json();
    pollId = poll.poll_id;
  });

  // Cleanup: Delete meeting after tests
  test.afterAll(async ({ request }) => {
    if (meetingId && adminCookies) {
      await request.delete(`http://localhost:8000/api/v1/admin/meetings/${meetingId}`, {
        headers: { Cookie: adminCookies }
      });
    }
  });

  test('user can check in and vote successfully', async ({ page }) => {
    // Navigate to home page
    await page.goto('/');

    // Wait specifically for a meeting card to appear (not just "no meetings")
    // The SSE connection needs time to establish and fetch meetings
    // Note: Don't use waitForLoadState('networkidle') - SSE keeps connections open
    await page.waitForSelector('.meeting-card', { timeout: 15000 });

    // Find the meeting card that's not checked in yet
    // Note: Meeting code is not displayed in user view, so we find by "Not Checked In" status
    const meetingCard = page.locator('.meeting-card').filter({ hasText: /not checked in/i }).first();
    await expect(meetingCard).toBeVisible();

    // Click "Check In" button for the meeting
    const checkInButton = meetingCard.locator('button').filter({ hasText: /check in/i });
    await expect(checkInButton).toBeVisible({ timeout: 10000 });
    await checkInButton.click();

    // Check-in modal should appear
    await expect(page.getByRole('heading', { name: /check in/i })).toBeVisible();

    // Scope all interactions to the modal
    const checkInModal = page.locator('.modal-content');

    // Enter meeting code
    await checkInModal.getByPlaceholder(/meetcode/i).fill(meetingCode);

    // Submit check-in
    const submitCheckInButton = checkInModal.locator('button').filter({ hasText: /check in/i });
    await expect(submitCheckInButton).toBeVisible({ timeout: 10000 });
    await submitCheckInButton.click();

    // Should see success message or modal closes
    await expect(page.getByRole('heading', { name: /check in/i })).not.toBeVisible({ timeout: 5000 });

    // Re-find the meeting card - it now says "Checked In" instead of "Not Checked In"
    const checkedInCard = page.locator('.meeting-card').filter({ hasText: /checked in/i }).first();
    await expect(checkedInCard.getByText(/checked in/i)).toBeVisible();

    // Poll should be visible in the meeting card
    await expect(checkedInCard.getByText(/Should we approve the budget/i)).toBeVisible();

    // Click "Vote Now" button for the poll
    const voteNowButton = checkedInCard.locator('button').filter({ hasText: /vote now/i });
    await expect(voteNowButton).toBeVisible({ timeout: 10000 });
    await voteNowButton.click();

    // Vote modal should appear
    await expect(page.getByRole('heading', { name: /vote in poll/i })).toBeVisible();

    // Scope all interactions to the modal
    const voteModal = page.locator('.modal-content');

    // Select option A - click the label since the radio input is hidden by CSS
    const optionA = voteModal.locator('label.vote-option').filter({ hasText: /^A$/ });
    await expect(optionA).toBeVisible({ timeout: 10000 });
    await optionA.click();

    // Submit vote
    const submitVoteButton = voteModal.locator('button').filter({ hasText: /submit vote/i });
    await expect(submitVoteButton).toBeVisible({ timeout: 10000 });
    await submitVoteButton.click();

    // Vote modal should close
    await expect(page.getByRole('heading', { name: /vote in poll/i })).not.toBeVisible({ timeout: 5000 });

    // Should see that user has voted (format: "You have voted: A")
    // The vote includes the option in a <strong> tag
    await expect(checkedInCard.getByText(/you have voted/i)).toBeVisible();
    await expect(checkedInCard.locator('strong', { hasText: 'A' })).toBeVisible();

    // Verify that the "Vote Now" button is no longer visible after voting
    // The UI prevents double-voting by hiding the vote button
    await expect(checkedInCard.locator('button').filter({ hasText: /vote now/i })).not.toBeVisible();
  });
});
