import React, { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { server } from '../setupTests';
import App from '../App';

describe('App Component', () => {
  test('shows loading state initially', () => {
    render(<App />);
    expect(screen.getByText(/Loading.../i)).toBeInTheDocument();
  });

  test('renders home page after auth check', async () => {
    // Mock API to reject (not authenticated)
    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(ctx.status(401));
      })
    );

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText(/Available Meetings/i)).toBeInTheDocument();
    });
  });

  test('shows admin dashboard when authenticated', async () => {
    // Mock API to succeed (authenticated)
    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json([]));
      })
    );

    // Navigate directly to /admin
    window.history.pushState({}, 'Admin', '/admin');

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText(/Admin Dashboard/i)).toBeInTheDocument();
    });
  });

  test('shows admin login when not authenticated and accessing /admin', async () => {
    // Mock API to reject (not authenticated)
    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(ctx.status(401));
      })
    );

    // Navigate to /admin
    window.history.pushState({}, 'Admin', '/admin');

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText(/Admin Login/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    });
  });

  test('shows logout button when authenticated', async () => {
    // Mock API to succeed (authenticated)
    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json([]));
      })
    );

    // Navigate to /admin
    window.history.pushState({}, 'Admin', '/admin');

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Logout/i })).toBeInTheDocument();
    });
  });

  test('logout button clears authentication', async () => {
    const user = userEvent.setup();

    // Mock API to succeed (authenticated)
    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json([]));
      }),
      rest.post('/api/v1/auth/admin/logout', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json({ success: true }));
      })
    );

    // Navigate to /admin
    window.history.pushState({}, 'Admin', '/admin');

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Logout/i })).toBeInTheDocument();
    });

    const logoutButton = screen.getByRole('button', { name: /Logout/i });

    await act(async () => {
      await user.click(logoutButton);
    });

    // Should show login form after logout
    await waitFor(() => {
      expect(screen.getByText(/Admin Login/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    });
  });

  test('renders Quorum header on all pages', async () => {
    server.use(
      rest.get('/api/v1/admin/meetings', (req, res, ctx) => {
        return res(ctx.status(401));
      })
    );

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText(/Quorum/i)).toBeInTheDocument();
    });
  });
});
