import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/auth';
import { prisma } from '@/lib/prisma';

export async function GET() {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get all searches for this user (last 30 days)
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const searches = await prisma.grantSearch.findMany({
      where: {
        userId: session.user.id,
        createdAt: {
          gte: thirtyDaysAgo,
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
      include: {
        _count: {
          select: {
            grants: true,
          },
        },
        grants: {
          select: {
            score: true,
          },
          orderBy: {
            score: 'desc',
          },
          take: 1,
        },
      },
    });

    const runs = searches.map((search) => {
      const progress = (search.metadata as any)?.progress || {
        step: 'Initializing',
        percentage: 0,
      };

      const cost = {
        estimated: Number((search.metadata as any)?.estimatedCost || 0),
        actual: Number((search.metadata as any)?.actualCost || 0),
        charged: Number((search.metadata as any)?.chargedCost || 0),
      };

      const results = {
        totalGrants: search._count.grants,
        highScore: search.grants[0]?.score || 0,
      };

      return {
        id: search.id,
        status: search.status,
        trigger: search.trigger,
        query: search.query,
        progress,
        cost,
        results,
        createdAt: search.createdAt.toISOString(),
        completedAt: search.completedAt?.toISOString(),
        error: search.error,
      };
    });

    return NextResponse.json({ runs });
  } catch (error) {
    console.error('Failed to fetch runs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch runs' },
      { status: 500 }
    );
  }
}
