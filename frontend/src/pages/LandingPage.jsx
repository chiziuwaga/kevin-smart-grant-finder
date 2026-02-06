import React from 'react';
import { Link } from 'react-router-dom';

/* SVG icons for feature cards — niche grant/money themed */
const icons = {
  search: (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="14" cy="14" r="9" stroke="#1A1A1A" strokeWidth="2"/>
      <path d="M14 10V18M10 14H18" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round"/>
      <path d="M21 21L27 27" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),
  score: (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="18" width="6" height="10" rx="1" stroke="#1A1A1A" strokeWidth="2"/>
      <rect x="13" y="12" width="6" height="16" rx="1" stroke="#1A1A1A" strokeWidth="2"/>
      <rect x="22" y="4" width="6" height="24" rx="1" stroke="#1A1A1A" strokeWidth="2"/>
    </svg>
  ),
  document: (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 4H20L26 10V28H8V4Z" stroke="#1A1A1A" strokeWidth="2" strokeLinejoin="round"/>
      <path d="M20 4V10H26" stroke="#1A1A1A" strokeWidth="2" strokeLinejoin="round"/>
      <path d="M12 16H22M12 20H22M12 24H18" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),
  clock: (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="12" stroke="#1A1A1A" strokeWidth="2"/>
      <path d="M16 8V16L21 21" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="16" cy="16" r="2" fill="#1A1A1A"/>
    </svg>
  ),
};

const features = [
  {
    icon: icons.search,
    title: 'AI-Powered Discovery',
    desc: 'DeepSeek reasoning discovers grants across federal, state, and foundation sources — tailored to your business profile.',
  },
  {
    icon: icons.score,
    title: 'Smart Scoring',
    desc: 'Multi-dimensional scoring evaluates relevance, compliance, feasibility, and strategic alignment automatically.',
  },
  {
    icon: icons.document,
    title: 'Application Generation',
    desc: 'Generate grant applications from your business profile using RAG-powered AI that adapts to each opportunity.',
  },
  {
    icon: icons.clock,
    title: 'Works While You Sleep',
    desc: 'Scheduled searches run every 6 hours so you never miss a deadline. Get email alerts for high-priority matches.',
  },
];

const LandingPage = () => {
  return (
    <div style={{
      minHeight: '100vh',
      fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
    }}>
      {/* Nav */}
      <header className="landing-nav" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px 40px',
        maxWidth: '1200px',
        margin: '0 auto',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="#1A1A1A" strokeWidth="2"/>
            <path d="M12 6V12L16 16" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round"/>
            <path d="M8 8L12 12" stroke="#1A1A1A" strokeWidth="1.5" strokeLinecap="round" opacity="0.4"/>
          </svg>
          <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: '#1A1A1A' }}>
            Smart Grant Finder
          </h2>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <Link to="/login" className="btn btn-secondary" style={{ padding: '10px 24px', fontSize: '14px' }}>
            Sign In
          </Link>
          <Link to="/register" className="btn btn-primary" style={{ padding: '10px 24px', fontSize: '14px' }}>
            Get Started
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="landing-hero landing-section landing-bg-dots" style={{
        textAlign: 'center',
        padding: '80px 40px 60px',
        maxWidth: '800px',
        margin: '0 auto',
      }}>
        <h1 className="landing-hero-title" style={{
          fontSize: '52px',
          fontWeight: 700,
          lineHeight: 1.15,
          color: '#1A1A1A',
          margin: '0 0 24px 0',
        }}>
          Money finder for your
          <br />
          business while you sleep.
        </h1>
        <p className="landing-hero-subtitle" style={{
          fontSize: '20px',
          lineHeight: 1.6,
          color: '#666666',
          margin: '0 0 40px 0',
          maxWidth: '600px',
          marginLeft: 'auto',
          marginRight: 'auto',
        }}>
          AI-powered grant discovery and application generation for
          nonprofits, small businesses, and community organizations.
        </p>
        <div className="landing-cta-row" style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
          <Link
            to="/register"
            className="btn btn-primary cta-pulse"
            style={{ padding: '16px 40px', fontSize: '18px', fontWeight: 600 }}
          >
            Start Free Trial
          </Link>
          <Link
            to="/login"
            className="btn btn-secondary"
            style={{ padding: '16px 40px', fontSize: '18px' }}
          >
            Sign In
          </Link>
        </div>
        <p style={{ fontSize: '14px', color: '#999', marginTop: '16px' }}>
          5 free searches included &middot; No credit card required
        </p>
      </section>

      {/* Features */}
      <section className="landing-features landing-section" style={{
        padding: '60px 40px',
        maxWidth: '1100px',
        margin: '0 auto',
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '32px',
        }}>
          {features.map((f, i) => (
            <div
              key={i}
              className="card feature-card"
              style={{
                padding: '32px',
                cursor: 'default',
              }}
            >
              <div style={{ marginBottom: '16px', opacity: 0.85 }}>
                {f.icon}
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 12px 0', color: '#1A1A1A' }}>
                {f.title}
              </h3>
              <p style={{ fontSize: '15px', lineHeight: 1.6, color: '#666666', margin: 0 }}>
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="landing-section" style={{
        padding: '60px 40px',
        maxWidth: '800px',
        margin: '0 auto',
        textAlign: 'center',
      }}>
        <h2 style={{ fontSize: '32px', fontWeight: 700, marginBottom: '48px', color: '#1A1A1A' }}>
          How It Works
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', textAlign: 'left' }}>
          {[
            { step: '01', title: 'Create your business profile', desc: 'Tell us about your organization, mission, and target sectors.' },
            { step: '02', title: 'AI discovers matching grants', desc: 'Our engine searches federal, state, and foundation databases using DeepSeek reasoning.' },
            { step: '03', title: 'Review scored results', desc: 'Grants are ranked by relevance, compliance, and strategic fit for your organization.' },
            { step: '04', title: 'Generate applications', desc: 'AI drafts tailored grant applications based on your business profile and the specific opportunity.' },
          ].map((item) => (
            <div key={item.step} className="landing-step" style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
              <div style={{
                fontSize: '14px',
                fontWeight: 700,
                color: '#999',
                minWidth: '32px',
                lineHeight: '28px',
              }}>
                {item.step}
              </div>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 600, margin: '0 0 4px 0', color: '#1A1A1A' }}>
                  {item.title}
                </h3>
                <p style={{ fontSize: '15px', color: '#666', margin: 0, lineHeight: 1.5 }}>
                  {item.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing hint */}
      <section className="landing-section" style={{
        textAlign: 'center',
        padding: '40px 40px',
        maxWidth: '600px',
        margin: '0 auto',
      }}>
        <div className="card" style={{ padding: '32px', textAlign: 'center' }}>
          <p style={{ fontSize: '14px', fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: '1px', margin: '0 0 8px 0' }}>
            Simple Pricing
          </p>
          <p style={{ fontSize: '36px', fontWeight: 700, color: '#1A1A1A', margin: '0 0 8px 0' }}>
            $15<span style={{ fontSize: '16px', fontWeight: 400, color: '#666' }}>/month</span>
          </p>
          <p style={{ fontSize: '15px', color: '#666', margin: 0 }}>
            50 AI searches &middot; Unlimited applications &middot; Email alerts
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="landing-section" style={{
        textAlign: 'center',
        padding: '60px 40px 80px',
        maxWidth: '600px',
        margin: '0 auto',
      }}>
        <h2 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '16px', color: '#1A1A1A' }}>
          Ready to find funding?
        </h2>
        <p style={{ fontSize: '16px', color: '#666', marginBottom: '32px' }}>
          Join organizations already using Smart Grant Finder to discover
          money for their business while they sleep.
        </p>
        <Link
          to="/register"
          className="btn btn-primary"
          style={{ padding: '16px 48px', fontSize: '18px', fontWeight: 600 }}
        >
          Get Started Free
        </Link>
      </section>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid #E0E0E0',
        padding: '24px 40px',
        textAlign: 'center',
      }}>
        <p style={{ fontSize: '13px', color: '#999', margin: 0 }}>
          Smart Grant Finder &copy; {new Date().getFullYear()}
        </p>
      </footer>
    </div>
  );
};

export default LandingPage;
