import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import LoginButton from './LoginButton';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth0();

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: '20px'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          border: '3px solid #E0E0E0',
          borderTop: '3px solid #1A1A1A',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
        <p style={{ marginTop: '16px', fontSize: '16px', color: '#1A1A1A' }}>
          Loading...
        </p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        textAlign: 'center',
        padding: '20px',
        maxWidth: '600px',
        margin: '0 auto'
      }}>
        <h1 style={{
          fontSize: '48px',
          fontWeight: 700,
          marginBottom: '16px',
          color: '#1A1A1A'
        }}>
          Smart Grant Finder
        </h1>
        <p style={{
          fontSize: '16px',
          color: '#666666',
          marginBottom: '32px'
        }}>
          Please log in to access your grant dashboard
        </p>
        <LoginButton fullWidth />
      </div>
    );
  }

  return <>{children}</>;
};

export default ProtectedRoute;
