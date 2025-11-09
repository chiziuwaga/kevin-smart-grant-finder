import { prisma } from '@/lib/prisma';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const data = await req.json();

    // Check if user already exists
    const existing = await prisma.user.findUnique({
      where: { email: data.email },
    });

    if (existing) {
      return NextResponse.json({ error: 'Email already registered' }, { status: 400 });
    }

    // Create user with PENDING status
    const user = await prisma.user.create({
      data: {
        email: data.email,
        name: data.name,
        password: data.password,
        organizationType: data.organizationType,
        organizationName: data.organizationName,
        grantTypes: data.grantTypes || [],
        geographicFocus: data.geographicFocus || [],
        fundingRange: data.fundingRange,
        whitelistStatus: 'PENDING',
        role: 'USER',
      },
    });

    // Create default settings
    await prisma.userSettings.create({
      data: {
        userId: user.id,
      },
    });

    return NextResponse.json({
      message: 'Account created successfully. Pending admin approval.',
      userId: user.id,
    });
  } catch (error) {
    console.error('Signup error:', error);
    return NextResponse.json({ error: 'Sign up failed' }, { status: 500 });
  }
}
