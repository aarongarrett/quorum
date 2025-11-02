import { rest } from 'msw';

const API_BASE = 'http://localhost';
const API_VERSION = 'v1';

export const handlers = [
  // Get available meetings
  rest.post(`${API_BASE}/api/${API_VERSION}/meetings/available`, (req, res, ctx) => {
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

  // Check in
  rest.post(`${API_BASE}/api/${API_VERSION}/meetings/:id/checkins`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        token: 'mock-token-12345'
      })
    );
  }),

  // Vote
  rest.post(`${API_BASE}/api/${API_VERSION}/meetings/:meetingId/polls/:pollId/votes`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true
      })
    );
  }),

  // Admin login - now sets cookie instead of returning token
  rest.post(`${API_BASE}/api/${API_VERSION}/auth/admin/login`, (req, res, ctx) => {
    const { password } = req.body;
    if (password === 'testpass') {
      return res(
        ctx.status(200),
        ctx.cookie('admin_token', 'mock-jwt-token', { httpOnly: true }),
        ctx.json({
          success: true,
          message: 'Logged in successfully'
        })
      );
    }
    return res(ctx.status(401));
  }),

  // Admin logout
  rest.post(`${API_BASE}/api/${API_VERSION}/auth/admin/logout`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.cookie('admin_token', '', { httpOnly: true, maxAge: 0 }),
      ctx.json({
        success: true,
        message: 'Logged out successfully'
      })
    );
  }),

  // Get all meetings (admin)
  rest.get(`${API_BASE}/api/${API_VERSION}/admin/meetings`, (req, res, ctx) => {
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
  }),

  // Create meeting (admin)
  rest.post(`${API_BASE}/api/${API_VERSION}/meetings`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        meeting_id: 1,
        meeting_code: 'NEWTEST1'
      })
    );
  }),

  // Create poll (admin)
  rest.post(`${API_BASE}/api/${API_VERSION}/meetings/:id/polls`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        poll_id: 1
      })
    );
  }),
];
