import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/auth';
import { prisma } from '@/lib/prisma';

export async function POST(
  req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Verify this search belongs to the user
    const search = await prisma.grantSearch.findUnique({
      where: { id: params.id },
    });

    if (!search) {
      return NextResponse.json({ error: 'Search not found' }, { status: 404 });
    }

    if (search.userId !== session.user.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
    }

    // Can only cancel pending or running searches
    if (!['PENDING', 'RUNNING'].includes(search.status)) {
      return NextResponse.json(
        { error: 'Can only cancel pending or running searches' },
        { status: 400 }
      );
    }

    // Update status to failed with cancellation message
    await prisma.grantSearch.update({
      where: { id: params.id },
      data: {
        status: 'FAILED',
        error: 'Cancelled by user',
        completedAt: new Date(),
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to cancel search:', error);
    return NextResponse.json(
      { error: 'Failed to cancel search' },
      { status: 500 }
    );
  }
}
