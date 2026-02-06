import React, { useEffect, useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import UserProfile from '../Auth/UserProfile';
import { OnboardingTips, ReplayTipsButton } from '../Onboarding/OnboardingTips';

const AppLayout = () => {
  const [open, setOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const location = useLocation();
  const [lastRunTime, setLastRunTime] = useState('—');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [tipsKey, setTipsKey] = useState(0);

  // Get user email from localStorage (set by Auth0 on login)
  const userEmail = localStorage.getItem('user_email') || 'default';

  // Handle responsive behavior
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleDrawerToggle = () => {
    setOpen(!open);
  };

  // Fetch last run time
  useEffect(() => {
    const fetchLastRun = async () => {
      try {
        const { getLastRun } = await import('../../api/apiClient');
        const data = await getLastRun();
        if (data.status !== 'none') {
          setLastRunTime(new Date(data.end || data.start).toLocaleString());
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchLastRun();
    const interval = setInterval(fetchLastRun, 60000);
    return () => clearInterval(interval);
  }, []);

  const menuItems = [
    { text: 'Dashboard', path: '/' },
    { text: 'All Grants', path: '/grants' },
    { text: 'Search', path: '/search' },
    { text: 'Saved Grants', path: '/saved' },
    { text: 'Applications', path: '/applications' },
    { text: 'Business Profile', path: '/profile' },
    { text: 'Analytics', path: '/analytics' },
    { text: 'Settings', path: '/settings' }
  ];

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className={`app-sidebar ${!open ? 'closed' : ''}`}>
        <div className="sidebar-header">
          <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>
            Smart Grant Finder
          </h2>
        </div>

        <nav style={{ flex: 1, overflowY: 'auto' }}>
          <ul className="nav-list">
            {menuItems.map((item) => (
              <li key={item.text} className="nav-item">
                <Link
                  to={item.path}
                  className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
                  onClick={isMobile ? handleDrawerToggle : undefined}
                >
                  {item.text}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <div style={{ marginBottom: '8px' }}>
            <p className="text-sm text-secondary" style={{ margin: 0 }}>
              System Status: All Good
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <p className="text-xs text-secondary" style={{ margin: 0 }}>
              Last run: {lastRunTime}
            </p>
            <button
              className="btn-text btn-small"
              onClick={() => setHistoryOpen(true)}
              style={{ padding: '4px 8px' }}
            >
              History
            </button>
          </div>
          <p className="text-xs text-secondary" style={{ margin: 0 }}>
            Version 1.0.0
          </p>
          <ReplayTipsButton
            userEmail={userEmail}
            onReplay={() => setTipsKey((k) => k + 1)}
          />
        </div>
      </aside>

      {/* Mobile Overlay */}
      {isMobile && open && (
        <div
          className="sidebar-overlay"
          onClick={handleDrawerToggle}
        />
      )}

      {/* Header */}
      <header className={`app-header ${!open ? 'sidebar-closed' : ''}`}>
        <button
          className="menu-toggle"
          onClick={handleDrawerToggle}
          aria-label="Toggle menu"
        >
          <svg
            className="menu-icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            {open ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            )}
          </svg>
        </button>

        <h1 style={{ fontSize: '18px', fontWeight: 600, margin: 0, flex: 1 }}>
          Smart Grant Finder
        </h1>

        <UserProfile />
      </header>

      {/* Main Content */}
      <main className={`app-main ${!open ? 'sidebar-closed' : ''}`}>
        <Outlet />
      </main>

      {/* Onboarding Tips */}
      <OnboardingTips key={tipsKey} userEmail={userEmail} />

      {/* Run History Modal - placeholder for now */}
      {historyOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setHistoryOpen(false)}
        >
          <div
            className="card"
            style={{
              minWidth: '400px',
              maxWidth: '600px',
              maxHeight: '80vh',
              overflow: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0 }}>Run History</h3>
              <button
                className="btn-text"
                onClick={() => setHistoryOpen(false)}
              >
                Close
              </button>
            </div>
            <p className="text-secondary">Run history will be displayed here.</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default AppLayout;
