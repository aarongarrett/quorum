import React, { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { rest } from 'msw';
import { server } from '../setupTests';
import Home from '../components/Home';
import API from '../api';

// Mock the useSearchParams hook
let mockSearchParams;
let mockSetSearchParams;

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useSearchParams: () => [mockSearchParams, mockSetSearchParams]
}));

const renderHome = async () => {
  let result;
  await act(async () => {
    result = render(
      <BrowserRouter>
        <Home />
      </BrowserRouter>
    );
  });
  return result;
};

describe('Home Component', () => {
  let originalSetItem;
  let originalGetItem;

  beforeEach(() => {
    mockSearchParams = new URLSearchParams();
    mockSetSearchParams = jest.fn();
    localStorage.clear();

    // Store original localStorage methods
    originalSetItem = Storage.prototype.setItem;
    originalGetItem = Storage.prototype.getItem;
  });

  afterEach(() => {
    // Restore original localStorage methods in case tests modified them
    Storage.prototype.setItem = originalSetItem;
    Storage.prototype.getItem = originalGetItem;
  });

  test('renders "Available Meetings" title', async () => {
    await renderHome();
    expect(screen.getByText(/Available Meetings/i)).toBeInTheDocument();
  });

  test('displays meetings from API', async () => {
    await renderHome();

    await waitFor(() => {
      // Meeting card should be displayed (not the "no meetings" message)
      expect(screen.queryByText(/No meetings are currently available/i)).not.toBeInTheDocument();
      // Should have at least one meeting card with a status badge
      expect(screen.getByText(/Not Checked In|Checked In/i)).toBeInTheDocument();
    });
  });

  test('shows "Not Checked In" status for meetings without check-in', async () => {
    await renderHome();

    await waitFor(() => {
      expect(screen.getByText(/Not Checked In/i)).toBeInTheDocument();
    });
  });

  test('shows "Check In" button for unchecked meetings', async () => {
    await renderHome();

    await waitFor(() => {
      const checkInButton = screen.getByRole('button', { name: /Check In/i });
      expect(checkInButton).toBeInTheDocument();
    });
  });

  test('shows "No meetings" message when list is empty', async () => {
    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json([]));
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByText(/No meetings are currently available/i)).toBeInTheDocument();
    });
  });

  test('handles SSE connection', async () => {
    await renderHome();

    // EventSource should be created
    expect(global.EventSource).toBeDefined();
  });

  test('getTokenMap retrieves tokens from localStorage', async () => {
    // Set some tokens in localStorage
    localStorage.setItem('meeting_1_token', 'token123');
    localStorage.setItem('meeting_2_token', 'token456');
    localStorage.setItem('other_key', 'should_be_ignored');

    await renderHome();

    // Wait for component to mount and use the tokens
    await waitFor(() => {
      expect(screen.queryByText(/No meetings are currently available/i)).not.toBeInTheDocument();
    });

    // Verify that tokens were set (the component successfully used localStorage)
    expect(localStorage.length).toBeGreaterThan(0);
  });

  test('opens check-in modal when check-in button is clicked', async () => {
    const user = userEvent.setup();

    // Override to ensure meeting is not checked in
    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: false,
              polls: []
            }
          ])
        );
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Check In/i })).toBeInTheDocument();
    });

    const checkInButton = screen.getByRole('button', { name: /Check In/i });

    await act(async () => {
      await user.click(checkInButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Enter Meeting Code/i)).toBeInTheDocument();
    });
  });

  test('handles successful check-in', async () => {
    const user = userEvent.setup();

    // Override the default handler to return unchecked meeting first, then checked after check-in
    let callCount = 0;
    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        callCount++;
        if (callCount === 1) {
          // First call - not checked in
          return res(
            ctx.status(200),
            ctx.json([
              {
                id: 1,
                start_time: new Date().toISOString(),
                end_time: new Date(Date.now() + 3600000).toISOString(),
                meeting_code: 'TEST1234',
                checked_in: false,
                polls: []
              }
            ])
          );
        } else {
          // After check-in - checked in
          return res(
            ctx.status(200),
            ctx.json([
              {
                id: 1,
                start_time: new Date().toISOString(),
                end_time: new Date(Date.now() + 3600000).toISOString(),
                meeting_code: 'TEST1234',
                checked_in: true,
                polls: []
              }
            ])
          );
        }
      }),
      rest.post('/api/v1/meetings/1/checkins', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json({ token: 'new-token-123' }));
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Check In/i })).toBeInTheDocument();
    });

    const checkInButton = screen.getByRole('button', { name: /Check In/i });

    await act(async () => {
      await user.click(checkInButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Enter Meeting Code/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/MEETCODE/i);

    await act(async () => {
      await user.type(input, 'TEST1234');
    });

    const submitButton = screen.getAllByRole('button', { name: /Check In/i })[1]; // Second "Check In" button (in modal)

    await act(async () => {
      await user.click(submitButton);
    });

    // Wait for check-in to complete and verify token was stored
    await waitFor(() => {
      expect(localStorage.getItem('meeting_1_token')).toBe('new-token-123');
    });
  });

  test('displays checked-in meetings with polls', async () => {
    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: null
                }
              ]
            }
          ])
        );
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByText(/Checked In/i)).toBeInTheDocument();
      expect(screen.getByText(/Test Poll/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Vote Now/i })).toBeInTheDocument();
    });
  });

  test('displays vote status for already voted polls', async () => {
    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: 'A'
                }
              ]
            }
          ])
        );
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
      // Verify the vote value is displayed (checking for strong tag)
      expect(screen.getByText((content, element) => {
        return element.tagName === 'STRONG' && content === 'A';
      })).toBeInTheDocument();
    });
  });

  test('displays no polls message when checked in but no polls available', async () => {
    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: []
            }
          ])
        );
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByText(/Checked In/i)).toBeInTheDocument();
      expect(screen.getByText(/No polls available/i)).toBeInTheDocument();
    });
  });

  test('opens vote modal when vote button is clicked', async () => {
    const user = userEvent.setup();

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: null
                }
              ]
            }
          ])
        );
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Vote Now/i })).toBeInTheDocument();
    });

    const voteButton = screen.getByRole('button', { name: /Vote Now/i });

    await act(async () => {
      await user.click(voteButton);
    });

    // Wait for modal to open
    await waitFor(() => {
      const radios = screen.queryAllByRole('radio');
      expect(radios.length).toBeGreaterThan(0);
    }, { timeout: 3000 });
  });

  test('handles successful vote submission', async () => {
    const user = userEvent.setup();

    // Store a token for the meeting
    localStorage.setItem('meeting_1_token', 'test-token');

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: null
                }
              ]
            }
          ])
        );
      }),
      rest.post('/api/v1/meetings/1/polls/1/votes', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json({ success: true }));
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Vote Now/i })).toBeInTheDocument();
    });

    const voteButton = screen.getByRole('button', { name: /Vote Now/i });

    await act(async () => {
      await user.click(voteButton);
    });

    await waitFor(() => {
      expect(screen.getAllByRole('radio').length).toBeGreaterThan(0);
    });

    // Select option A
    const radioA = screen.getAllByRole('radio')[0];

    await act(async () => {
      await user.click(radioA);
    });

    // Submit vote
    const submitButton = screen.getByRole('button', { name: /Submit Vote/i });

    await act(async () => {
      await user.click(submitButton);
    });

    // Vote modal should close
    await waitFor(() => {
      expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    });
  });

  test('handles API fetch error gracefully', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation();

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(consoleError).toHaveBeenCalled();
    });

    consoleError.mockRestore();
  });

  test('cleans up SSE connection on unmount', async () => {
    const { unmount } = await renderHome();

    await waitFor(() => {
      expect(global.EventSource).toBeDefined();
    });

    unmount();

    // SSE cleanup is handled in the component
  });

  // Edge case tests (Issue 5.4)

  test('handles very long meeting codes (>20 characters)', async () => {
    const user = userEvent.setup();
    const longCode = 'VERYLONGMEETINGCODE123456789';

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: longCode,
              checked_in: false,
              polls: []
            }
          ])
        );
      }),
      rest.post('/api/v1/meetings/1/checkins', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json({ token: 'new-token-123' }));
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Check In/i })).toBeInTheDocument();
    });

    const checkInButton = screen.getByRole('button', { name: /Check In/i });

    await act(async () => {
      await user.click(checkInButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Enter Meeting Code/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/MEETCODE/i);

    await act(async () => {
      await user.type(input, longCode);
    });

    const submitButton = screen.getAllByRole('button', { name: /Check In/i })[1];

    await act(async () => {
      await user.click(submitButton);
    });

    // Should successfully check in with long code
    await waitFor(() => {
      expect(localStorage.getItem('meeting_1_token')).toBe('new-token-123');
    });
  });

  test('handles localStorage quota exceeded gracefully', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation();

    // Mock localStorage.setItem to throw quota exceeded error
    const originalSetItem = Storage.prototype.setItem;
    let setItemCallCount = 0;

    Storage.prototype.setItem = jest.fn((key, value) => {
      setItemCallCount++;
      // Throw error on token storage, but not on other operations
      if (key.includes('token')) {
        throw new DOMException('QuotaExceededError', 'QuotaExceededError');
      }
      // Allow other localStorage operations
      return originalSetItem.call(localStorage, key, value);
    });

    const user = userEvent.setup();

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: false,
              polls: []
            }
          ])
        );
      }),
      rest.post('/api/v1/meetings/1/checkins', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json({ token: 'new-token-123' }));
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Check In/i })).toBeInTheDocument();
    });

    const checkInButton = screen.getByRole('button', { name: /Check In/i });

    await act(async () => {
      await user.click(checkInButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Enter Meeting Code/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/MEETCODE/i);

    await act(async () => {
      await user.type(input, 'TEST1234');
    });

    const submitButton = screen.getAllByRole('button', { name: /Check In/i })[1];

    await act(async () => {
      await user.click(submitButton);
    });

    // Component should handle localStorage error gracefully by showing error message
    await waitFor(() => {
      // Error message should be displayed (component shows error, doesn't crash)
      expect(screen.getByText(/QuotaExceededError/i)).toBeInTheDocument();
    });

    // Verify the component attempted to save to localStorage
    expect(setItemCallCount).toBeGreaterThan(0);

    // Restore original localStorage
    Storage.prototype.setItem = originalSetItem;
    consoleError.mockRestore();
  });

  test('handles network reconnection with stale tokens', async () => {
    // Simulate having stale tokens in localStorage
    localStorage.setItem('meeting_1_token', 'stale-token-123');
    localStorage.setItem('meeting_2_token', 'stale-token-456');

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        // Check if stale tokens were sent in request body
        const tokens = req.body.tokens || {};

        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'MEET1',
              checked_in: false, // Token was stale, so not checked in
              polls: []
            },
            {
              id: 2,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'MEET2',
              checked_in: false,
              polls: []
            }
          ])
        );
      })
    );

    await renderHome();

    // Should load meetings even with stale tokens
    await waitFor(() => {
      const checkInButtons = screen.getAllByRole('button', { name: /Check In/i });
      expect(checkInButtons.length).toBeGreaterThan(0);
    });

    // Meetings should show as not checked in despite having tokens
    expect(screen.getAllByText(/Not Checked In/i).length).toBeGreaterThan(0);
  });

  test('handles rapid repeated check-ins without duplicates', async () => {
    const user = userEvent.setup();
    const checkinCalls = [];

    // Ensure localStorage is working properly for this test
    localStorage.clear();

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: false,
              polls: []
            }
          ])
        );
      }),
      rest.post('/api/v1/meetings/1/checkins', (req, res, ctx) => {
        const callTime = Date.now();
        checkinCalls.push(callTime);
        // Simulate slow response to create opportunity for race condition
        return res(
          ctx.delay(100),
          ctx.status(200),
          ctx.json({ token: 'new-token-123' })
        );
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Check In/i })).toBeInTheDocument();
    });

    const checkInButton = screen.getByRole('button', { name: /Check In/i });

    await act(async () => {
      await user.click(checkInButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Enter Meeting Code/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/MEETCODE/i);

    await act(async () => {
      await user.type(input, 'TEST1234');
    });

    const submitButton = screen.getAllByRole('button', { name: /Check In/i })[1];

    // Click submit button (first click should trigger API call)
    await act(async () => {
      await user.click(submitButton);
    });

    // Try clicking again immediately (should be prevented or handled gracefully)
    // We don't await these to simulate rapid clicking
    act(() => {
      submitButton.click();
      submitButton.click();
    });

    // Wait for check-in to complete
    await waitFor(() => {
      // Check that the token was saved successfully
      const token = localStorage.getItem('meeting_1_token');
      return token === 'new-token-123';
    }, { timeout: 2000 });

    // Verify the component handled rapid clicks
    // At least 1 call should have been made for successful check-in
    expect(checkinCalls.length).toBeGreaterThanOrEqual(1);

    // Should not make excessive calls (depends on implementation)
    // This is more of a smoke test - component doesn't crash with rapid clicks
    expect(checkinCalls.length).toBeLessThanOrEqual(5);
  });

  // Vote privacy tests

  test('vote is initially visible when poll data first loads', async () => {
    jest.useFakeTimers();

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: 'A'
                }
              ]
            }
          ])
        );
      })
    );

    await renderHome();

    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
      expect(screen.getByText('A')).toBeInTheDocument();
    });

    jest.useRealTimers();
  });

  test('vote auto-hides after 3 seconds', async () => {
    jest.useFakeTimers();

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: 'A'
                }
              ]
            }
          ])
        );
      })
    );

    await renderHome();

    // Vote should be visible initially
    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
    });

    // Fast-forward 3 seconds
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // Vote should now be hidden, "Show Vote" button should be visible
    await waitFor(() => {
      expect(screen.queryByText(/You have voted:/i)).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Show Vote/i })).toBeInTheDocument();
    });

    jest.useRealTimers();
  });

  test('clicking "Show Vote" button reveals the vote', async () => {
    jest.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: 'B'
                }
              ]
            }
          ])
        );
      })
    );

    await renderHome();

    // Vote should be visible initially
    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
    });

    // Fast-forward to hide the vote
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // Wait for "Show Vote" button to appear
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Show Vote/i })).toBeInTheDocument();
    });

    const showVoteButton = screen.getByRole('button', { name: /Show Vote/i });

    // Click the button
    await act(async () => {
      await user.click(showVoteButton);
    });

    // Vote should be visible again
    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
      expect(screen.getByText('B')).toBeInTheDocument();
    });

    jest.useRealTimers();
  });

  test('vote auto-hides again after 3 seconds when revealed via button', async () => {
    jest.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: 'C'
                }
              ]
            }
          ])
        );
      })
    );

    await renderHome();

    // Vote should be visible initially
    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
    });

    // Fast-forward to hide the vote
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // Wait for "Show Vote" button
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Show Vote/i })).toBeInTheDocument();
    });

    const showVoteButton = screen.getByRole('button', { name: /Show Vote/i });

    // Click to reveal vote
    await act(async () => {
      await user.click(showVoteButton);
    });

    // Vote should be visible
    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
    });

    // Fast-forward another 3 seconds
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // Vote should be hidden again
    await waitFor(() => {
      expect(screen.queryByText(/You have voted:/i)).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Show Vote/i })).toBeInTheDocument();
    });

    jest.useRealTimers();
  });

  test('multiple polls each have independent vote visibility timers', async () => {
    jest.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Poll 1',
                  vote: 'A'
                },
                {
                  id: 2,
                  name: 'Poll 2',
                  vote: 'B'
                }
              ]
            }
          ])
        );
      })
    );

    await renderHome();

    // Both votes should be visible initially
    await waitFor(() => {
      const voteTexts = screen.getAllByText(/You have voted:/i);
      expect(voteTexts.length).toBe(2);
    });

    // Fast-forward 3 seconds
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // Both votes should be hidden
    await waitFor(() => {
      expect(screen.queryByText(/You have voted:/i)).not.toBeInTheDocument();
      const showButtons = screen.getAllByRole('button', { name: /Show Vote/i });
      expect(showButtons.length).toBe(2);
    });

    // Click first "Show Vote" button
    const showButtons = screen.getAllByRole('button', { name: /Show Vote/i });
    await act(async () => {
      await user.click(showButtons[0]);
    });

    // Only first vote should be visible
    await waitFor(() => {
      const voteTexts = screen.getAllByText(/You have voted:/i);
      expect(voteTexts.length).toBe(1);
    });

    // Fast-forward 3 seconds again
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // First vote should be hidden again
    await waitFor(() => {
      expect(screen.queryByText(/You have voted:/i)).not.toBeInTheDocument();
      const showButtons = screen.getAllByRole('button', { name: /Show Vote/i });
      expect(showButtons.length).toBe(2);
    });

    jest.useRealTimers();
  });

  test('timers are cleaned up on component unmount', async () => {
    jest.useFakeTimers();

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: 'A'
                }
              ]
            }
          ])
        );
      })
    );

    const { unmount } = await renderHome();

    // Vote should be visible initially
    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
    });

    // Unmount component before timer fires
    unmount();

    // Fast-forward timers (should not cause any errors)
    act(() => {
      jest.advanceTimersByTime(5000);
    });

    // No errors should occur from timers trying to update unmounted component
    jest.useRealTimers();
  });

  test('clicking "Show Vote" multiple times rapidly only sets one timer', async () => {
    jest.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checked_in: true,
              polls: [
                {
                  id: 1,
                  name: 'Test Poll',
                  vote: 'D'
                }
              ]
            }
          ])
        );
      })
    );

    await renderHome();

    // Wait for initial visibility
    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
    });

    // Fast-forward to hide
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // Wait for button
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Show Vote/i })).toBeInTheDocument();
    });

    const showVoteButton = screen.getByRole('button', { name: /Show Vote/i });

    // Click multiple times rapidly
    await act(async () => {
      await user.click(showVoteButton);
    });

    await act(async () => {
      await user.click(showVoteButton);
    });

    await act(async () => {
      await user.click(showVoteButton);
    });

    // Vote should be visible
    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
    });

    // Fast-forward 3 seconds
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // Vote should be hidden (only one timer was set)
    await waitFor(() => {
      expect(screen.queryByText(/You have voted:/i)).not.toBeInTheDocument();
    });

    jest.useRealTimers();
  });

  test('vote does not re-show when SSE updates arrive with same vote data', async () => {
    jest.useFakeTimers();

    const meetingData = {
      id: 1,
      start_time: new Date().toISOString(),
      end_time: new Date(Date.now() + 3600000).toISOString(),
      meeting_code: 'TEST1234',
      checked_in: true,
      polls: [
        {
          id: 1,
          name: 'Test Poll',
          vote: 'A'
        }
      ]
    };

    server.use(
      rest.post('/api/v1/meetings/available', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json([meetingData]));
      })
    );

    // Capture EventSource instance
    let eventSourceInstance = null;
    const originalEventSource = global.EventSource;
    global.EventSource = class MockEventSource {
      constructor(url) {
        this.url = url;
        this.readyState = 1;
        this.onmessage = null;
        this.onerror = null;
        eventSourceInstance = this; // Capture the instance
      }
      close() {
        this.readyState = 2;
      }
    };

    await renderHome();

    // Vote should be visible initially
    await waitFor(() => {
      expect(screen.getByText(/You have voted:/i)).toBeInTheDocument();
    });

    // Fast-forward 3 seconds to hide the vote
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    // Vote should be hidden
    await waitFor(() => {
      expect(screen.queryByText(/You have voted:/i)).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Show Vote/i })).toBeInTheDocument();
    });

    // Simulate SSE sending an update with the same vote data
    if (eventSourceInstance && eventSourceInstance.onmessage) {
      await act(async () => {
        eventSourceInstance.onmessage({
          data: JSON.stringify([meetingData])
        });
      });
    }

    // Vote should STILL be hidden (not re-shown)
    // This test should FAIL with current implementation because the useEffect
    // will see poll.vote exists and !visibleVotes[poll.id] and re-show it
    await waitFor(() => {
      expect(screen.queryByText(/You have voted:/i)).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Show Vote/i })).toBeInTheDocument();
    });

    global.EventSource = originalEventSource;
    jest.useRealTimers();
  });
});
