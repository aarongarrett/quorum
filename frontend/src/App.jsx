import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './components/Home';
import AdminLogin from './components/AdminLogin';
import AdminDashboard from './components/AdminDashboard';
import API from './api';
import './App.css';

function App() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    // Check if admin is authenticated by trying to fetch meetings
    // (cookie is httpOnly so we can't check it directly)
    const checkAuth = async () => {
      try {
        await API.getAllMeetings();
        setIsAdmin(true);
      } catch (err) {
        setIsAdmin(false);
      } finally {
        setAuthChecked(true);
      }
    };

    checkAuth();
  }, []);

  const handleLogout = async () => {
    try {
      // Call logout endpoint to clear cookie
      await API.adminLogout();
    } catch (err) {
      console.error('Logout error:', err);
    }
    setIsAdmin(false);
  };

  // Don't render routes until auth check is complete
  if (!authChecked) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>;
  }

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={
            <>
              <header className="app-header user-header">
                <h1>Quorum</h1>
              </header>
              <main className="app-main">
                <Home />
              </main>
            </>
          } />
          <Route path="/admin/login" element={
            <>
              <header className="app-header user-header">
                <h1>Quorum</h1>
              </header>
              <main className="app-main">
                <AdminLogin onLogin={() => setIsAdmin(true)} />
              </main>
            </>
          } />
          <Route path="/admin" element={
            isAdmin ? (
              <>
                <header className="app-header admin-header">
                  <h1>Quorum</h1>
                  <button className="btn btn-outline btn-logout" onClick={handleLogout}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                      <polyline points="16 17 21 12 16 7"></polyline>
                      <line x1="21" y1="12" x2="9" y2="12"></line>
                    </svg>
                    Logout
                  </button>
                </header>
                <main className="app-main">
                  <AdminDashboard />
                </main>
              </>
            ) : (
              <>
                <header className="app-header user-header">
                  <h1>Quorum</h1>
                </header>
                <main className="app-main">
                  <AdminLogin onLogin={() => setIsAdmin(true)} />
                </main>
              </>
            )
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;