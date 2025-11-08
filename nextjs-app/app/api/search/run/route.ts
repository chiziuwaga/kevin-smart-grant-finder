import { auth } from '@/auth';
import { GrantSearchOrchestrator } from '@/lib/services/grant-search-orchestrator';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { query, filters } = await req.json();

    const orchestrator = new GrantSearchOrchestrator();

    // Execute search (async - don't wait)
    const searchId = await orchestrator.executeSearch({
      userId: session.user.id,
      query,
      trigger: 'MANUAL',
      filters,
    });

    return NextResponse.json({ searchId, status: 'running' });
  } catch (error) {
    console.error('Search error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Search failed' },
      { status: 500 }
    );
  }
}
