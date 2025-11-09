import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/auth';
import { prisma } from '@/lib/prisma';

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

    if (grantIds.length > 4) {
      return NextResponse.json(
        { error: 'Maximum 4 grants can be compared at once' },
        { status: 400 }
      );
    }

    // Fetch grants and verify they belong to user's searches
    const grants = await prisma.grant.findMany({
      where: {
        id: { in: grantIds },
        search: {
          userId: session.user.id,
        },
      },
      include: {
        search: {
          select: {
            id: true,
          },
        },
      },
    });

    if (grants.length !== grantIds.length) {
      return NextResponse.json(
        { error: 'Some grants not found or unauthorized' },
        { status: 404 }
      );
    }

    const formattedGrants = grants.map((grant) => ({
      id: grant.id,
      title: grant.title,
      organization: grant.organization,
      amount: grant.amount,
      deadline: grant.deadline.toISOString(),
      eligibility: grant.eligibility,
      grantType: grant.grantType,
      geographicFocus: grant.geographicFocus,
      description: grant.description,
      applicationUrl: grant.applicationUrl,
      requirements: grant.requirements,
      score: grant.score,
      matchReason: grant.matchReason,
    }));

    return NextResponse.json({ grants: formattedGrants });
  } catch (error) {
    console.error('Failed to fetch grants for comparison:', error);
    return NextResponse.json(
      { error: 'Failed to fetch grants' },
      { status: 500 }
    );
  }
}
