import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/auth';
import { prisma } from '@/lib/prisma';
import { DeepSeekService } from '@/lib/services/deepseek-service';
import CreditManager from '@/lib/services/credit-manager';

export async function POST(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { grantIds } = await req.json();

    if (!Array.isArray(grantIds) || grantIds.length === 0) {
      return NextResponse.json(
        { error: 'Invalid grant IDs' },
        { status: 400 }
      );
    }

    // Check credit balance
    const canUse = await CreditManager.canUseService(session.user.id);
    if (!canUse.allowed) {
      return NextResponse.json(
        { error: canUse.reason || 'Insufficient credits' },
        { status: 402 }
      );
    }

    // Fetch user profile and grants
    const user = await prisma.user.findUnique({
      where: { id: session.user.id },
      select: {
        organizationType: true,
        organizationName: true,
        grantTypes: true,
        geographicFocus: true,
        fundingRange: true,
      },
    });

    const grants = await prisma.grant.findMany({
      where: {
        id: { in: grantIds },
        search: {
          userId: session.user.id,
        },
      },
    });

    if (grants.length === 0) {
      return NextResponse.json({ error: 'No grants found' }, { status: 404 });
    }

    // Generate application drafts for each grant
    const drafts = [];
    let totalCost = 0;

    for (const grant of grants) {
      const prompt = `You are an expert grant writer. Generate a professional grant application draft with the following sections:

GRANT INFORMATION:
- Title: ${grant.title}
- Organization: ${grant.organization}
- Funding Amount: $${(grant.amount as any).min.toLocaleString()} - $${(grant.amount as any).max.toLocaleString()}
- Grant Type: ${(grant.grantType as string[]).join(', ')}
- Eligibility: ${(grant.eligibility as string[]).join(', ')}
- Requirements: ${(grant.requirements as string[]).join(', ')}

APPLICANT ORGANIZATION:
- Type: ${user?.organizationType || 'Not specified'}
- Name: ${user?.organizationName || 'Not specified'}
- Focus Areas: ${(user?.grantTypes as string[] || []).join(', ')}
- Geographic Focus: ${(user?.geographicFocus as string[] || []).join(', ')}

Please provide:

1. COVER LETTER (200-300 words):
Write a compelling cover letter introducing the organization and expressing interest in the grant.

2. PROJECT DESCRIPTION (300-400 words):
Describe a project that would benefit from this grant, aligned with both the grant's focus and the organization's mission.

3. BUDGET JUSTIFICATION (150-200 words):
Explain how the grant funds would be allocated and why each expense is necessary.

4. IMPACT STATEMENT (150-200 words):
Describe the expected outcomes and long-term impact of the proposed project.

Format each section clearly with headings.`;

      try {
        const response = await DeepSeekService.chat([
          {
            role: 'user',
            content: prompt,
          },
        ]);

        // Track cost (estimate ~2000 tokens)
        const estimatedCost = (2000 / 1_000_000) * 0.28;
        totalCost += estimatedCost;

        // Parse sections from response
        const content = response.content;

        // Simple section extraction
        const coverLetterMatch = content.match(
          /COVER LETTER[:\s]*([\s\S]*?)(?=\d+\.|PROJECT DESCRIPTION|$)/i
        );
        const projectMatch = content.match(
          /PROJECT DESCRIPTION[:\s]*([\s\S]*?)(?=\d+\.|BUDGET JUSTIFICATION|$)/i
        );
        const budgetMatch = content.match(
          /BUDGET JUSTIFICATION[:\s]*([\s\S]*?)(?=\d+\.|IMPACT STATEMENT|$)/i
        );
        const impactMatch = content.match(/IMPACT STATEMENT[:\s]*([\s\S]*?)$/i);

        drafts.push({
          grantId: grant.id,
          grantTitle: grant.title,
          coverLetter: coverLetterMatch?.[1]?.trim() || content.substring(0, 500),
          projectDescription: projectMatch?.[1]?.trim() || '',
          budgetJustification: budgetMatch?.[1]?.trim() || '',
          impactStatement: impactMatch?.[1]?.trim() || '',
          generatedAt: new Date().toISOString(),
        });
      } catch (error) {
        console.error(`Failed to generate draft for grant ${grant.id}:`, error);
        // Continue with other grants
      }
    }

    // Deduct credits for AI usage
    if (totalCost > 0) {
      await CreditManager.deductCredits(
        session.user.id,
        totalCost,
        `Generated ${drafts.length} application draft(s)`,
        undefined,
        {
          feature: 'application-generation',
          grantCount: drafts.length,
        }
      );
    }

    return NextResponse.json({ drafts });
  } catch (error) {
    console.error('Failed to generate application drafts:', error);
    return NextResponse.json(
      { error: 'Failed to generate application drafts' },
      { status: 500 }
    );
  }
}
