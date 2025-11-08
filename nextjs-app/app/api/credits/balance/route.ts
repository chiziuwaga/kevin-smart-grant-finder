import { auth } from '@/auth';
import { CreditManager } from '@/lib/services/credit-manager';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const balance = await CreditManager.getBalance(session.user.id);

    return NextResponse.json(balance);
  } catch (error) {
    console.error('Get balance error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
