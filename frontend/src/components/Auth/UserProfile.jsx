import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

const UserProfile = () => {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToggle = () => {
    setDropdownOpen(!dropdownOpen);
  };

  const handleClose = () => {
    setDropdownOpen(false);
  };

  const handleSettings = () => {
    navigate('/settings');
    handleClose();
  };

  const handleProfile = () => {
    navigate('/profile');
    handleClose();
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (isLoading || !isAuthenticated || !user) {
    return null;
  }

  const userInitial = (user.fullName || user.email || 'U').charAt(0).toUpperCase();

  return (
    <div className="user-profile" ref={dropdownRef}>
      <button
        className="user-profile-button"
        onClick={handleToggle}
        aria-label="User menu"
      >
        <div className="user-avatar">{userInitial}</div>
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="currentColor"
          style={{
            transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 200ms ease'
          }}
        >
          <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="2" fill="none" />
        </svg>
      </button>

      <div className={`user-dropdown ${!dropdownOpen ? 'hidden' : ''}`}>
        <div style={{ padding: '16px 24px', borderBottom: '1px solid #E0E0E0' }}>
          <p style={{
            fontWeight: 600,
            fontSize: '14px',
            margin: 0,
            marginBottom: '4px',
            color: '#1A1A1A'
          }}>
            {user.fullName || 'User'}
          </p>
          <p style={{
            fontSize: '12px',
            margin: 0,
            color: '#666666'
          }}>
            {user.email}
          </p>
        </div>

        <button className="user-dropdown-item" onClick={handleProfile}>
          Business Profile
        </button>

        <button className="user-dropdown-item" onClick={handleSettings}>
          Settings
        </button>

        <div style={{ borderTop: '1px solid #E0E0E0' }}>
          <button className="user-dropdown-item" onClick={handleLogout}>
            Log Out
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
