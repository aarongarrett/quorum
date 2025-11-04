import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import API from '../api';
import CheckInModal from './CheckInModal';
import VoteModal from './VoteModal';

function Home() {
  const [meetings, setMeetings] = useState([]);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [selectedPoll, setSelectedPoll] = useState(null);
  const [showCheckinModal, setShowCheckinModal] = useState(false);
  const [showVoteModal, setShowVoteModal] = useState(false);
  const sseRef = useRef(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const checkedInFromQR = useRef(false);
  const [visibleVotes, setVisibleVotes] = useState({});
  const voteTimersRef = useRef({});
  const seenVotesRef = useRef(new Set()); // Track which poll IDs have already been auto-shown

  // Get token map from localStorage
  const getTokenMap = () => {
    const tokenMap = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith('meeting_') && key.endsWith('_token')) {
        const meetingId = parseInt(key.replace('meeting_', '').replace('_token', ''));
        tokenMap[meetingId] = localStorage.getItem(key);
      }
    }
    return tokenMap;
  };

  // Clean up tokens for meetings that are no longer available
  const cleanupOldTokens = (activeMeetings) => {
    const activeMeetingIds = new Set(activeMeetings.map(m => m.id));
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const key = localStorage.key(i);
      if (key && key.startsWith('meeting_') && key.endsWith('_token')) {
        const meetingId = parseInt(key.replace('meeting_', '').replace('_token', ''));
        if (!activeMeetingIds.has(meetingId)) {
          localStorage.removeItem(key);
        }
      }
    }
  };

  useEffect(() => {
    // Initial fetch
    const tokenMap = getTokenMap();
    API.getAvailableMeetings(tokenMap).then(data => {
      cleanupOldTokens(data);
      setMeetings(data);
    }).catch(console.error);

    // Set up SSE
    sseRef.current = API.createMeetingsSSE(
      tokenMap,
      (data) => {
        cleanupOldTokens(data);
        setMeetings(data);
      },
      (error) => console.error('SSE error:', error)
    );

    return () => {
      if (sseRef.current) {
        sseRef.current.close();
      }
    };
  }, []);

  // Check for meeting code in URL parameters and auto-check-in
  useEffect(() => {
    const meetingCode = searchParams.get('meeting');
    if (meetingCode && meetings.length > 0 && !checkedInFromQR.current) {
      checkedInFromQR.current = true;

      // Find the meeting with this code
      const meeting = meetings.find(m => m.meeting_code === meetingCode.toUpperCase());
      if (meeting && !meeting.checked_in) {
        // Auto check-in with the meeting code
        const existingToken = localStorage.getItem(`meeting_${meeting.id}_token`);
        API.checkin(meeting.id, meetingCode.toUpperCase(), existingToken)
          .then(response => {
            localStorage.setItem(`meeting_${meeting.id}_token`, response.token);

            // Refresh meetings to show checked-in status
            const tokenMap = getTokenMap();
            API.getAvailableMeetings(tokenMap).then(data => {
              cleanupOldTokens(data);
              setMeetings(data);
            }).catch(console.error);

            // Update SSE with new token map
            if (sseRef.current) {
              sseRef.current.updateTokens(tokenMap);
            }
          })
          .catch(error => {
            console.error('Auto check-in failed:', error);
          })
          .finally(() => {
            // Clear the URL parameter
            setSearchParams({});
          });
      } else {
        // Clear the URL parameter even if meeting not found or already checked in
        setSearchParams({});
      }
    }
  }, [meetings, searchParams, setSearchParams]);

  // Auto-hide votes after 3 seconds when they first appear
  useEffect(() => {
    meetings.forEach(meeting => {
      if (meeting.checked_in && meeting.polls) {
        meeting.polls.forEach(poll => {
          // Only auto-show if: vote exists AND not already seen AND not currently visible
          if (poll.vote && !seenVotesRef.current.has(poll.id) && !visibleVotes[poll.id]) {
            // Mark this vote as seen so we don't auto-show it again on SSE updates
            seenVotesRef.current.add(poll.id);

            // Vote exists but not currently visible - show it for 3 seconds
            setVisibleVotes(prev => ({ ...prev, [poll.id]: true }));

            // Clear any existing timer for this poll
            if (voteTimersRef.current[poll.id]) {
              clearTimeout(voteTimersRef.current[poll.id]);
            }

            // Set timer to hide after 3 seconds
            voteTimersRef.current[poll.id] = setTimeout(() => {
              setVisibleVotes(prev => ({ ...prev, [poll.id]: false }));
              delete voteTimersRef.current[poll.id];
            }, 3000);
          }
        });
      }
    });
  }, [meetings]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      Object.values(voteTimersRef.current).forEach(timer => clearTimeout(timer));
    };
  }, []);

  const handleCheckin = (meeting) => {
    setSelectedMeeting(meeting);
    setShowCheckinModal(true);
  };

  const handleCheckinSuccess = (token) => {
    localStorage.setItem(`meeting_${selectedMeeting.id}_token`, token);
    setShowCheckinModal(false);

    // Refresh meetings
    const tokenMap = getTokenMap();
    API.getAvailableMeetings(tokenMap).then(data => {
      cleanupOldTokens(data);
      setMeetings(data);
    }).catch(console.error);

    // Update SSE with new token map
    if (sseRef.current) {
      sseRef.current.updateTokens(tokenMap);
    }
  };

  const handleVote = (meeting, poll) => {
    setSelectedMeeting(meeting);
    setSelectedPoll(poll);
    setShowVoteModal(true);
  };

  const handleVoteSuccess = () => {
    setShowVoteModal(false);

    // Refresh meetings
    const tokenMap = getTokenMap();
    API.getAvailableMeetings(tokenMap).then(data => {
      cleanupOldTokens(data);
      setMeetings(data);
    }).catch(console.error);
  };

  const handleShowVote = (pollId) => {
    // Show the vote
    setVisibleVotes(prev => ({ ...prev, [pollId]: true }));

    // Clear any existing timer for this poll
    if (voteTimersRef.current[pollId]) {
      clearTimeout(voteTimersRef.current[pollId]);
    }

    // Set timer to hide after 3 seconds
    voteTimersRef.current[pollId] = setTimeout(() => {
      setVisibleVotes(prev => ({ ...prev, [pollId]: false }));
      delete voteTimersRef.current[pollId];
    }, 3000);
  };

  return (
    <div className="home">
      <div className="page-header">
        <h1 className="page-title">Available Meetings</h1>
      </div>

      <div className="card-grid">
        {meetings.length === 0 ? (
          <div className="no-meetings">
            <p>No meetings are currently available. Please check back later.</p>
          </div>
        ) : (
          meetings.map(meeting => {
            const startTime = new Date(meeting.start_time);
            const endTime = new Date(meeting.end_time);

            return (
              <div key={meeting.id} className="card meeting-card">
                <div className="meeting-date">
                  {startTime.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                </div>
                <div className="meeting-time">
                  {startTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: 'numeric' })} - {endTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: 'numeric' })}
                </div>

                {!meeting.checked_in ? (
                  <>
                    <div className="status-badge status-not-checked-in">
                      Not Checked In
                    </div>
                    <button
                      className="btn btn-primary"
                      onClick={() => handleCheckin(meeting)}
                    >
                      Check In
                    </button>
                  </>
                ) : (
                  <>
                    <div className="status-badge status-checked-in">✓ Checked In</div>
                    <div className="poll-list">
                      {meeting.polls.length > 0 ? (
                        meeting.polls.map(poll => (
                          <div key={poll.id} className="poll-item">
                            <h3 className="poll-title">{poll.name}</h3>
                            <div className="vote-status">
                              {poll.vote ? (
                                visibleVotes[poll.id] ? (
                                  <div className="status-message vote-cast">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '0.5rem' }}>
                                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                                      <polyline points="22 4 12 14.01 9 11.01"></polyline>
                                    </svg>
                                    <span>You have voted: <strong>{poll.vote}</strong></span>
                                  </div>
                                ) : (
                                  <button
                                    className="btn btn-secondary show-vote-btn"
                                    onClick={() => handleShowVote(poll.id)}
                                  >
                                    Show Vote
                                  </button>
                                )
                              ) : (
                                <button
                                  className="btn btn-primary"
                                  onClick={() => handleVote(meeting, poll)}
                                >
                                  Vote Now
                                </button>
                              )}
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="no-polls">
                          <p>No polls available.</p>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>

      {showCheckinModal && (
        <CheckInModal
          meeting={selectedMeeting}
          onSuccess={handleCheckinSuccess}
          onClose={() => setShowCheckinModal(false)}
        />
      )}

      {showVoteModal && (
        <VoteModal
          meeting={selectedMeeting}
          poll={selectedPoll}
          onSuccess={handleVoteSuccess}
          onClose={() => setShowVoteModal(false)}
        />
      )}
    </div>
  );
}

export default Home;