import API from '../api';
import { server } from '../setupTests';
import { rest } from 'msw';

const API_BASE = '';
const API_VERSION = 'v1';

// Mock EventSource for SSE tests
class MockEventSource {
  constructor(url, options) {
    this.url = url;
    this.options = options;
    this.onmessage = null;
    this.onerror = null;
    MockEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }
}

MockEventSource.instances = [];
MockEventSource.resetInstances = () => {
  MockEventSource.instances = [];
};

global.EventSource = MockEventSource;

describe('API', () => {
  beforeEach(() => {
    MockEventSource.resetInstances();
  });

  describe('adminLogin', () => {
    it('should successfully login with valid password', async () => {
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/auth/admin/login`, (req, res, ctx) => {
          return res(ctx.status(200), ctx.json({ success: true }));
        })
      );

      const result = await API.adminLogin('correct-password');
      expect(result).toEqual({ success: true });
    });

    it('should throw error on failed login', async () => {
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/auth/admin/login`, (req, res, ctx) => {
          return res(ctx.status(401));
        })
      );

      await expect(API.adminLogin('wrong-password')).rejects.toThrow('Invalid password');
    });
  });

  describe('createMeeting', () => {
    it('should create meeting with EST timezone (winter)', async () => {
      // Mock fetch to capture the request body
      let capturedBody;
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings`, (req, res, ctx) => {
          capturedBody = req.body;
          return res(ctx.status(200), ctx.json({ id: 1, start_time: capturedBody.start_time, end_time: capturedBody.end_time }));
        })
      );

      // Use a winter date (January) to ensure EST
      const result = await API.createMeeting('2024-01-15T10:00', '2024-01-15T11:00');

      expect(capturedBody.start_time).toBe('2024-01-15T10:00:00-05:00');
      expect(capturedBody.end_time).toBe('2024-01-15T11:00:00-05:00');
      expect(result.id).toBe(1);
    });

    it('should create meeting with EDT timezone (summer)', async () => {
      let capturedBody;
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings`, (req, res, ctx) => {
          capturedBody = req.body;
          return res(ctx.status(200), ctx.json({ id: 2, start_time: capturedBody.start_time, end_time: capturedBody.end_time }));
        })
      );

      // Use a summer date (July) to ensure EDT
      const result = await API.createMeeting('2024-07-15T10:00', '2024-07-15T11:00');

      expect(capturedBody.start_time).toBe('2024-07-15T10:00:00-04:00');
      expect(capturedBody.end_time).toBe('2024-07-15T11:00:00-04:00');
      expect(result.id).toBe(2);
    });

    it('should throw error on failed meeting creation', async () => {
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings`, (req, res, ctx) => {
          return res(ctx.status(500));
        })
      );

      await expect(API.createMeeting('2024-01-15T10:00', '2024-01-15T11:00'))
        .rejects.toThrow('Failed to create meeting');
    });
  });

  describe('getAvailableMeetings', () => {
    it('should fetch available meetings with token map', async () => {
      const mockMeetings = [{ id: 1, status: 'active' }];
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/available`, (req, res, ctx) => {
          return res(ctx.status(200), ctx.json(mockMeetings));
        })
      );

      const tokenMap = { '1': 'token123' };
      const result = await API.getAvailableMeetings(tokenMap);

      expect(result).toEqual(mockMeetings);
    });

    it('should fetch available meetings with empty token map', async () => {
      const mockMeetings = [{ id: 1, status: 'active' }];
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/available`, (req, res, ctx) => {
          return res(ctx.status(200), ctx.json(mockMeetings));
        })
      );

      const result = await API.getAvailableMeetings();

      expect(result).toEqual(mockMeetings);
    });

    it('should throw error on failed fetch', async () => {
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/available`, (req, res, ctx) => {
          return res(ctx.status(500));
        })
      );

      await expect(API.getAvailableMeetings({})).rejects.toThrow('Failed to fetch meetings');
    });
  });

  describe('getAllMeetings', () => {
    it('should fetch all meetings for admin', async () => {
      const mockMeetings = [{ id: 1 }, { id: 2 }];
      server.use(
        rest.get(`${API_BASE}/api/${API_VERSION}/admin/meetings`, (req, res, ctx) => {
          return res(ctx.status(200), ctx.json(mockMeetings));
        })
      );

      const result = await API.getAllMeetings();

      expect(result).toEqual(mockMeetings);
    });

    it('should throw error on failed fetch', async () => {
      server.use(
        rest.get(`${API_BASE}/api/${API_VERSION}/admin/meetings`, (req, res, ctx) => {
          return res(ctx.status(500));
        })
      );

      await expect(API.getAllMeetings()).rejects.toThrow('Failed to fetch meetings');
    });
  });

  describe('deleteMeeting', () => {
    it('should successfully delete a meeting', async () => {
      server.use(
        rest.delete(`${API_BASE}/api/${API_VERSION}/admin/meetings/1`, (req, res, ctx) => {
          return res(ctx.status(200), ctx.json({ success: true }));
        })
      );

      const result = await API.deleteMeeting(1);

      expect(result).toEqual({ success: true });
    });

    it('should throw error on failed delete', async () => {
      server.use(
        rest.delete(`${API_BASE}/api/${API_VERSION}/admin/meetings/1`, (req, res, ctx) => {
          return res(ctx.status(500));
        })
      );

      await expect(API.deleteMeeting(1)).rejects.toThrow('Failed to delete meeting');
    });
  });

  describe('createPoll', () => {
    it('should successfully create a poll', async () => {
      const mockPoll = { id: 1, name: 'Test Poll', meeting_id: 1 };
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/1/polls`, (req, res, ctx) => {
          return res(ctx.status(200), ctx.json(mockPoll));
        })
      );

      const result = await API.createPoll(1, 'Test Poll');

      expect(result).toEqual(mockPoll);
    });

    it('should throw error on failed poll creation', async () => {
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/1/polls`, (req, res, ctx) => {
          return res(ctx.status(500));
        })
      );

      await expect(API.createPoll(1, 'Test Poll')).rejects.toThrow('Failed to create poll');
    });
  });

  describe('deletePoll', () => {
    it('should successfully delete a poll', async () => {
      server.use(
        rest.delete(`${API_BASE}/api/${API_VERSION}/admin/meetings/1/polls/1`, (req, res, ctx) => {
          return res(ctx.status(200), ctx.json({ success: true }));
        })
      );

      const result = await API.deletePoll(1, 1);

      expect(result).toEqual({ success: true });
    });

    it('should throw error on failed poll delete', async () => {
      server.use(
        rest.delete(`${API_BASE}/api/${API_VERSION}/admin/meetings/1/polls/1`, (req, res, ctx) => {
          return res(ctx.status(500));
        })
      );

      await expect(API.deletePoll(1, 1)).rejects.toThrow('Failed to delete poll');
    });
  });

  describe('checkin', () => {
    it('should successfully check in to a meeting', async () => {
      const mockResponse = { token: 'new-token', meeting_id: 1 };
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/1/checkins`, (req, res, ctx) => {
          return res(ctx.status(200), ctx.json(mockResponse));
        })
      );

      const result = await API.checkin(1, 'ABC123');

      expect(result).toEqual(mockResponse);
    });

    it('should check in with existing token', async () => {
      const mockResponse = { token: 'existing-token', meeting_id: 1 };
      let capturedBody;
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/1/checkins`, (req, res, ctx) => {
          capturedBody = req.body;
          return res(ctx.status(200), ctx.json(mockResponse));
        })
      );

      const result = await API.checkin(1, 'ABC123', 'existing-token');

      expect(result).toEqual(mockResponse);
      expect(capturedBody.token).toBe('existing-token');
    });

    it('should throw error with detail on failed check-in', async () => {
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/1/checkins`, (req, res, ctx) => {
          return res(ctx.status(400), ctx.json({ detail: 'Invalid meeting code' }));
        })
      );

      await expect(API.checkin(1, 'WRONG')).rejects.toThrow('Invalid meeting code');
    });

    it('should throw generic error when no detail provided', async () => {
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/1/checkins`, (req, res, ctx) => {
          return res(ctx.status(400), ctx.json({}));
        })
      );

      await expect(API.checkin(1, 'WRONG')).rejects.toThrow('Check-in failed');
    });
  });

  describe('vote', () => {
    it('should successfully submit a vote', async () => {
      const mockResponse = { success: true };
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/1/polls/1/votes`, (req, res, ctx) => {
          return res(ctx.status(200), ctx.json(mockResponse));
        })
      );

      const result = await API.vote(1, 1, 'token123', 'yes');

      expect(result).toEqual(mockResponse);
    });

    it('should throw error with detail on failed vote', async () => {
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/1/polls/1/votes`, (req, res, ctx) => {
          return res(ctx.status(400), ctx.json({ detail: 'Invalid token' }));
        })
      );

      await expect(API.vote(1, 1, 'bad-token', 'yes')).rejects.toThrow('Invalid token');
    });

    it('should throw generic error when no detail provided', async () => {
      server.use(
        rest.post(`${API_BASE}/api/${API_VERSION}/meetings/1/polls/1/votes`, (req, res, ctx) => {
          return res(ctx.status(400), ctx.json({}));
        })
      );

      await expect(API.vote(1, 1, 'token', 'yes')).rejects.toThrow('Vote failed');
    });
  });

  describe('createMeetingsSSE', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
    });

    it('should create SSE connection with token map', () => {
      const tokenMap = { '1': 'token1', '2': 'token2' };
      const onMessage = jest.fn();
      const onError = jest.fn();

      API.createMeetingsSSE(tokenMap, onMessage, onError);

      expect(MockEventSource.instances).toHaveLength(1);
      const instance = MockEventSource.instances[0];

      const expectedTokens = encodeURIComponent(JSON.stringify(tokenMap));
      expect(instance.url).toContain(`/api/${API_VERSION}/sse/meetings?tokens=${expectedTokens}`);
    });

    it('should call onMessage when receiving SSE message', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      API.createMeetingsSSE({}, onMessage, onError);

      const instance = MockEventSource.instances[0];
      const mockData = { meetings: [{ id: 1 }] };

      instance.onmessage({ data: JSON.stringify(mockData) });

      expect(onMessage).toHaveBeenCalledWith(mockData);
    });

    it('should handle invalid JSON in SSE message', () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation();
      const onMessage = jest.fn();
      const onError = jest.fn();

      API.createMeetingsSSE({}, onMessage, onError);

      const instance = MockEventSource.instances[0];
      instance.onmessage({ data: 'invalid json' });

      expect(onMessage).not.toHaveBeenCalled();
      expect(consoleError).toHaveBeenCalledWith('Failed to parse SSE message:', expect.any(Error));

      consoleError.mockRestore();
    });

    it('should call onError and attempt reconnection on error', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      const connection = API.createMeetingsSSE({}, onMessage, onError);

      const instance = MockEventSource.instances[0];
      instance.onerror(new Error('Connection failed'));

      expect(onError).toHaveBeenCalled();
      expect(instance.closed).toBe(true);

      // Fast-forward time to trigger reconnection
      jest.advanceTimersByTime(3000);

      // Should create a new EventSource for reconnection
      expect(MockEventSource.instances).toHaveLength(2);

      connection.close();
    });

    it('should not reconnect after close is called', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      const connection = API.createMeetingsSSE({}, onMessage, onError);
      connection.close();

      const instance = MockEventSource.instances[0];
      expect(instance.closed).toBe(true);

      // Trigger error after close
      instance.onerror(new Error('Connection failed'));

      // Fast-forward time
      jest.advanceTimersByTime(3000);

      // Should not create a new EventSource
      expect(MockEventSource.instances).toHaveLength(1);
    });

    it('should update tokens and reconnect', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      const connection = API.createMeetingsSSE({ '1': 'token1' }, onMessage, onError);

      expect(MockEventSource.instances).toHaveLength(1);

      const newTokenMap = { '1': 'token1', '2': 'token2' };
      connection.updateTokens(newTokenMap);

      // Should close old connection and create new one
      expect(MockEventSource.instances[0].closed).toBe(true);
      expect(MockEventSource.instances).toHaveLength(2);

      const newInstance = MockEventSource.instances[1];
      const expectedTokens = encodeURIComponent(JSON.stringify(newTokenMap));
      expect(newInstance.url).toContain(`tokens=${expectedTokens}`);

      connection.close();
    });

    it('should clear reconnect timer on updateTokens', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      const connection = API.createMeetingsSSE({}, onMessage, onError);

      const instance = MockEventSource.instances[0];
      instance.onerror(new Error('Connection failed'));

      // Update tokens before reconnect timer fires
      connection.updateTokens({ '1': 'new-token' });

      // Fast-forward past the original reconnect time
      jest.advanceTimersByTime(3000);

      // Should only have 2 instances (original + updateTokens), not 3
      expect(MockEventSource.instances).toHaveLength(2);

      connection.close();
    });
  });

  describe('createAdminSSE', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
    });

    it('should create admin SSE connection with credentials', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      API.createAdminSSE(onMessage, onError);

      expect(MockEventSource.instances).toHaveLength(1);
      const instance = MockEventSource.instances[0];

      expect(instance.url).toContain('/api/v1/sse/admin/meetings');
      expect(instance.options).toEqual({ withCredentials: true });
    });

    it('should call onMessage when receiving admin SSE message', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      API.createAdminSSE(onMessage, onError);

      const instance = MockEventSource.instances[0];
      const mockData = { meetings: [{ id: 1 }] };

      instance.onmessage({ data: JSON.stringify(mockData) });

      expect(onMessage).toHaveBeenCalledWith(mockData);
    });

    it('should handle invalid JSON in admin SSE message', () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation();
      const onMessage = jest.fn();
      const onError = jest.fn();

      API.createAdminSSE(onMessage, onError);

      const instance = MockEventSource.instances[0];
      instance.onmessage({ data: 'invalid json' });

      expect(onMessage).not.toHaveBeenCalled();
      expect(consoleError).toHaveBeenCalledWith('Failed to parse SSE message:', expect.any(Error));

      consoleError.mockRestore();
    });

    it('should call onError and attempt reconnection on error', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      const connection = API.createAdminSSE(onMessage, onError);

      const instance = MockEventSource.instances[0];
      instance.onerror(new Error('Connection failed'));

      expect(onError).toHaveBeenCalled();
      expect(instance.closed).toBe(true);

      // Fast-forward time to trigger reconnection
      jest.advanceTimersByTime(3000);

      // Should create a new EventSource for reconnection
      expect(MockEventSource.instances).toHaveLength(2);

      connection.close();
    });

    it('should not reconnect after close is called', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      const connection = API.createAdminSSE(onMessage, onError);
      connection.close();

      const instance = MockEventSource.instances[0];
      expect(instance.closed).toBe(true);

      // Trigger error after close
      instance.onerror(new Error('Connection failed'));

      // Fast-forward time
      jest.advanceTimersByTime(3000);

      // Should not create a new EventSource
      expect(MockEventSource.instances).toHaveLength(1);
    });

    it('should properly close connection and clear timers', () => {
      const onMessage = jest.fn();
      const onError = jest.fn();

      const connection = API.createAdminSSE(onMessage, onError);

      // Trigger an error to start reconnect timer
      const instance = MockEventSource.instances[0];
      instance.onerror(new Error('Connection failed'));

      // Close before reconnect happens
      connection.close();

      // Fast-forward time
      jest.advanceTimersByTime(3000);

      // Should still only have 1 instance (no reconnection)
      expect(MockEventSource.instances).toHaveLength(1);
    });
  });
});
