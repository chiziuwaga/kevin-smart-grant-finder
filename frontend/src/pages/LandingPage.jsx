import React from 'react';
import { Link } from 'react-router-dom';

const features = [
  {
    title: 'AI-Powered Search',
    desc: 'DeepSeek reasoning discovers grants across federal, state, and foundation sources tailored to your business profile.',
  },
  {
    title: 'Smart Scoring',
    desc: 'Multi-dimensional scoring evaluates relevance, compliance, feasibility, and strategic alignment automatically.',
  },
  {
    title: 'Application Generation',
    desc: 'Generate grant applications from your business profile using RAG-powered AI that adapts to each opportunity.',
  },
  {
    title: 'Automated Monitoring',
    desc: 'Scheduled searches run every 6 hours so you never miss a deadline. Get email alerts for high-priority matches.',
  },
];

const LandingPage = () => {
  return (
    <div style={{
      minHeight: '100vh',
      background: '#FAFAFA',
      fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
    }}>
      {/* Nav */}
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px 40px',
        maxWidth: '1200px',
        margin: '0 auto',
      }}>
        <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: '#1A1A1A' }}>
          Smart Grant Finder
        </h2>
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
      <section style={{
        textAlign: 'center',
        padding: '80px 40px 60px',
        maxWidth: '800px',
        margin: '0 auto',
      }}>
        <h1 style={{
          fontSize: '52px',
          fontWeight: 700,
          lineHeight: 1.15,
          color: '#1A1A1A',
          margin: '0 0 24px 0',
        }}>
          Find grants that fit.
          <br />
          Apply with confidence.
        </h1>
        <p style={{
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
        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
          <Link
            to="/register"
            className="btn btn-primary"
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
          5 free searches included. No credit card required.
        </p>
      </section>

      {/* Features */}
      <section style={{
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
              className="card"
              style={{
                padding: '32px',
                transition: 'transform 200ms ease, box-shadow 200ms ease',
                cursor: 'default',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '';
              }}
            >
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
      <section style={{
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
            <div key={item.step} style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
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

      {/* CTA */}
      <section style={{
        textAlign: 'center',
        padding: '60px 40px 80px',
        maxWidth: '600px',
        margin: '0 auto',
      }}>
        <h2 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '16px', color: '#1A1A1A' }}>
          Ready to find your next grant?
        </h2>
        <p style={{ fontSize: '16px', color: '#666', marginBottom: '32px' }}>
          Join organizations already using Smart Grant Finder to streamline their funding search.
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
