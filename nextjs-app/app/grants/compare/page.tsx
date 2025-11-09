'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import {
  DollarSign,
  Calendar,
  MapPin,
  Target,
  FileText,
  ExternalLink,
  X,
  Download,
} from 'lucide-react';

interface Grant {
  id: string;
  title: string;
  organization: string;
  amount: { min: number; max: number };
  deadline: string;
  eligibility: string[];
  grantType: string[];
  geographicFocus: string[];
  description: string;
  applicationUrl: string;
  requirements: string[];
  score: number;
  matchReason: string;
}

export default function CompareGrantsPage() {
  const searchParams = useSearchParams();
  const [grants, setGrants] = useState<Grant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const grantIds = searchParams.get('ids')?.split(',') || [];
    if (grantIds.length === 0) {
      toast.error('No grants selected for comparison');
      return;
    }
    if (grantIds.length > 4) {
      toast.error('Maximum 4 grants can be compared at once');
      return;
    }
    fetchGrants(grantIds);
  }, [searchParams]);

  const fetchGrants = async (grantIds: string[]) => {
    try {
      const res = await fetch('/api/grants/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grantIds }),
      });

      const data = await res.json();
      if (res.ok) {
        setGrants(data.grants);
      } else {
        toast.error(data.error || 'Failed to load grants');
      }
    } catch (error) {
      toast.error('Failed to load grants');
    } finally {
      setLoading(false);
    }
  };

  const removeGrant = (grantId: string) => {
    const newGrants = grants.filter((g) => g.id !== grantId);
    const newIds = newGrants.map((g) => g.id).join(',');
    window.history.replaceState(
      {},
      '',
      `/grants/compare?ids=${newIds}`
    );
    setGrants(newGrants);
  };

  const exportComparison = async () => {
    try {
      const res = await fetch('/api/grants/compare/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grantIds: grants.map((g) => g.id) }),
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `grant-comparison-${Date.now()}.pdf`;
        a.click();
        toast.success('Comparison exported!');
      } else {
        toast.error('Failed to export comparison');
      }
    } catch (error) {
      toast.error('Failed to export comparison');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  if (grants.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">No Grants to Compare</h2>
          <p className="text-muted-foreground mb-4">
            Please select grants from the search results
          </p>
          <a
            href="/grants"
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
          >
            View All Grants
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Compare Grants</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Comparing {grants.length} grant{grants.length > 1 ? 's' : ''}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={exportComparison}
                className="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90 flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Export PDF
              </button>
              <a
                href="/grants"
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
              >
                Back to Grants
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="overflow-x-auto">
          <div className="grid gap-6" style={{ gridTemplateColumns: `250px repeat(${grants.length}, 1fr)` }}>
            {/* Header Row - Grant Names */}
            <div className="font-semibold text-muted-foreground">Grant</div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card relative">
                <button
                  onClick={() => removeGrant(grant.id)}
                  className="absolute top-2 right-2 p-1 hover:bg-destructive/10 rounded transition"
                  title="Remove from comparison"
                >
                  <X className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                </button>
                <h3 className="font-bold mb-1 pr-6">{grant.title}</h3>
                <p className="text-sm text-muted-foreground">{grant.organization}</p>
                <div className="mt-2 flex items-center gap-1">
                  <div className="text-xs font-medium px-2 py-1 bg-primary/10 text-primary rounded">
                    Score: {grant.score}
                  </div>
                </div>
              </div>
            ))}

            {/* Match Reason */}
            <div className="font-semibold text-muted-foreground flex items-center gap-2">
              <Target className="h-4 w-4" />
              Why It Matches
            </div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card">
                <p className="text-sm">{grant.matchReason}</p>
              </div>
            ))}

            {/* Funding Amount */}
            <div className="font-semibold text-muted-foreground flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Funding Amount
            </div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card">
                <div className="text-lg font-bold text-primary">
                  ${grant.amount.min.toLocaleString()} - $
                  {grant.amount.max.toLocaleString()}
                </div>
              </div>
            ))}

            {/* Deadline */}
            <div className="font-semibold text-muted-foreground flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Deadline
            </div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card">
                <div className="font-semibold">
                  {new Date(grant.deadline).toLocaleDateString()}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {Math.ceil(
                    (new Date(grant.deadline).getTime() - Date.now()) /
                      (1000 * 60 * 60 * 24)
                  )}{' '}
                  days remaining
                </div>
              </div>
            ))}

            {/* Grant Type */}
            <div className="font-semibold text-muted-foreground flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Grant Type
            </div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card">
                <div className="flex flex-wrap gap-1">
                  {grant.grantType.map((type, i) => (
                    <span
                      key={i}
                      className="px-2 py-1 bg-secondary text-secondary-foreground rounded text-xs"
                    >
                      {type}
                    </span>
                  ))}
                </div>
              </div>
            ))}

            {/* Geographic Focus */}
            <div className="font-semibold text-muted-foreground flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              Geographic Focus
            </div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card">
                <div className="flex flex-wrap gap-1">
                  {grant.geographicFocus.map((geo, i) => (
                    <span
                      key={i}
                      className="px-2 py-1 bg-secondary text-secondary-foreground rounded text-xs"
                    >
                      {geo}
                    </span>
                  ))}
                </div>
              </div>
            ))}

            {/* Eligibility */}
            <div className="font-semibold text-muted-foreground">
              Eligibility
            </div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card">
                <ul className="list-disc list-inside space-y-1 text-sm">
                  {grant.eligibility.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}

            {/* Requirements */}
            <div className="font-semibold text-muted-foreground">
              Requirements
            </div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card">
                <ul className="list-disc list-inside space-y-1 text-sm">
                  {grant.requirements.map((req, i) => (
                    <li key={i}>{req}</li>
                  ))}
                </ul>
              </div>
            ))}

            {/* Description */}
            <div className="font-semibold text-muted-foreground">
              Description
            </div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card">
                <p className="text-sm">{grant.description}</p>
              </div>
            ))}

            {/* Application Link */}
            <div className="font-semibold text-muted-foreground">
              Apply
            </div>
            {grants.map((grant) => (
              <div key={grant.id} className="border rounded-lg p-4 bg-card">
                <a
                  href={grant.applicationUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition text-sm"
                >
                  <ExternalLink className="h-4 w-4" />
                  Apply Now
                </a>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
