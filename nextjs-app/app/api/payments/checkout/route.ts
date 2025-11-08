import { auth } from '@/auth';
import { StripeService } from '@/lib/services/stripe';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const session = await auth();

    if (!session?.user?.id || !session?.user?.email) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { type, amount } = await req.json();

    const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';

    const checkoutSession = await StripeService.createCheckoutSession({
      userId: session.user.id,
      userEmail: session.user.email,
      type,
      amount,
      successUrl: `${baseUrl}/chat?payment=success`,
      cancelUrl: `${baseUrl}/chat?payment=cancelled`,
    });

    return NextResponse.json({ url: checkoutSession.url });
  } catch (error) {
    console.error('Checkout error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
