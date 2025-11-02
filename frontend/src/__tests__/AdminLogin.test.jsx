import React, { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import AdminLogin from '../components/AdminLogin';

const renderAdminLogin = async (onLogin = jest.fn()) => {
  let result;
  await act(async () => {
    result = render(
      <BrowserRouter>
        <AdminLogin onLogin={onLogin} />
      </BrowserRouter>
    );
  });
  return result;
};

describe('AdminLogin Component', () => {
  test('renders login form', async () => {
    await renderAdminLogin();

    expect(screen.getByText(/Admin Login/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Login/i })).toBeInTheDocument();
  });

  test('allows typing in password field', async () => {
    const user = userEvent.setup();
    await renderAdminLogin();

    const passwordInput = screen.getByLabelText(/Password/i);

    await act(async () => {
      await user.type(passwordInput, 'testpassword');
    });

    expect(passwordInput).toHaveValue('testpassword');
  });

  test('successful login calls onLogin callback', async () => {
    const user = userEvent.setup();
    const onLogin = jest.fn();
    await renderAdminLogin(onLogin);

    const passwordInput = screen.getByLabelText(/Password/i);
    const submitButton = screen.getByRole('button', { name: /Login/i });

    await act(async () => {
      await user.type(passwordInput, 'testpass');
    });

    await act(async () => {
      await user.click(submitButton);
    });

    await waitFor(() => {
      expect(onLogin).toHaveBeenCalled();
    });
  });

  test('shows error message on failed login', async () => {
    const user = userEvent.setup();
    const onLogin = jest.fn();
    await renderAdminLogin(onLogin);

    const passwordInput = screen.getByLabelText(/Password/i);
    const submitButton = screen.getByRole('button', { name: /Login/i });

    // Use wrong password
    await act(async () => {
      await user.type(passwordInput, 'wrongpassword');
    });

    await act(async () => {
      await user.click(submitButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Invalid password/i)).toBeInTheDocument();
    });

    // onLogin should not have been called
    expect(onLogin).not.toHaveBeenCalled();
  });

  test('clears error message on new submission', async () => {
    const user = userEvent.setup();
    const onLogin = jest.fn();
    await renderAdminLogin(onLogin);

    const passwordInput = screen.getByLabelText(/Password/i);
    const submitButton = screen.getByRole('button', { name: /Login/i });

    // First attempt with wrong password
    await act(async () => {
      await user.type(passwordInput, 'wrongpassword');
    });

    await act(async () => {
      await user.click(submitButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Invalid password/i)).toBeInTheDocument();
    });

    // Clear and try again with correct password
    await act(async () => {
      await user.clear(passwordInput);
    });

    await act(async () => {
      await user.type(passwordInput, 'testpass');
    });

    await act(async () => {
      await user.click(submitButton);
    });

    // Error should be gone
    await waitFor(() => {
      expect(screen.queryByText(/Invalid password/i)).not.toBeInTheDocument();
    });
  });
});
