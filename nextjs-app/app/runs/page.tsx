'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Clock, CheckCircle, XCircle, Loader2, DollarSign, Search } from 'lucide-react';

interface SearchRun {
  id: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  trigger: 'MANUAL' | 'CRON';
  query: string;
  progress: {
    step: string;
    percentage: number;
    currentSource?: string;
  };
  cost: {
    estimated: number;
    actual: number;
    charged: number;
  };
  results: {
    totalGrants: number;
    highScore: number;
  };
  createdAt: string;
  completedAt?: string;
  error?: string;
}

export default function ActiveRunsPage() {
  const [runs, setRuns] = useState<SearchRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  useEffect(() => {
    fetchRuns();
    // Poll for updates every 3 seconds
    const interval = setInterval(fetchRuns, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchRuns = async () => {
    try {
      const res = await fetch('/api/search/runs');
      const data = await res.json();
      setRuns(data.runs || []);
    } catch (error) {
      console.error('Failed to fetch runs:', error);
    } finally {
      setLoading(false);
    }
  };

  const cancelRun = async (runId: string) => {
    try {
      const res = await fetch(`/api/search/runs/${runId}/cancel`, {
        method: 'POST',
      });

      if (res.ok) {
        toast.success('Search cancelled');
        fetchRuns();
      } else {
        toast.error('Failed to cancel search');
      }
    } catch (error) {
      toast.error('Failed to cancel search');
    }
  };

  const filteredRuns = runs.filter((run) => {
    if (filter === 'active') return ['PENDING', 'RUNNING'].includes(run.status);
    if (filter === 'completed') return ['COMPLETED', 'FAILED'].includes(run.status);
    return true;
  });

  const activeRuns = runs.filter((r) => ['PENDING', 'RUNNING'].includes(r.status));
  const completedRuns = runs.filter((r) => r.status === 'COMPLETED');

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Grant Search Runs</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Track your grant searches in real-time
              </p>
            </div>
            <a
              href="/chat"
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition"
            >
              Back to Chat
            </a>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
            <div className="p-4 bg-background rounded-lg border">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Loader2 className="h-4 w-4" />
                <span className="text-sm">Active Searches</span>
              </div>
              <div className="text-2xl font-bold">{activeRuns.length}</div>
            </div>
            <div className="p-4 bg-background rounded-lg border">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <CheckCircle className="h-4 w-4" />
                <span className="text-sm">Completed Today</span>
              </div>
              <div className="text-2xl font-bold">{completedRuns.length}</div>
            </div>
            <div className="p-4 bg-background rounded-lg border">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <DollarSign className="h-4 w-4" />
                <span className="text-sm">Total Spent Today</span>
              </div>
              <div className="text-2xl font-bold">
                ${completedRuns.reduce((sum, r) => sum + r.cost.charged, 0).toFixed(2)}
              </div>
            </div>
          </div>

          {/* Filter */}
          <div className="flex gap-2 mt-6">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-lg transition ${
                filter === 'all'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground hover:bg-muted'
              }`}
            >
              All ({runs.length})
            </button>
            <button
              onClick={() => setFilter('active')}
              className={`px-4 py-2 rounded-lg transition ${
                filter === 'active'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground hover:bg-muted'
              }`}
            >
              Active ({activeRuns.length})
            </button>
            <button
              onClick={() => setFilter('completed')}
              className={`px-4 py-2 rounded-lg transition ${
                filter === 'completed'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground hover:bg-muted'
              }`}
            >
              Completed ({completedRuns.length})
            </button>
          </div>
        </div>
      </div>

      {/* Runs List */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {filteredRuns.length === 0 ? (
          <div className="text-center py-12 border rounded-lg bg-card">
            <Search className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="text-lg font-semibold mb-1">No searches found</h3>
            <p className="text-muted-foreground">
              Start a new grant search in the chat to see it here
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredRuns.map((run) => (
              <div
                key={run.id}
                className="border rounded-lg bg-card overflow-hidden hover:border-primary/50 transition"
              >
                {/* Run Header */}
                <div className="p-4 flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      {run.status === 'RUNNING' && (
                        <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                      )}
                      {run.status === 'COMPLETED' && (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      )}
                      {run.status === 'FAILED' && (
                        <XCircle className="h-4 w-4 text-red-500" />
                      )}
                      {run.status === 'PENDING' && (
                        <Clock className="h-4 w-4 text-yellow-500" />
                      )}
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          run.status === 'RUNNING'
                            ? 'bg-blue-500/10 text-blue-500'
                            : run.status === 'COMPLETED'
                            ? 'bg-green-500/10 text-green-500'
                            : run.status === 'FAILED'
                            ? 'bg-red-500/10 text-red-500'
                            : 'bg-yellow-500/10 text-yellow-500'
                        }`}
                      >
                        {run.status}
                      </span>
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-muted">
                        {run.trigger}
                      </span>
                    </div>
                    <h3 className="font-semibold text-lg mb-1">{run.query}</h3>
                    <p className="text-sm text-muted-foreground">
                      Started {new Date(run.createdAt).toLocaleString()}
                      {run.completedAt &&
                        ` • Completed ${new Date(run.completedAt).toLocaleString()}`}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    {run.status === 'COMPLETED' && (
                      <a
                        href={`/grants?searchId=${run.id}`}
                        className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 transition"
                      >
                        View Results
                      </a>
                    )}
                    {['PENDING', 'RUNNING'].includes(run.status) && (
                      <button
                        onClick={() => cancelRun(run.id)}
                        className="px-3 py-1.5 text-sm bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 transition"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress Bar (for running searches) */}
                {run.status === 'RUNNING' && (
                  <div className="px-4 pb-4">
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="font-medium">{run.progress.step}</span>
                      <span className="text-muted-foreground">
                        {run.progress.percentage}%
                      </span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${run.progress.percentage}%` }}
                      />
                    </div>
                    {run.progress.currentSource && (
                      <p className="text-xs text-muted-foreground mt-2">
                        Scraping: {run.progress.currentSource}
                      </p>
                    )}
                  </div>
                )}

                {/* Error Message */}
                {run.status === 'FAILED' && run.error && (
                  <div className="px-4 pb-4">
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded text-sm text-red-500">
                      {run.error}
                    </div>
                  </div>
                )}

                {/* Results & Cost */}
                <div className="px-4 pb-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">
                      Grants Found
                    </div>
                    <div className="font-semibold">
                      {run.status === 'COMPLETED' ? run.results.totalGrants : '-'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">
                      Highest Score
                    </div>
                    <div className="font-semibold">
                      {run.status === 'COMPLETED' ? run.results.highScore : '-'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">
                      Estimated Cost
                    </div>
                    <div className="font-semibold">
                      ${run.cost.estimated.toFixed(4)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">
                      Charged
                    </div>
                    <div className="font-semibold text-primary">
                      ${run.cost.charged.toFixed(4)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
