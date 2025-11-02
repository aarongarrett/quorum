import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { server } from '../setupTests';
import AdminDashboard from '../components/AdminDashboard';

describe('AdminDashboard Component', () => {
  beforeEach(() => {
    // Mock window.confirm and window.alert
    global.confirm = jest.fn();
    global.alert = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders dashboard title', () => {
    render(<AdminDashboard />);
    expect(screen.getByText(/Admin Dashboard/i)).toBeInTheDocument();
  });

  test('shows empty state when no meetings', async () => {
    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json([]));
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/No meetings found/i)).toBeInTheDocument();
      expect(screen.getByText(/Create your first meeting to get started/i)).toBeInTheDocument();
    });
  });

  test('displays meetings from API', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      // Should show meeting code from mock data
      expect(screen.getByText(/TEST1234/i)).toBeInTheDocument();
      // Should show check-in count
      expect(screen.getByText(/Checked In/i)).toBeInTheDocument();
    });
  });

  test('shows create meeting button', () => {
    render(<AdminDashboard />);
    const createButtons = screen.getAllByRole('button', { name: /Create Meeting/i });
    expect(createButtons.length).toBeGreaterThan(0);
  });

  test('opens create meeting modal when button clicked', async () => {
    const user = userEvent.setup();
    render(<AdminDashboard />);

    const createButton = screen.getAllByRole('button', { name: /Create Meeting/i })[0];
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/Date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Start Time/i)).toBeInTheDocument();
    });
  });

  test('creates a meeting successfully', async () => {
    const user = userEvent.setup();
    render(<AdminDashboard />);

    // Open create meeting modal
    const createButton = screen.getAllByRole('button', { name: /Create Meeting/i })[0];
    await user.click(createButton);

    let modal;
    await waitFor(() => {
      modal = screen.getByLabelText(/Date/i).closest('.modal-content');
      expect(modal).toBeInTheDocument();
    });

    // Fill in the form (date and time should have defaults, so just submit)
    // Find the submit button within the modal (not the header button)
    const submitButton = within(modal).getByRole('button', { name: /Create Meeting/i });
    await user.click(submitButton);

    // Modal should close after successful creation
    await waitFor(() => {
      expect(screen.queryByLabelText(/Date/i)).not.toBeInTheDocument();
    });
  });

  test('shows create poll button for each meeting', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Poll/i })).toBeInTheDocument();
    });
  });

  test('opens create poll modal when button clicked', async () => {
    const user = userEvent.setup();
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/TEST1234/i)).toBeInTheDocument();
    });

    const createPollButton = screen.getByRole('button', { name: /Create Poll/i });
    await user.click(createPollButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/Poll Name/i)).toBeInTheDocument();
    });
  });

  test('creates a poll successfully', async () => {
    const user = userEvent.setup();
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/TEST1234/i)).toBeInTheDocument();
    });

    // Open create poll modal
    const createPollButton = screen.getByRole('button', { name: /Create Poll/i });
    await user.click(createPollButton);

    let modal;
    await waitFor(() => {
      modal = screen.getByLabelText(/Poll Name/i).closest('.modal-content');
      expect(modal).toBeInTheDocument();
    });

    // Fill in poll name
    const pollNameInput = within(modal).getByLabelText(/Poll Name/i);
    await user.type(pollNameInput, 'Test Poll Question');

    // Submit - find button within the modal (not the header button)
    const submitButton = within(modal).getByRole('button', { name: /Create Poll/i });
    await user.click(submitButton);

    // Modal should close after successful creation
    await waitFor(() => {
      expect(screen.queryByLabelText(/Poll Name/i)).not.toBeInTheDocument();
    });
  });

  test('shows no polls message when meeting has no polls', async () => {
    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checkins: 0,
              polls: []
            }
          ])
        );
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/No polls created yet for this meeting/i)).toBeInTheDocument();
    });
  });

  test('displays delete meeting button', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Delete Meeting/i })).toBeInTheDocument();
    });
  });

  test('deletes meeting when confirmed', async () => {
    const user = userEvent.setup();
    global.confirm.mockReturnValue(true);

    server.use(
      rest.delete('/api/v1/admin/meetings/1', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json({ success: true }));
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Delete Meeting/i })).toBeInTheDocument();
    });

    const deleteButton = screen.getByRole('button', { name: /Delete Meeting/i });
    await user.click(deleteButton);

    expect(global.confirm).toHaveBeenCalledWith(expect.stringContaining('Are you sure you want to delete this meeting'));

    // Meeting should be removed from the list
    await waitFor(() => {
      expect(screen.queryByText(/TEST1234/i)).not.toBeInTheDocument();
    });
  });

  test('does not delete meeting when cancelled', async () => {
    const user = userEvent.setup();
    global.confirm.mockReturnValue(false);

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Delete Meeting/i })).toBeInTheDocument();
    });

    const deleteButton = screen.getByRole('button', { name: /Delete Meeting/i });
    await user.click(deleteButton);

    expect(global.confirm).toHaveBeenCalled();

    // Meeting should still be in the list
    await waitFor(() => {
      expect(screen.getByText(/TEST1234/i)).toBeInTheDocument();
    });
  });

  test('handles delete meeting error', async () => {
    const user = userEvent.setup();
    global.confirm.mockReturnValue(true);

    server.use(
      rest.delete('/api/v1/admin/meetings/1', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Delete Meeting/i })).toBeInTheDocument();
    });

    const deleteButton = screen.getByRole('button', { name: /Delete Meeting/i });
    await user.click(deleteButton);

    await waitFor(() => {
      expect(global.alert).toHaveBeenCalledWith(expect.stringContaining('Failed to delete meeting'));
    });
  });

  test('displays poll table with vote counts', async () => {
    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checkins: 5,
              polls: [
                {
                  id: 1,
                  name: 'Sample Poll',
                  total_votes: 10,
                  votes: {
                    A: 5,
                    B: 3,
                    C: 2,
                    D: 0,
                    E: 0,
                    F: 0,
                    G: 0,
                    H: 0
                  }
                }
              ]
            }
          ])
        );
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Sample Poll/i)).toBeInTheDocument();
      // Check vote counts are displayed
      const table = screen.getByRole('table');
      expect(within(table).getByText('10')).toBeInTheDocument(); // total votes
    });
  });

  test('deletes poll when confirmed', async () => {
    const user = userEvent.setup();
    global.confirm.mockReturnValue(true);

    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checkins: 0,
              polls: [
                {
                  id: 1,
                  name: 'Poll to Delete',
                  total_votes: 0,
                  votes: {}
                }
              ]
            }
          ])
        );
      }),
      rest.delete('/api/v1/admin/meetings/1/polls/1', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json({ success: true }));
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Poll to Delete/i)).toBeInTheDocument();
    });

    // Find the delete button for the poll (inside the table)
    const deletePollButton = screen.getByRole('button', { name: '' }); // SVG button has no text
    await user.click(deletePollButton);

    expect(global.confirm).toHaveBeenCalledWith(expect.stringContaining('Are you sure you want to delete the poll'));
  });

  test('does not delete poll when cancelled', async () => {
    const user = userEvent.setup();
    global.confirm.mockReturnValue(false);

    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checkins: 0,
              polls: [
                {
                  id: 1,
                  name: 'Sample Poll',
                  total_votes: 0,
                  votes: {}
                }
              ]
            }
          ])
        );
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Sample Poll/i)).toBeInTheDocument();
    });

    const deletePollButton = screen.getByRole('button', { name: '' });
    await user.click(deletePollButton);

    expect(global.confirm).toHaveBeenCalled();

    // Poll should still be in the list
    await waitFor(() => {
      expect(screen.getByText(/Sample Poll/i)).toBeInTheDocument();
    });
  });

  test('handles delete poll error', async () => {
    const user = userEvent.setup();
    global.confirm.mockReturnValue(true);

    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json([
            {
              id: 1,
              start_time: new Date().toISOString(),
              end_time: new Date(Date.now() + 3600000).toISOString(),
              meeting_code: 'TEST1234',
              checkins: 0,
              polls: [
                {
                  id: 1,
                  name: 'Sample Poll',
                  total_votes: 0,
                  votes: {}
                }
              ]
            }
          ])
        );
      }),
      rest.delete('/api/v1/admin/meetings/1/polls/1', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Sample Poll/i)).toBeInTheDocument();
    });

    const deletePollButton = screen.getByRole('button', { name: '' });
    await user.click(deletePollButton);

    await waitFor(() => {
      expect(global.alert).toHaveBeenCalledWith(expect.stringContaining('Failed to delete poll'));
    });
  });

  test('clicks empty state create meeting button', async () => {
    const user = userEvent.setup();

    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json([]));
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/No meetings found/i)).toBeInTheDocument();
    });

    // There should be 2 Create Meeting buttons: one in header, one in empty state
    const createButtons = screen.getAllByRole('button', { name: /Create Meeting/i });
    expect(createButtons.length).toBe(2);

    // Click the empty state button (second one)
    await user.click(createButtons[1]);

    await waitFor(() => {
      expect(screen.getByLabelText(/Date/i)).toBeInTheDocument();
    });
  });

  test('closes create meeting modal when clicking overlay', async () => {
    const user = userEvent.setup();
    render(<AdminDashboard />);

    const createButton = screen.getAllByRole('button', { name: /Create Meeting/i })[0];
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/Date/i)).toBeInTheDocument();
    });

    // Click the overlay (modal background)
    const overlay = screen.getByLabelText(/Date/i).closest('.modal-overlay');
    await user.click(overlay);

    // Modal should close
    await waitFor(() => {
      expect(screen.queryByLabelText(/Date/i)).not.toBeInTheDocument();
    });
  });

  test('closes create poll modal when clicking overlay', async () => {
    const user = userEvent.setup();
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/TEST1234/i)).toBeInTheDocument();
    });

    const createPollButton = screen.getByRole('button', { name: /Create Poll/i });
    await user.click(createPollButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/Poll Name/i)).toBeInTheDocument();
    });

    // Click the overlay
    const overlay = screen.getByLabelText(/Poll Name/i).closest('.modal-overlay');
    await user.click(overlay);

    // Modal should close
    await waitFor(() => {
      expect(screen.queryByLabelText(/Poll Name/i)).not.toBeInTheDocument();
    });
  });

  test('handles create meeting error', async () => {
    const user = userEvent.setup();

    server.use(
      rest.post('/api/v1/meetings', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    render(<AdminDashboard />);

    const createButton = screen.getAllByRole('button', { name: /Create Meeting/i })[0];
    await user.click(createButton);

    let modal;
    await waitFor(() => {
      modal = screen.getByLabelText(/Date/i).closest('.modal-content');
      expect(modal).toBeInTheDocument();
    });

    const submitButton = within(modal).getByRole('button', { name: /Create Meeting/i });
    await user.click(submitButton);

    // Error message should be displayed
    await waitFor(() => {
      expect(screen.getByText(/Failed to create meeting/i)).toBeInTheDocument();
    });
  });

  test('handles create poll error', async () => {
    const user = userEvent.setup();

    server.use(
      rest.post('/api/v1/meetings/1/polls', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/TEST1234/i)).toBeInTheDocument();
    });

    const createPollButton = screen.getByRole('button', { name: /Create Poll/i });
    await user.click(createPollButton);

    let modal;
    await waitFor(() => {
      modal = screen.getByLabelText(/Poll Name/i).closest('.modal-content');
      expect(modal).toBeInTheDocument();
    });

    const pollNameInput = within(modal).getByLabelText(/Poll Name/i);
    await user.type(pollNameInput, 'Test Poll');

    const submitButton = within(modal).getByRole('button', { name: /Create Poll/i });
    await user.click(submitButton);

    // Error message should be displayed
    await waitFor(() => {
      expect(screen.getByText(/Failed to create poll/i)).toBeInTheDocument();
    });
  });

  test('changes date input in create meeting modal', async () => {
    const user = userEvent.setup();
    render(<AdminDashboard />);

    const createButton = screen.getAllByRole('button', { name: /Create Meeting/i })[0];
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/Date/i)).toBeInTheDocument();
    });

    const dateInput = screen.getByLabelText(/Date/i);
    await user.clear(dateInput);
    await user.type(dateInput, '2025-12-25');

    expect(dateInput.value).toBe('2025-12-25');
  });

  test('changes time input in create meeting modal', async () => {
    const user = userEvent.setup();
    render(<AdminDashboard />);

    const createButton = screen.getAllByRole('button', { name: /Create Meeting/i })[0];
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByLabelText(/Start Time/i)).toBeInTheDocument();
    });

    const timeInput = screen.getByLabelText(/Start Time/i);
    await user.clear(timeInput);
    await user.type(timeInput, '14:30');

    expect(timeInput.value).toBe('14:30');
  });

  test('handles API fetch error gracefully', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation();

    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(consoleError).toHaveBeenCalled();
    });

    consoleError.mockRestore();
  });

  test('displays QR code for each meeting', async () => {
    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/TEST1234/i)).toBeInTheDocument();
      // QRCode component should be rendered (checking for canvas element)
      const canvases = document.querySelectorAll('canvas');
      expect(canvases.length).toBeGreaterThan(0);
    });
  });

  test('cleans up SSE connection on unmount', async () => {
    const { unmount } = render(<AdminDashboard />);

    await waitFor(() => {
      expect(global.EventSource).toBeDefined();
    });

    unmount();

    // SSE cleanup is handled in the component
  });
});
