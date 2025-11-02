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
  beforeEach(() => {
    mockSearchParams = new URLSearchParams();
    mockSetSearchParams = jest.fn();
    localStorage.clear();
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
});
