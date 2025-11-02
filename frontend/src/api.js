const API_BASE = import.meta.env.VITE_API_URL || '';
const API_VERSION = 'v1';
// SSE must bypass proxy and connect directly to backend
// In production (Render), use current origin; in dev, use localhost
const SSE_BASE = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000');

class API {
  // Auth
  static async adminLogin(password) {
    const response = await fetch(`${API_BASE}/api/${API_VERSION}/auth/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
      credentials: 'include'  // Important: sends cookies with request
    });

    if (!response.ok) throw new Error('Invalid password');
    return response.json();
  }

  static async adminLogout() {
    const response = await fetch(`${API_BASE}/api/${API_VERSION}/auth/admin/logout`, {
      method: 'POST',
      credentials: 'include'  // Important: sends cookies with request
    });

    if (!response.ok) throw new Error('Logout failed');
    return response.json();
  }

  // Meetings
  static async createMeeting(startTime, endTime) {
    // Convert datetime-local strings (YYYY-MM-DDTHH:mm) to ISO strings with Eastern timezone
    // datetime-local gives us naive strings, so we need to explicitly add timezone info
    const toEasternISO = (datetimeLocal) => {
      // Parse the datetime-local string (format: YYYY-MM-DDTHH:mm)
      const parts = datetimeLocal.match(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
      if (!parts) throw new Error('Invalid datetime format');

      const year = parseInt(parts[1]);
      const month = parseInt(parts[2]) - 1; // JS months are 0-indexed
      const day = parseInt(parts[3]);
      const hour = parseInt(parts[4]);
      const minute = parseInt(parts[5]);

      // Create a test date to check if DST is in effect for this specific date AND time
      // in the Eastern timezone (important for DST transition days)
      const testDate = new Date(year, month, day, hour, minute);
      const isDST = testDate.toLocaleString('en-US', {
        timeZone: 'America/New_York',
        timeZoneName: 'short'
      }).includes('EDT');

      // Eastern timezone offset: -05:00 for EST, -04:00 for EDT
      const tzOffset = isDST ? '-04:00' : '-05:00';

      // Return ISO 8601 string with explicit timezone
      return `${parts[1]}-${parts[2]}-${parts[3]}T${parts[4]}:${parts[5]}:00${tzOffset}`;
    };

    const response = await fetch(`${API_BASE}/api/${API_VERSION}/meetings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',  // Sends cookies with request
      body: JSON.stringify({
        start_time: toEasternISO(startTime),
        end_time: toEasternISO(endTime)
      })
    });

    if (!response.ok) throw new Error('Failed to create meeting');
    return response.json();
  }

  static async getAvailableMeetings(tokenMap = {}) {
    const response = await fetch(`${API_BASE}/api/${API_VERSION}/meetings/available`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tokenMap)
    });

    if (!response.ok) throw new Error('Failed to fetch meetings');
    return response.json();
  }

  static async getAllMeetings() {
    const response = await fetch(`${API_BASE}/api/${API_VERSION}/admin/meetings`, {
      credentials: 'include'  // Sends cookies with request
    });

    if (!response.ok) throw new Error('Failed to fetch meetings');
    return response.json();
  }

  static async deleteMeeting(meetingId) {
    const response = await fetch(`${API_BASE}/api/${API_VERSION}/admin/meetings/${meetingId}`, {
      method: 'DELETE',
      credentials: 'include'  // Sends cookies with request
    });

    if (!response.ok) throw new Error('Failed to delete meeting');
    return response.json();
  }

  // Polls
  static async createPoll(meetingId, name) {
    const response = await fetch(`${API_BASE}/api/${API_VERSION}/meetings/${meetingId}/polls`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',  // Sends cookies with request
      body: JSON.stringify({ name })
    });

    if (!response.ok) throw new Error('Failed to create poll');
    return response.json();
  }

  static async deletePoll(meetingId, pollId) {
    const response = await fetch(`${API_BASE}/api/${API_VERSION}/admin/meetings/${meetingId}/polls/${pollId}`, {
      method: 'DELETE',
      credentials: 'include'  // Sends cookies with request
    });

    if (!response.ok) throw new Error('Failed to delete poll');
    return response.json();
  }

  // Check-in
  static async checkin(meetingId, meetingCode, existingToken = null) {
    const response = await fetch(`${API_BASE}/api/${API_VERSION}/meetings/${meetingId}/checkins`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        meeting_code: meetingCode,
        token: existingToken
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Check-in failed');
    }
    return response.json();
  }

  // Vote
  static async vote(meetingId, pollId, token, vote) {
    const response = await fetch(`${API_BASE}/api/${API_VERSION}/meetings/${meetingId}/polls/${pollId}/votes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, vote })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Vote failed');
    }
    return response.json();
  }

  // SSE helpers with automatic reconnection

  /**
   * Generic SSE connection helper with automatic reconnection.
   * @private
   * @param {Function} urlBuilder - Function that returns the SSE URL
   * @param {Function} onMessage - Callback for incoming messages
   * @param {Function} onError - Callback for errors
   * @param {Object} options - Additional options (withCredentials, etc.)
   * @returns {Object} Object with close() method and optional update() method
   */
  static _createSSEConnection(urlBuilder, onMessage, onError, options = {}) {
    let eventSource = null;
    let reconnectTimer = null;
    let isClosed = false;

    const connect = () => {
      if (isClosed) return;

      const url = urlBuilder();
      const eventSourceOptions = options.withCredentials ? { withCredentials: true } : undefined;

      eventSource = new EventSource(url, eventSourceOptions);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (err) {
          console.error('Failed to parse SSE message:', err);
        }
      };

      eventSource.onerror = (error) => {
        if (onError) onError(error);

        // Close the current connection
        if (eventSource) {
          eventSource.close();
        }

        // Attempt reconnection after 3 seconds if not manually closed
        if (!isClosed) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };
    };

    connect();

    // Return connection control object
    const connection = {
      close: () => {
        isClosed = true;
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
        }
        if (eventSource) {
          eventSource.close();
        }
      }
    };

    // Add reconnect method if provided in options
    if (options.reconnect) {
      connection.reconnect = () => {
        if (eventSource) {
          eventSource.close();
        }
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
        }
        connect();
      };
    }

    return connection;
  }

  /**
   * Create SSE connection for meetings endpoint (user view).
   * Supports dynamic token updates for real-time check-in tracking.
   */
  static createMeetingsSSE(tokenMap, onMessage, onError) {
    let currentTokenMap = tokenMap;

    const connection = this._createSSEConnection(
      () => {
        const tokens = encodeURIComponent(JSON.stringify(currentTokenMap));
        return `${SSE_BASE}/api/${API_VERSION}/sse/meetings?tokens=${tokens}`;
      },
      onMessage,
      onError,
      { reconnect: true }
    );

    // Add updateTokens method for dynamic token updates
    connection.updateTokens = (newTokenMap) => {
      currentTokenMap = newTokenMap;
      connection.reconnect();
    };

    return connection;
  }

  /**
   * Create SSE connection for admin dashboard endpoint.
   * Requires authentication via httpOnly cookies.
   */
  static createAdminSSE(onMessage, onError) {
    return this._createSSEConnection(
      () => `${SSE_BASE}/api/${API_VERSION}/sse/admin/meetings`,
      onMessage,
      onError,
      { withCredentials: true }
    );
  }
}

export default API;