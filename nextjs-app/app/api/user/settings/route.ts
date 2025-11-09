import { auth } from '@/auth';
import { prisma } from '@/lib/prisma';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    let settings = await prisma.userSettings.findUnique({
      where: { userId: session.user.id },
    });

    if (!settings) {
      // Create default settings
      settings = await prisma.userSettings.create({
        data: { userId: session.user.id },
      });
    }

    return NextResponse.json({ settings });
  } catch (error) {
    console.error('Get settings error:', error);
    return NextResponse.json({ error: 'Failed to load settings' }, { status: 500 });
  }
}

export async function PUT(req: Request) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const data = await req.json();

    // Validate cron schedule (max 2 times per day)
    if (data.cronSchedule && data.cronSchedule.length > 2) {
      return NextResponse.json(
        { error: 'Maximum 2 automated searches per day' },
        { status: 400 }
      );
    }

    const settings = await prisma.userSettings.upsert({
      where: { userId: session.user.id },
      update: {
        cronEnabled: data.cronEnabled,
        cronSchedule: data.cronSchedule || [],
        emailNotifications: data.emailNotifications,
        notifyOnNewGrants: data.notifyOnNewGrants,
        notifyOnLowCredits: data.notifyOnLowCredits,
        lowCreditThreshold: data.lowCreditThreshold,
        minGrantScore: data.minGrantScore,
        autoSaveHighScore: data.autoSaveHighScore,
      },
      create: {
        userId: session.user.id,
        cronEnabled: data.cronEnabled,
        cronSchedule: data.cronSchedule || [],
        emailNotifications: data.emailNotifications,
        notifyOnNewGrants: data.notifyOnNewGrants,
        notifyOnLowCredits: data.notifyOnLowCredits,
        lowCreditThreshold: data.lowCreditThreshold,
        minGrantScore: data.minGrantScore,
        autoSaveHighScore: data.autoSaveHighScore,
      },
    });

    return NextResponse.json({ settings });
  } catch (error) {
    console.error('Update settings error:', error);
    return NextResponse.json({ error: 'Failed to save settings' }, { status: 500 });
  }
}
