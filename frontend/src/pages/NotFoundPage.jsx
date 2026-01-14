import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/swiss-theme.css';

const NotFoundPage = () => (
  <div className="container" style={{ padding: 'var(--space-8) var(--space-3)', textAlign: 'center' }}>
    <h1 style={{ fontSize: '6rem', marginBottom: 'var(--space-2)' }}>404</h1>
    <h2 style={{ marginBottom: 'var(--space-3)' }}>Page Not Found</h2>
    <p style={{ color: 'var(--color-gray-600)', marginBottom: 'var(--space-4)' }}>
      The page you're looking for doesn't exist or has been moved.
    </p>
    <Link to="/" className="btn btn-primary">
      ← Back to Home
    </Link>
  </div>
);

export default NotFoundPage;
