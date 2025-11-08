import { auth } from '@/auth';
import { prisma } from '@/lib/prisma';
import { ResendService } from '@/lib/services/resend';
import { NextResponse } from 'next/server';

export async function POST(
  req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await auth();

    if (!session?.user?.id || session.user.role !== 'ADMIN') {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    const { action } = await req.json(); // 'approve' or 'reject'

    const user = await prisma.user.findUnique({
      where: { id: params.id },
    });

    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    if (action === 'approve') {
      // Update user status
      await prisma.user.update({
        where: { id: params.id },
        data: {
          whitelistStatus: 'APPROVED',
          whitelistedAt: new Date(),
          whitelistedBy: session.user.id,
        },
      });

      // Create credit record
      await prisma.credit.create({
        data: {
          userId: params.id,
          balance: 0, // Start at 0, user needs to pay
        },
      });

      // Send approval email with payment link
      const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
      const paymentLink = `${baseUrl}/auth/signin?payment=required`;

      await ResendService.sendWhitelistApprovalEmail(
        user.email,
        user.name || 'User',
        paymentLink
      );

      return NextResponse.json({ message: 'User approved and notified' });
    } else if (action === 'reject') {
      await prisma.user.update({
        where: { id: params.id },
        data: {
          whitelistStatus: 'REJECTED',
          whitelistedBy: session.user.id,
        },
      });

      return NextResponse.json({ message: 'User rejected' });
    } else {
      return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
    }
  } catch (error) {
    console.error('Whitelist error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
