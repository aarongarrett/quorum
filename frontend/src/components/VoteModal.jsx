import React, { useState } from 'react';
import API from '../api';

const VOTE_OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

function VoteModal({ meeting, poll, onSuccess, onClose }) {
  const [selectedVote, setSelectedVote] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!selectedVote) {
      setError('Please select an option');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const token = localStorage.getItem(`meeting_${meeting.id}_token`);
      
      if (!token) {
        throw new Error('No check-in token found. Please check in first.');
      }

      await API.vote(meeting.id, poll.id, token, selectedVote);
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
        <h2>Vote in Poll</h2>
        <h3>{poll.name}</h3>
        
        <form onSubmit={handleSubmit}>
          <div className="vote-options">
            {VOTE_OPTIONS.map(option => (
              <label key={option} className="vote-option">
                <input
                  type="radio"
                  name="vote"
                  value={option}
                  checked={selectedVote === option}
                  onChange={(e) => setSelectedVote(e.target.value)}
                />
                <span className="vote-label">{option}</span>
              </label>
            ))}
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? 'Submitting...' : 'Submit Vote'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default VoteModal;