import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';

const LoginButton = ({ fullWidth = false }) => {
  const { loginWithRedirect } = useAuth0();

  return (
    <button
      className="btn btn-primary"
      onClick={() => loginWithRedirect()}
      style={{
        width: fullWidth ? '100%' : 'auto',
        fontSize: '18px',
        padding: '16px 32px'
      }}
    >
      Log In
    </button>
  );
};

export default LoginButton;
