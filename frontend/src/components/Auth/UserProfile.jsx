import React, { useState, useEffect, useRef } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useNavigate } from 'react-router-dom';
import LogoutButton from './LogoutButton';

const UserProfile = () => {
  const { user, isAuthenticated, isLoading } = useAuth0();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // Close dropdown when clicking outside
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

  if (isLoading || !isAuthenticated) {
    return null;
  }

  const userInitial = user?.name?.charAt(0).toUpperCase() || 'U';

  return (
    <div className="user-profile" ref={dropdownRef}>
      <button
        className="user-profile-button"
        onClick={handleToggle}
        aria-label="User menu"
      >
        {user?.picture ? (
          <img
            src={user.picture}
            alt={user.name}
            className="user-avatar"
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '2px',
              objectFit: 'cover'
            }}
          />
        ) : (
          <div className="user-avatar">{userInitial}</div>
        )}
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
            {user?.name}
          </p>
          <p style={{
            fontSize: '12px',
            margin: 0,
            color: '#666666'
          }}>
            {user?.email}
          </p>
        </div>

        <button className="user-dropdown-item" onClick={handleProfile}>
          Business Profile
        </button>

        <button className="user-dropdown-item" onClick={handleSettings}>
          Settings
        </button>

        <div style={{ borderTop: '1px solid #E0E0E0' }}>
          <LogoutButton />
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
