import React, { useState } from 'react';
import API from '../api';

function CheckInModal({ meeting, onSuccess, onClose }) {
  const [meetingCode, setMeetingCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Check if we already have a token for this meeting
      const existingToken = localStorage.getItem(`meeting_${meeting.id}_token`);
      
      const response = await API.checkin(meeting.id, meetingCode, existingToken);
      onSuccess(response.token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Check In to Meeting</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="meeting-code">Enter Meeting Code:</label>
            <input
              id="meeting-code"
              type="text"
              value={meetingCode}
              onChange={(e) => setMeetingCode(e.target.value.toUpperCase())}
              placeholder="MEETCODE"
              required
              autoFocus
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? 'Checking in...' : 'Check In'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CheckInModal;