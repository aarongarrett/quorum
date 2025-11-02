/**
 * Critical Path Test #2: Admin Workflow
 *
 * This test verifies the admin can:
 * 1. Log in to admin dashboard
 * 2. Create a new meeting
 * 3. Create polls for the meeting
 * 4. See meeting and poll data
 */

const { test, expect } = require('@playwright/test');

test.describe('Admin Workflow', () => {
  const createdMeetingIds = [];

  // Cleanup: Delete all created meetings after all tests
  test.afterAll(async ({ request }) => {
    // Login as admin
    const loginResponse = await request.post('http://localhost:8000/api/v1/auth/admin/login', {
      data: { password: process.env.ADMIN_PASSWORD }
    });
    const cookies = loginResponse.headers()['set-cookie'];

    // Delete all meetings created during tests
    for (const meetingId of createdMeetingIds) {
      try {
        await request.delete(`http://localhost:8000/api/v1/admin/meetings/${meetingId}`, {
          headers: { Cookie: cookies }
        });
      } catch (err) {
        console.log(`Failed to delete meeting ${meetingId}:`, err.message);
      }
    }
  });

  test('admin can login and create meeting with polls', async ({ page }) => {
    // Login via UI
    await page.goto('/admin/login');
    await page.waitForLoadState('networkidle');

    // Fill in password and submit - wait for navigation
    await page.getByLabel('Password:').fill(process.env.ADMIN_PASSWORD);

    await Promise.all([
      page.waitForURL('/admin', { timeout: 15000 }),
      page.getByRole('button', { name: /login/i }).click()
    ]);

    // Dashboard should be visible
    await expect(page.locator('h2').filter({ hasText: /admin dashboard/i })).toBeVisible({ timeout: 10000 });

    // Get existing meeting codes before creating a new one
    const existingMeetingCodes = await page.locator('.meeting-code').allTextContents();

    // Wait for and click Create Meeting button (use text selector since button has SVG icon)
    const createMeetingButton = page.locator('button').filter({ hasText: /create meeting/i }).first();
    await expect(createMeetingButton).toBeVisible({ timeout: 10000 });
    await createMeetingButton.click();

    // Fill in meeting details
    // The UI has separate date and time inputs (not datetime-local)
    const now = new Date();
    const startDateTime = new Date(now.getTime() - 300000); // 5 min ago to be active now

    const dateStr = startDateTime.toISOString().split('T')[0]; // YYYY-MM-DD
    const hours = String(startDateTime.getHours()).padStart(2, '0');
    const minutes = String(startDateTime.getMinutes()).padStart(2, '0');
    const timeStr = `${hours}:${minutes}`; // HH:mm

    // Scope all modal interactions to the modal
    const modal = page.locator('.modal-content');
    await modal.getByLabel('Date').fill(dateStr);
    await modal.getByLabel('Start Time').fill(timeStr);

    // Submit meeting creation (end time is auto-calculated as +2 hours)
    const submitMeetingButton = modal.locator('button').filter({ hasText: /create meeting/i });
    await expect(submitMeetingButton).toBeVisible({ timeout: 10000 });
    await submitMeetingButton.click();

    // Wait for modal to close (indicates successful creation)
    await expect(modal).not.toBeVisible({ timeout: 10000 });

    // Find the NEW meeting code (one that wasn't in existingMeetingCodes)
    // Wait for the new meeting to appear via SSE update
    let meetingCode = '';
    for (let i = 0; i < 20; i++) {
      await page.waitForTimeout(500);
      const currentMeetingCodes = await page.locator('.meeting-code').allTextContents();
      const newCodes = currentMeetingCodes.filter(code => !existingMeetingCodes.includes(code));
      if (newCodes.length > 0) {
        meetingCode = newCodes[0];
        break;
      }
    }

    if (!meetingCode) {
      throw new Error('Failed to find newly created meeting code');
    }

    // Get the meeting ID for cleanup by fetching all meetings
    const allMeetingsResponse = await page.request.get('http://localhost:8000/api/v1/admin/meetings');
    const allMeetings = await allMeetingsResponse.json();
    const createdMeeting = allMeetings.find(m => m.meeting_code === meetingCode);
    if (createdMeeting) {
      createdMeetingIds.push(createdMeeting.id);
    }

    // Create a poll for this meeting
    // Find the meeting card and click "Create Poll"
    const meetingCard = page.locator('.meeting-admin-card').filter({ hasText: meetingCode });
    const createPollButton = meetingCard.locator('button').filter({ hasText: /create poll/i });
    await expect(createPollButton).toBeVisible({ timeout: 10000 });
    await createPollButton.click();

    // Scope all modal interactions to the modal
    const pollModal = page.locator('.modal-content');

    // Enter poll name (uses label, not placeholder)
    await pollModal.getByLabel('Poll Name').fill('Should we extend the deadline?');

    // Submit poll
    const submitPollButton = pollModal.locator('button').filter({ hasText: /create poll/i });
    await expect(submitPollButton).toBeVisible({ timeout: 10000 });
    await submitPollButton.click();

    // Should see the poll in the poll table
    await expect(meetingCard.getByText(/Should we extend the deadline/i)).toBeVisible({ timeout: 5000 });

    // Verify meeting shows 0 checkins initially (format: "0 Checked In")
    await expect(meetingCard.locator('.checkin-count')).toHaveText('0');

    // Verify poll shows 0 total votes in the table
    const pollRow = meetingCard.locator('.poll-row').filter({ hasText: /Should we extend the deadline/i });
    await expect(pollRow.locator('.vote-count').first()).toHaveText('0');
  });

  test('admin can see real-time vote updates', async ({ page, request }) => {
    // First, admin creates a meeting and poll
    const loginResponse = await request.post('http://localhost:8000/api/v1/auth/admin/login', {
      data: { password: process.env.ADMIN_PASSWORD }
    });
    const cookies = loginResponse.headers()['set-cookie'];

    const now = new Date();
    const startTime = new Date(now.getTime() - 300000).toISOString();
    const endTime = new Date(now.getTime() + 7200000).toISOString();

    const meetingResponse = await request.post('http://localhost:8000/api/v1/meetings', {
      headers: { Cookie: cookies },
      data: { start_time: startTime, end_time: endTime }
    });
    const meeting = await meetingResponse.json();

    // Track meeting for cleanup
    createdMeetingIds.push(meeting.meeting_id);

    const pollResponse = await request.post(`http://localhost:8000/api/v1/meetings/${meeting.meeting_id}/polls`, {
      headers: { Cookie: cookies },
      data: { name: 'Test Vote Update' }
    });
    const poll = await pollResponse.json();

    // Navigate to admin dashboard
    await page.goto('/admin/login');
    await page.waitForLoadState('networkidle');

    // Login via UI - wait for navigation
    await page.getByLabel('Password:').fill(process.env.ADMIN_PASSWORD);

    await Promise.all([
      page.waitForURL('/admin', { timeout: 15000 }),
      page.getByRole('button', { name: /login/i }).click()
    ]);

    // Dashboard should be visible
    await expect(page.locator('h2').filter({ hasText: /admin dashboard/i })).toBeVisible({ timeout: 10000 });

    // Find the meeting we created
    const meetingCard = page.locator('.meeting-admin-card').filter({ hasText: meeting.meeting_code });
    await expect(meetingCard).toBeVisible();

    // Initially should show 0 check-ins
    await expect(meetingCard.locator('.checkin-count')).toHaveText('0');

    // Simulate a user checking in and voting via API
    const checkinResponse = await request.post(`http://localhost:8000/api/v1/meetings/${meeting.meeting_id}/checkins`, {
      data: { meeting_code: meeting.meeting_code }
    });
    const checkin = await checkinResponse.json();

    await request.post(`http://localhost:8000/api/v1/meetings/${meeting.meeting_id}/polls/${poll.poll_id}/votes`, {
      data: { token: checkin.token, vote: 'A' }
    });

    // Wait for SSE update (should happen within 5 seconds)
    // Check-in count should update to 1
    await expect(meetingCard.locator('.checkin-count')).toHaveText('1', { timeout: 10000 });

    // Vote count should update to 1 in the poll table
    const pollRow = meetingCard.locator('.poll-row').filter({ hasText: 'Test Vote Update' });
    await expect(pollRow.locator('.vote-count').first()).toHaveText('1', { timeout: 10000 });
  });
});
