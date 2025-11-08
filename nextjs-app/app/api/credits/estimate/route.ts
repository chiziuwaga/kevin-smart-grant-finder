import { auth } from '@/auth';
import { CreditManager } from '@/lib/services/credit-manager';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { sources } = await req.json();

    const estimate = CreditManager.estimateSearchCost({
      useDeepSeek: true,
      useAgentQL: true,
      numberOfSources: sources || 3,
    });

    return NextResponse.json(estimate);
  } catch (error) {
    console.error('Estimate cost error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
