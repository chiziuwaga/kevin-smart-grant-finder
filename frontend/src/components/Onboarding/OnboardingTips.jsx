import React, { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import './OnboardingTips.css';

/**
 * Onboarding tips system.
 * - Shows contextual tips per page on first visit
 * - Per-user persistence via localStorage (keyed by user email)
 * - Replayable: call resetTips() to show all tips again
 */

const TIPS_BY_ROUTE = {
  '/': [
    {
      id: 'dashboard-welcome',
      title: 'Welcome to your Dashboard',
      body: 'This is your command center. See your latest grant matches, search stats, and quick actions all in one place.',
      position: { top: 80, left: 260 },
      arrow: 'left',
    },
    {
      id: 'dashboard-sidebar',
      title: 'Navigate with the sidebar',
      body: 'Use the sidebar to jump between grants, searches, applications, and your business profile. On mobile, tap the menu icon.',
      position: { top: 120, left: 20 },
      arrow: 'top',
    },
  ],
  '/search': [
    {
      id: 'search-intro',
      title: 'AI-Powered Search',
      body: 'Enter keywords or let AI discover grants based on your business profile. Results are scored by relevance, compliance, and fit.',
      position: { top: 140, left: 280 },
      arrow: 'top',
    },
  ],
  '/grants': [
    {
      id: 'grants-filters',
      title: 'Filter your results',
      body: 'Use the filter bar to narrow grants by score, deadline, or category. Click any row to see full details.',
      position: { top: 180, left: 280 },
      arrow: 'top',
    },
  ],
  '/profile': [
    {
      id: 'profile-importance',
      title: 'Your business profile matters',
      body: 'The more complete your profile, the better our AI can match you with relevant grants. Sectors, mission, and geographic focus all improve results.',
      position: { top: 140, left: 280 },
      arrow: 'top',
    },
  ],
  '/applications': [
    {
      id: 'applications-intro',
      title: 'Generate applications',
      body: 'Select a grant and generate a tailored application using AI. Your business profile provides the context for personalized content.',
      position: { top: 140, left: 280 },
      arrow: 'top',
    },
  ],
  '/analytics': [
    {
      id: 'analytics-intro',
      title: 'Track your progress',
      body: 'See your search history, grant matches over time, and application success metrics all in one view.',
      position: { top: 140, left: 280 },
      arrow: 'top',
    },
  ],
};

const STORAGE_KEY_PREFIX = 'sgf_onboarding_';

function getStorageKey(userEmail) {
  return `${STORAGE_KEY_PREFIX}${userEmail || 'default'}`;
}

function getSeenTips(userEmail) {
  try {
    const raw = localStorage.getItem(getStorageKey(userEmail));
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function markTipSeen(userEmail, tipId) {
  const seen = getSeenTips(userEmail);
  seen[tipId] = Date.now();
  localStorage.setItem(getStorageKey(userEmail), JSON.stringify(seen));
}

function resetAllTips(userEmail) {
  localStorage.removeItem(getStorageKey(userEmail));
}

/**
 * Main onboarding tips component.
 * Place this inside the app layout (after <Outlet />).
 *
 * Props:
 *   userEmail - current user email for per-user persistence
 */
export function OnboardingTips({ userEmail }) {
  const location = useLocation();
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  const [tips, setTips] = useState([]);
  const [dismissed, setDismissed] = useState(false);

  // Determine which tips to show for this route
  useEffect(() => {
    const routeTips = TIPS_BY_ROUTE[location.pathname] || [];
    const seen = getSeenTips(userEmail);
    const unseen = routeTips.filter((t) => !seen[t.id]);

    if (unseen.length > 0) {
      setTips(unseen);
      setCurrentTipIndex(0);
      setDismissed(false);
    } else {
      setTips([]);
      setDismissed(true);
    }
  }, [location.pathname, userEmail]);

  const handleNext = useCallback(() => {
    const current = tips[currentTipIndex];
    if (current) {
      markTipSeen(userEmail, current.id);
    }

    if (currentTipIndex < tips.length - 1) {
      setCurrentTipIndex((i) => i + 1);
    } else {
      setDismissed(true);
    }
  }, [tips, currentTipIndex, userEmail]);

  const handleDismissAll = useCallback(() => {
    tips.forEach((t) => markTipSeen(userEmail, t.id));
    setDismissed(true);
  }, [tips, userEmail]);

  if (dismissed || tips.length === 0) return null;

  const tip = tips[currentTipIndex];

  return (
    <>
      <div className="onboarding-overlay" onClick={handleDismissAll} />
      <div
        className="onboarding-tip"
        style={{ top: tip.position.top, left: tip.position.left }}
      >
        <div className={`onboarding-tip-arrow ${tip.arrow || 'top'}`} />

        <div className="onboarding-tip-step">
          <span className="onboarding-tip-step-badge">
            TIP {currentTipIndex + 1}/{tips.length}
          </span>
        </div>

        <h4 className="onboarding-tip-title">{tip.title}</h4>
        <p className="onboarding-tip-body">{tip.body}</p>

        <div className="onboarding-tip-footer">
          <div className="onboarding-tip-dots">
            {tips.map((_, i) => (
              <div
                key={i}
                className={`onboarding-tip-dot ${i === currentTipIndex ? 'active' : ''}`}
              />
            ))}
          </div>
          <div className="onboarding-tip-actions">
            <button
              className="btn btn-text btn-small"
              onClick={handleDismissAll}
            >
              Skip
            </button>
            <button
              className="btn btn-primary btn-small"
              onClick={handleNext}
            >
              {currentTipIndex < tips.length - 1 ? 'Next' : 'Got it'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * Small button for sidebar footer to replay tips.
 */
export function ReplayTipsButton({ userEmail, onReplay }) {
  const handleReplay = () => {
    resetAllTips(userEmail);
    if (onReplay) onReplay();
    // Force re-render by reloading route tips
    window.dispatchEvent(new Event('onboarding-reset'));
  };

  return (
    <button className="onboarding-replay-btn" onClick={handleReplay}>
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 7C2 4.24 4.24 2 7 2C9.76 2 12 4.24 12 7C12 9.76 9.76 12 7 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <path d="M4 4L2 7L5 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
      Replay tips
    </button>
  );
}

export default OnboardingTips;
