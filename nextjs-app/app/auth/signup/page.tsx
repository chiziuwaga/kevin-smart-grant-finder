'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { toast } from 'sonner';
import { hash } from 'bcryptjs';

export default function SignUpPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  // Step 1: Basic Info
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Step 2: Organization Info
  const [organizationType, setOrganizationType] = useState('');
  const [organizationName, setOrganizationName] = useState('');
  const [grantTypes, setGrantTypes] = useState<string[]>([]);
  const [geographicFocus, setGeographicFocus] = useState<string[]>([]);
  const [fundingRange, setFundingRange] = useState({ min: 5000, max: 100000 });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (step === 1) {
      // Validate and move to step 2
      if (!name || !email || !password) {
        toast.error('Please fill all fields');
        return;
      }
      if (password.length < 8) {
        toast.error('Password must be at least 8 characters');
        return;
      }
      setStep(2);
      return;
    }

    // Step 2: Create account
    setLoading(true);

    try {
      const hashedPassword = await hash(password, 12);

      const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          email,
          password: hashedPassword,
          organizationType,
          organizationName,
          grantTypes,
          geographicFocus,
          fundingRange,
        }),
      });

      if (response.ok) {
        toast.success('Account created! Pending admin approval.');
        router.push('/auth/signin?status=pending');
      } else {
        const data = await response.json();
        toast.error(data.error || 'Sign up failed');
      }
    } catch (error) {
      toast.error('Sign up failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleGrantType = (type: string) => {
    setGrantTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const toggleLocation = (location: string) => {
    setGeographicFocus((prev) =>
      prev.includes(location) ? prev.filter((l) => l !== location) : [...prev, location]
    );
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-primary/10 to-background p-4">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">Smart Grant Finder</h1>
          <p className="text-muted-foreground">
            {step === 1 ? 'Create your account' : 'Tell us about your organization'}
          </p>
        </div>

        <div className="bg-card border rounded-lg p-8 shadow-lg">
          {/* Progress Indicator */}
          <div className="flex items-center justify-center mb-8">
            <div className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  step >= 1 ? 'bg-primary text-primary-foreground' : 'bg-muted'
                }`}
              >
                1
              </div>
              <div className="w-16 h-1 bg-muted" />
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  step >= 2 ? 'bg-primary text-primary-foreground' : 'bg-muted'
                }`}
              >
                2
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {step === 1 && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Full Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="John Doe"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="you@example.com"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Password (min 8 characters)
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="••••••••"
                    required
                    minLength={8}
                  />
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Organization Type</label>
                  <select
                    value={organizationType}
                    onChange={(e) => setOrganizationType(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    required
                  >
                    <option value="">Select type...</option>
                    <option value="nonprofit">Nonprofit</option>
                    <option value="research">Research Institution</option>
                    <option value="business">Small Business</option>
                    <option value="education">Educational Institution</option>
                    <option value="individual">Individual</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Organization Name</label>
                  <input
                    type="text"
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Your Organization"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-3">Grant Types (select all that apply)</label>
                  <div className="grid grid-cols-2 gap-2">
                    {['Research', 'Education', 'Healthcare', 'Arts', 'Technology', 'Community'].map(
                      (type) => (
                        <button
                          key={type}
                          type="button"
                          onClick={() => toggleGrantType(type)}
                          className={`px-4 py-2 rounded-lg border ${
                            grantTypes.includes(type)
                              ? 'bg-primary text-primary-foreground border-primary'
                              : 'bg-background hover:bg-muted'
                          }`}
                        >
                          {type}
                        </button>
                      )
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-3">Geographic Focus</label>
                  <div className="grid grid-cols-2 gap-2">
                    {['National', 'NYC', 'California', 'Texas', 'Florida', 'International'].map(
                      (location) => (
                        <button
                          key={location}
                          type="button"
                          onClick={() => toggleLocation(location)}
                          className={`px-4 py-2 rounded-lg border ${
                            geographicFocus.includes(location)
                              ? 'bg-primary text-primary-foreground border-primary'
                              : 'bg-background hover:bg-muted'
                          }`}
                        >
                          {location}
                        </button>
                      )
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-3">
                    Funding Range: ${fundingRange.min.toLocaleString()} - $
                    {fundingRange.max.toLocaleString()}
                  </label>
                  <div className="space-y-2">
                    <input
                      type="range"
                      min="1000"
                      max="500000"
                      step="1000"
                      value={fundingRange.min}
                      onChange={(e) =>
                        setFundingRange({ ...fundingRange, min: parseInt(e.target.value) })
                      }
                      className="w-full"
                    />
                    <input
                      type="range"
                      min="1000"
                      max="500000"
                      step="1000"
                      value={fundingRange.max}
                      onChange={(e) =>
                        setFundingRange({ ...fundingRange, max: parseInt(e.target.value) })
                      }
                      className="w-full"
                    />
                  </div>
                </div>
              </>
            )}

            <div className="flex gap-4">
              {step === 2 && (
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="flex-1 px-4 py-3 border rounded-lg font-semibold hover:bg-muted"
                >
                  Back
                </button>
              )}
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-3 bg-primary text-primary-foreground rounded-lg font-semibold hover:bg-primary/90 disabled:opacity-50"
              >
                {loading ? 'Creating...' : step === 1 ? 'Next' : 'Create Account'}
              </button>
            </div>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link href="/auth/signin" className="text-primary hover:underline font-semibold">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
