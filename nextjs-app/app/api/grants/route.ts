import { auth } from '@/auth';
import { prisma } from '@/lib/prisma';
import { NextResponse } from 'next/server';

export async function GET(req: Request) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(req.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '20');
    const minScore = parseFloat(searchParams.get('minScore') || '0');
    const saved = searchParams.get('saved') === 'true';

    const where: any = {
      userId: session.user.id,
      status: 'ACTIVE',
    };

    if (minScore > 0) {
      where.finalScore = { gte: minScore };
    }

    if (saved) {
      where.isSaved = true;
    }

    const [grants, total] = await Promise.all([
      prisma.grant.findMany({
        where,
        orderBy: { finalScore: 'desc' },
        skip: (page - 1) * limit,
        take: limit,
        select: {
          id: true,
          title: true,
          description: true,
          fundingAmount: true,
          deadline: true,
          sourceUrl: true,
          sourceName: true,
          category: true,
          finalScore: true,
          isSaved: true,
          createdAt: true,
        },
      }),
      prisma.grant.count({ where }),
    ]);

    return NextResponse.json({
      grants,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      },
    });
  } catch (error) {
    console.error('Get grants error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
