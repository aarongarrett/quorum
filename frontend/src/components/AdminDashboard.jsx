import React, { useState, useEffect, useRef } from 'react';
import QRCode from 'qrcode.react';
import API from '../api';

function AdminDashboard() {
  const [meetings, setMeetings] = useState([]);
  const [showCreateMeeting, setShowCreateMeeting] = useState(false);
  const [showCreatePoll, setShowCreatePoll] = useState(null);
  const sseRef = useRef(null);

  useEffect(() => {
    // Initial fetch
    API.getAllMeetings().then(setMeetings).catch(console.error);

    // Set up SSE
    sseRef.current = API.createAdminSSE(
      (data) => setMeetings(data),
      (error) => console.error('SSE error:', error)
    );

    return () => {
      if (sseRef.current) sseRef.current.close();
    };
  }, []);

  const handleDeleteMeeting = async (meetingId) => {
    if (!window.confirm('Are you sure you want to delete this meeting? This will also delete all associated check-ins, polls, and votes. This action cannot be undone.')) return;

    try {
      await API.deleteMeeting(meetingId);
      setMeetings(meetings.filter(m => m.id !== meetingId));
    } catch (err) {
      alert('Failed to delete meeting: ' + err.message);
    }
  };

  const handleDeletePoll = async (meetingId, pollId, pollName) => {
    if (!window.confirm(`Are you sure you want to delete the poll "${pollName}"? This will also delete all votes for this poll. This action cannot be undone.`)) return;

    try {
      await API.deletePoll(meetingId, pollId);
      // Refresh meetings to get updated poll list
      const updatedMeetings = await API.getAllMeetings();
      setMeetings(updatedMeetings);
    } catch (err) {
      alert('Failed to delete poll: ' + err.message);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  return (
    <div className="admin-dashboard">
      <div className="dashboard-header">
        <h2>Admin Dashboard</h2>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateMeeting(true)}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
            <polyline points="17 21 17 13 7 13 7 21"></polyline>
            <polyline points="7 3 7 8 15 8"></polyline>
          </svg>
          Create Meeting
        </button>
      </div>

      {meetings.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <h3>No meetings found</h3>
          <p style={{ color: '#7f8c8d', margin: '1rem 0 1.5rem' }}>Create your first meeting to get started</p>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateMeeting(true)}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
              <polyline points="17 21 17 13 7 13 7 21"></polyline>
              <polyline points="7 3 7 8 15 8"></polyline>
            </svg>
            Create Meeting
          </button>
        </div>
      ) : (
        <div className="meetings-admin-list">
          {meetings.map(meeting => (
            <div key={meeting.id} className="meeting-admin-card">
              <div className="meeting-admin-header">
                <div>
                  <h2 className="card-title">{formatDate(meeting.start_time)}</h2>
                  <div className="card-meta">
                    <div className="card-meta-item">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="16" y1="2" x2="16" y2="6"></line>
                        <line x1="8" y1="2" x2="8" y2="6"></line>
                        <line x1="3" y1="10" x2="21" y2="10"></line>
                      </svg>
                      {formatTime(meeting.start_time)} - {formatTime(meeting.end_time)}
                    </div>
                    <div className="card-meta-item">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                        <circle cx="9" cy="7" r="4"></circle>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                      </svg>
                      <span className="checkin-count">{meeting.checkins}</span>&nbsp;Checked In
                    </div>
                  </div>
                </div>
                <div className="meeting-admin-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => setShowCreatePoll(meeting)}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
                      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                      <polyline points="17 21 17 13 7 13 7 21"></polyline>
                      <polyline points="7 3 7 8 15 8"></polyline>
                    </svg>
                    Create Poll
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleDeleteMeeting(meeting.id)}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      <line x1="10" y1="11" x2="10" y2="17"></line>
                      <line x1="14" y1="11" x2="14" y2="17"></line>
                    </svg>
                    Delete Meeting
                  </button>
                </div>
              </div>

              <div className="card-body">
                <div className="card-info">
                  <div className="card-left-sidebar">
                    <div className="meeting-code">
                      {meeting.meeting_code}
                    </div>
                    <div className="qr-code">
                      <QRCode value={`${window.location.origin}/?meeting=${meeting.meeting_code}`} size={100} level="H" />
                    </div>
                  </div>
                  <div className="card-details">
                    {meeting.polls && meeting.polls.length > 0 ? (
                      <table className="poll-table">
                        <thead>
                          <tr>
                            <th>Poll</th>
                            <th>Total Votes</th>
                            <th>A</th>
                            <th>B</th>
                            <th>C</th>
                            <th>D</th>
                            <th>E</th>
                            <th>F</th>
                            <th>G</th>
                            <th>H</th>
                            <th>Delete</th>
                          </tr>
                        </thead>
                        <tbody>
                          {meeting.polls.map(poll => (
                            <tr key={poll.id} className="poll-row">
                              <td>{poll.name}</td>
                              <td className="vote-count">{poll.total_votes}</td>
                              <td className="vote-count">{poll.votes.A || 0}</td>
                              <td className="vote-count">{poll.votes.B || 0}</td>
                              <td className="vote-count">{poll.votes.C || 0}</td>
                              <td className="vote-count">{poll.votes.D || 0}</td>
                              <td className="vote-count">{poll.votes.E || 0}</td>
                              <td className="vote-count">{poll.votes.F || 0}</td>
                              <td className="vote-count">{poll.votes.G || 0}</td>
                              <td className="vote-count">{poll.votes.H || 0}</td>
                              <td>
                                <button
                                  className="btn btn-sm btn-outline-danger delete-poll-btn"
                                  onClick={() => handleDeletePoll(meeting.id, poll.id, poll.name)}
                                >
                                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                    <line x1="10" y1="11" x2="10" y2="17"></line>
                                    <line x1="14" y1="11" x2="14" y2="17"></line>
                                  </svg>
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <p className="no-polls">No polls created yet for this meeting.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateMeeting && (
        <CreateMeetingModal
          onSuccess={() => {
            setShowCreateMeeting(false);
            API.getAllMeetings().then(setMeetings);
          }}
          onClose={() => setShowCreateMeeting(false)}
        />
      )}

      {showCreatePoll && (
        <CreatePollModal
          meeting={showCreatePoll}
          onSuccess={() => {
            setShowCreatePoll(null);
            API.getAllMeetings().then(setMeetings);
          }}
          onClose={() => setShowCreatePoll(null)}
        />
      )}
    </div>
  );
}

function CreateMeetingModal({ onSuccess, onClose }) {
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Set default date to today
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    setStartDate(dateStr);

    // Set default start time to next hour, rounded to nearest 15 minutes
    const nextHour = new Date();
    nextHour.setHours(nextHour.getHours() + 1);
    const minutes = Math.ceil(nextHour.getMinutes() / 15) * 15 % 60;
    nextHour.setMinutes(minutes);
    nextHour.setSeconds(0);

    const hours = String(nextHour.getHours()).padStart(2, '0');
    const mins = String(nextHour.getMinutes()).padStart(2, '0');
    setStartTime(`${hours}:${mins}`);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Combine date and time
      const startDateTime = `${startDate}T${startTime}`;

      // Calculate end time as 2 hours after start time
      const start = new Date(startDateTime);
      const end = new Date(start);
      end.setHours(end.getHours() + 2);

      // Format end time to datetime-local format
      const year = end.getFullYear();
      const month = String(end.getMonth() + 1).padStart(2, '0');
      const day = String(end.getDate()).padStart(2, '0');
      const hours = String(end.getHours()).padStart(2, '0');
      const mins = String(end.getMinutes()).padStart(2, '0');
      const endTime = `${year}-${month}-${day}T${hours}:${mins}`;

      await API.createMeeting(startDateTime, endTime);
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="meeting-date" className="form-label">Date</label>
            <input
              id="meeting-date"
              type="date"
              className="form-input"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="meeting-start-time" className="form-label">Start Time</label>
            <input
              id="meeting-start-time"
              type="time"
              className="form-input"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              required
            />
            <p style={{ fontSize: '0.875rem', color: '#7f8c8d', marginTop: '0.5rem' }}>
              Meeting will last 2 hours
            </p>
          </div>
          {error && <div className="error-message">{error}</div>}
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                <polyline points="17 21 17 13 7 13 7 21"></polyline>
                <polyline points="7 3 7 8 15 8"></polyline>
              </svg>
              {loading ? 'Creating...' : 'Create Meeting'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CreatePollModal({ meeting, onSuccess, onClose }) {
  const [pollName, setPollName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await API.createPoll(meeting.id, pollName);
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="poll-name" className="form-label">Poll Name</label>
            <input
              id="poll-name"
              type="text"
              className="form-input"
              value={pollName}
              onChange={(e) => setPollName(e.target.value)}
              required
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="btn-icon">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                <polyline points="17 21 17 13 7 13 7 21"></polyline>
                <polyline points="7 3 7 8 15 8"></polyline>
              </svg>
              {loading ? 'Creating...' : 'Create Poll'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AdminDashboard;
