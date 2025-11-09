'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import {
  Loader2,
  CheckCircle,
  FileText,
  Download,
  Sparkles,
  Info,
} from 'lucide-react';

interface Grant {
  id: string;
  title: string;
  organization: string;
  amount: { min: number; max: number };
  deadline: string;
  requirements: string[];
  applicationUrl: string;
}

interface ApplicationDraft {
  grantId: string;
  grantTitle: string;
  coverLetter: string;
  projectDescription: string;
  budgetJustification: string;
  impactStatement: string;
  generatedAt: string;
}

export default function GrantApplicationPage() {
  const searchParams = useSearchParams();
  const [grants, setGrants] = useState<Grant[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [drafts, setDrafts] = useState<ApplicationDraft[]>([]);
  const [currentStep, setCurrentStep] = useState<'select' | 'generate' | 'review'>('select');

  useEffect(() => {
    const grantIds = searchParams.get('ids')?.split(',') || [];
    if (grantIds.length > 0) {
      fetchGrants(grantIds);
    } else {
      setLoading(false);
    }
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

  const generateApplications = async () => {
    if (grants.length === 0) {
      toast.error('No grants selected');
      return;
    }

    setGenerating(true);
    setCurrentStep('generate');

    try {
      const res = await fetch('/api/grants/apply/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grantIds: grants.map((g) => g.id) }),
      });

      const data = await res.json();

      if (res.ok) {
        setDrafts(data.drafts);
        setCurrentStep('review');
        toast.success(`Generated ${data.drafts.length} application drafts!`);
      } else {
        toast.error(data.error || 'Failed to generate applications');
        setCurrentStep('select');
      }
    } catch (error) {
      toast.error('Failed to generate applications');
      setCurrentStep('select');
    } finally {
      setGenerating(false);
    }
  };

  const downloadDraft = (draft: ApplicationDraft) => {
    const content = `
GRANT APPLICATION DRAFT
Generated: ${new Date(draft.generatedAt).toLocaleString()}
Grant: ${draft.grantTitle}

=====================================
COVER LETTER
=====================================

${draft.coverLetter}

=====================================
PROJECT DESCRIPTION
=====================================

${draft.projectDescription}

=====================================
BUDGET JUSTIFICATION
=====================================

${draft.budgetJustification}

=====================================
IMPACT STATEMENT
=====================================

${draft.impactStatement}

=====================================
IMPORTANT NOTE
=====================================

This application draft was AI-generated. Please review, customize, and verify all information before submission.
Make sure to tailor the content to match your organization's specific circumstances and the grant's requirements.
`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `application-draft-${draft.grantTitle.replace(/[^a-z0-9]/gi, '-').toLowerCase()}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('Draft downloaded!');
  };

  const downloadAll = () => {
    drafts.forEach((draft) => {
      setTimeout(() => downloadDraft(draft), 100);
    });
    toast.success('Downloading all drafts...');
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
          <h2 className="text-2xl font-bold mb-2">No Grants Selected</h2>
          <p className="text-muted-foreground mb-4">
            Select grants from the search results to generate applications
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
      <div className="border-b bg-card">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">One-Click Applications</h1>
              <p className="text-sm text-muted-foreground mt-1">
                AI-powered application draft generation
              </p>
            </div>
            <a
              href="/grants"
              className="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90"
            >
              Back to Grants
            </a>
          </div>

          {/* Progress Steps */}
          <div className="mt-6 flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  currentStep === 'select'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-green-500 text-white'
                }`}
              >
                {currentStep !== 'select' ? <CheckCircle className="h-5 w-5" /> : '1'}
              </div>
              <span className="font-medium">Select Grants</span>
            </div>
            <div className="flex-1 h-0.5 bg-muted" />
            <div className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  currentStep === 'generate'
                    ? 'bg-primary text-primary-foreground'
                    : currentStep === 'review'
                    ? 'bg-green-500 text-white'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                {currentStep === 'review' ? <CheckCircle className="h-5 w-5" /> : '2'}
              </div>
              <span className="font-medium">Generate</span>
            </div>
            <div className="flex-1 h-0.5 bg-muted" />
            <div className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  currentStep === 'review'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                3
              </div>
              <span className="font-medium">Review & Download</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Step 1: Select Grants */}
        {currentStep === 'select' && (
          <div>
            <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-start gap-3">
              <Info className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium mb-1">How It Works</p>
                <p className="text-muted-foreground">
                  Our AI will analyze each grant's requirements and generate tailored application
                  drafts including cover letters, project descriptions, budget justifications, and
                  impact statements. Review and customize these drafts before submission.
                </p>
              </div>
            </div>

            <h2 className="text-xl font-bold mb-4">Selected Grants ({grants.length})</h2>

            <div className="space-y-3 mb-6">
              {grants.map((grant) => (
                <div key={grant.id} className="border rounded-lg p-4 bg-card">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold">{grant.title}</h3>
                      <p className="text-sm text-muted-foreground">{grant.organization}</p>
                      <div className="mt-2 flex items-center gap-4 text-sm">
                        <span>
                          <strong>Amount:</strong> ${grant.amount.min.toLocaleString()} - $
                          {grant.amount.max.toLocaleString()}
                        </span>
                        <span>
                          <strong>Deadline:</strong> {new Date(grant.deadline).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={generateApplications}
              disabled={generating}
              className="w-full px-6 py-4 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition flex items-center justify-center gap-2 font-medium disabled:opacity-50"
            >
              {generating ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Generating Applications...
                </>
              ) : (
                <>
                  <Sparkles className="h-5 w-5" />
                  Generate {grants.length} Application Draft{grants.length > 1 ? 's' : ''}
                </>
              )}
            </button>
          </div>
        )}

        {/* Step 2: Generating */}
        {currentStep === 'generate' && (
          <div className="text-center py-12">
            <Loader2 className="h-16 w-16 animate-spin text-primary mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Generating Application Drafts</h2>
            <p className="text-muted-foreground mb-4">
              Our AI is analyzing grant requirements and crafting tailored applications...
            </p>
            <div className="max-w-md mx-auto space-y-2 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Analyzing grant requirements</span>
              </div>
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Drafting cover letters</span>
              </div>
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Writing project descriptions</span>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Review Drafts */}
        {currentStep === 'review' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">Application Drafts ({drafts.length})</h2>
              <button
                onClick={downloadAll}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Download All
              </button>
            </div>

            <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-start gap-3">
              <Info className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium mb-1">Important</p>
                <p className="text-muted-foreground">
                  These are AI-generated drafts. Please review, customize, and verify all information
                  before submitting to grant organizations. Tailor each application to your specific
                  circumstances.
                </p>
              </div>
            </div>

            <div className="space-y-6">
              {drafts.map((draft) => (
                <div key={draft.grantId} className="border rounded-lg bg-card overflow-hidden">
                  <div className="p-4 border-b bg-muted/50">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-bold">{draft.grantTitle}</h3>
                        <p className="text-xs text-muted-foreground mt-1">
                          Generated {new Date(draft.generatedAt).toLocaleString()}
                        </p>
                      </div>
                      <button
                        onClick={() => downloadDraft(draft)}
                        className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 flex items-center gap-2"
                      >
                        <Download className="h-4 w-4" />
                        Download
                      </button>
                    </div>
                  </div>

                  <div className="p-4 space-y-4">
                    {/* Cover Letter */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <h4 className="font-semibold">Cover Letter</h4>
                      </div>
                      <div className="p-3 bg-muted/50 rounded text-sm whitespace-pre-wrap">
                        {draft.coverLetter}
                      </div>
                    </div>

                    {/* Project Description */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <h4 className="font-semibold">Project Description</h4>
                      </div>
                      <div className="p-3 bg-muted/50 rounded text-sm whitespace-pre-wrap">
                        {draft.projectDescription}
                      </div>
                    </div>

                    {/* Budget Justification */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <h4 className="font-semibold">Budget Justification</h4>
                      </div>
                      <div className="p-3 bg-muted/50 rounded text-sm whitespace-pre-wrap">
                        {draft.budgetJustification}
                      </div>
                    </div>

                    {/* Impact Statement */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <h4 className="font-semibold">Impact Statement</h4>
                      </div>
                      <div className="p-3 bg-muted/50 rounded text-sm whitespace-pre-wrap">
                        {draft.impactStatement}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
