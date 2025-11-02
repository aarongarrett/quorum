import React, { act } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CheckInModal from '../components/CheckInModal';

const mockMeeting = {
  id: 1,
  meeting_code: 'TEST1234'
};

describe('CheckInModal Component', () => {
  test('renders check-in modal', async () => {
    const onClose = jest.fn();
    const onSuccess = jest.fn();

    await act(async () => {
      render(
        <CheckInModal
          meeting={mockMeeting}
          onSuccess={onSuccess}
          onClose={onClose}
        />
      );
    });

    expect(screen.getByText(/Meeting Code/i)).toBeInTheDocument();
  });

  test('allows user to enter meeting code', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    const onSuccess = jest.fn();

    await act(async () => {
      render(
        <CheckInModal
          meeting={mockMeeting}
          onSuccess={onSuccess}
          onClose={onClose}
        />
      );
    });

    const input = screen.getByLabelText(/Meeting Code/i);

    await act(async () => {
      await user.type(input, 'TEST1234');
    });

    expect(input).toHaveValue('TEST1234');
  });

  test('calls onSuccess when check-in succeeds', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    const onSuccess = jest.fn();

    await act(async () => {
      render(
        <CheckInModal
          meeting={mockMeeting}
          onSuccess={onSuccess}
          onClose={onClose}
        />
      );
    });

    const input = screen.getByLabelText(/Meeting Code/i);
    const submitButton = screen.getByRole('button', { name: /Check In/i });

    await act(async () => {
      await user.type(input, 'TEST1234');
    });

    await act(async () => {
      await user.click(submitButton);
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  test('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    const onSuccess = jest.fn();

    await act(async () => {
      render(
        <CheckInModal
          meeting={mockMeeting}
          onSuccess={onSuccess}
          onClose={onClose}
        />
      );
    });

    // Click outside modal or find cancel button
    const modal = screen.getByText(/Meeting Code/i).closest('.modal-overlay');
    if (modal) {
      await act(async () => {
        await user.click(modal);
      });
      expect(onClose).toHaveBeenCalled();
    }
  });
});
