import { prisma } from '@/lib/prisma';
import { GrantSearchOrchestrator } from '@/lib/services/grant-search-orchestrator';
import { NextResponse } from 'next/server';

export async function GET(req: Request) {
  try {
    // Verify cron secret
    const authHeader = req.headers.get('authorization');
    const cronSecret = process.env.CRON_SECRET;

    if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const currentHour = new Date().getHours();
    const currentTime = `${currentHour.toString().padStart(2, '0')}:00`;

    // Find users with cron enabled and matching schedule
    const users = await prisma.user.findMany({
      where: {
        whitelistStatus: 'APPROVED',
        settings: {
          cronEnabled: true,
          cronSchedule: {
            has: currentTime,
          },
        },
      },
      include: {
        settings: true,
        credits: true,
      },
    });

    const results = [];
    const orchestrator = new GrantSearchOrchestrator();

    for (const user of users) {
      // Check if user has sufficient credits
      if (!user.credits || Number(user.credits.balance) <= 0) {
        console.log(`Skipping user ${user.id} - insufficient credits`);
        continue;
      }

      // Check daily search limit (max 2/day)
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const searchesToday = await prisma.grantSearch.count({
        where: {
          userId: user.id,
          trigger: 'CRON',
          createdAt: { gte: today },
        },
      });

      if (searchesToday >= 2) {
        console.log(`Skipping user ${user.id} - daily limit reached`);
        continue;
      }

      try {
        // Build search query from user profile
        const query = `Find grants for ${user.organizationType || 'organization'} ${
          user.grantTypes?.join(', ') || ''
        } in ${user.geographicFocus?.join(', ') || 'any location'}`;

        const searchId = await orchestrator.executeSearch({
          userId: user.id,
          query,
          trigger: 'CRON',
        });

        results.push({ userId: user.id, searchId, status: 'success' });
      } catch (error) {
        console.error(`Failed to execute search for user ${user.id}:`, error);
        results.push({
          userId: user.id,
          status: 'failed',
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }

    return NextResponse.json({
      message: `Processed ${results.length} users`,
      results,
    });
  } catch (error) {
    console.error('Cron job error:', error);
    return NextResponse.json({ error: 'Cron job failed' }, { status: 500 });
  }
}
