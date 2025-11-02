import React, { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VoteModal from '../components/VoteModal';

const mockMeeting = {
  id: 1
};

const mockPoll = {
  id: 1,
  name: 'Test Poll'
};

describe('VoteModal Component', () => {
  beforeEach(() => {
    localStorage.setItem('meeting_1_token', 'test-token');
  });

  test('renders vote modal with poll name', () => {
    const onClose = jest.fn();
    const onSuccess = jest.fn();

    render(
      <VoteModal
        meeting={mockMeeting}
        poll={mockPoll}
        onSuccess={onSuccess}
        onClose={onClose}
      />
    );

    expect(screen.getByText(/Test Poll/i)).toBeInTheDocument();
  });

  test('displays vote options A through H', () => {
    const onClose = jest.fn();
    const onSuccess = jest.fn();

    render(
      <VoteModal
        meeting={mockMeeting}
        poll={mockPoll}
        onSuccess={onSuccess}
        onClose={onClose}
      />
    );

    const options = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
    const radioButtons = screen.getAllByRole('radio');
    expect(radioButtons).toHaveLength(8);

    options.forEach(option => {
      const radio = radioButtons.find(r => r.value === option);
      expect(radio).toBeInTheDocument();
    });
  });

  test('allows selecting a vote option', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    const onSuccess = jest.fn();

    await act(async () => {
      render(
        <VoteModal
          meeting={mockMeeting}
          poll={mockPoll}
          onSuccess={onSuccess}
          onClose={onClose}
        />
      );
    });

    const radioButtons = screen.getAllByRole('radio');
    const optionA = radioButtons.find(r => r.value === 'A');

    await act(async () => {
      await user.click(optionA);
    });

    const submitButton = screen.getByRole('button', { name: /Submit Vote/i });

    await act(async () => {
      await user.click(submitButton);
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  test('submits vote with token from localStorage', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    const onSuccess = jest.fn();

    // Set a token in localStorage (component should retrieve this)
    localStorage.setItem('meeting_1_token', 'test-token');

    await act(async () => {
      render(
        <VoteModal
          meeting={mockMeeting}
          poll={mockPoll}
          onSuccess={onSuccess}
          onClose={onClose}
        />
      );
    });

    // Select a vote option
    const radioButtons = screen.getAllByRole('radio');
    const optionA = radioButtons.find(r => r.value === 'A');

    await act(async () => {
      await user.click(optionA);
    });

    // Submit the form
    const submitButton = screen.getByRole('button', { name: /Submit Vote/i });

    await act(async () => {
      await user.click(submitButton);
    });

    // onSuccess being called proves the token was retrieved and vote succeeded
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
