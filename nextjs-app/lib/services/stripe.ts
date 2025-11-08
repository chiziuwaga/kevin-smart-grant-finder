/**
 * Stripe Payment Service
 * Handles credit purchases and top-ups
 */

import Stripe from 'stripe';
import { CreditManager } from './credit-manager';
import { CreditTier } from '@prisma/client';

if (!process.env.STRIPE_SECRET_KEY) {
  throw new Error('STRIPE_SECRET_KEY is not defined');
}

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
  apiVersion: '2024-11-20.acacia',
  typescript: true,
});

export interface CreateCheckoutSessionOptions {
  userId: string;
  userEmail: string;
  type: 'tier1' | 'tier2' | 'topup';
  amount?: number; // For top-ups
  successUrl: string;
  cancelUrl: string;
}

export class StripeService {
  /**
   * Create checkout session for credit purchase
   */
  static async createCheckoutSession(
    options: CreateCheckoutSessionOptions
  ): Promise<Stripe.Checkout.Session> {
    let lineItems: Stripe.Checkout.SessionCreateParams.LineItem[] = [];

    switch (options.type) {
      case 'tier1':
        lineItems = [
          {
            price_data: {
              currency: 'usd',
              product_data: {
                name: '10 Credits',
                description: 'Tier 1: $10 for 10 credits',
              },
              unit_amount: 1000, // $10.00
            },
            quantity: 1,
          },
        ];
        break;

      case 'tier2':
        lineItems = [
          {
            price_data: {
              currency: 'usd',
              product_data: {
                name: '22 Credits',
                description: 'Tier 2: $20 for 22 credits (11% bonus!)',
              },
              unit_amount: 2000, // $20.00
            },
            quantity: 1,
          },
        ];
        break;

      case 'topup':
        if (!options.amount || options.amount < 5) {
          throw new Error('Top-up amount must be at least $5');
        }
        lineItems = [
          {
            price_data: {
              currency: 'usd',
              product_data: {
                name: `${options.amount} Credits`,
                description: `Top-up: $${options.amount}`,
              },
              unit_amount: options.amount * 100, // Convert to cents
            },
            quantity: 1,
          },
        ];
        break;
    }

    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      line_items: lineItems,
      success_url: options.successUrl,
      cancel_url: options.cancelUrl,
      customer_email: options.userEmail,
      client_reference_id: options.userId,
      metadata: {
        userId: options.userId,
        type: options.type,
        amount: options.amount?.toString() || '',
      },
    });

    return session;
  }

  /**
   * Handle successful payment webhook
   */
  static async handleSuccessfulPayment(
    session: Stripe.Checkout.Session
  ): Promise<void> {
    const userId = session.client_reference_id || session.metadata?.userId;
    if (!userId) {
      throw new Error('User ID not found in session');
    }

    const type = session.metadata?.type;

    switch (type) {
      case 'tier1':
        await CreditManager.addCredits(
          userId,
          CreditTier.TIER_1,
          session.payment_intent as string
        );
        break;

      case 'tier2':
        await CreditManager.addCredits(
          userId,
          CreditTier.TIER_2,
          session.payment_intent as string
        );
        break;

      case 'topup':
        const amount = parseFloat(session.metadata?.amount || '0');
        if (amount >= 5) {
          await CreditManager.topUp(
            userId,
            amount,
            session.payment_intent as string
          );
        }
        break;

      default:
        console.error('Unknown payment type:', type);
    }
  }

  /**
   * Verify webhook signature
   */
  static constructEvent(
    payload: string | Buffer,
    signature: string
  ): Stripe.Event {
    const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
    if (!webhookSecret) {
      throw new Error('STRIPE_WEBHOOK_SECRET is not defined');
    }

    return stripe.webhooks.constructEvent(payload, signature, webhookSecret);
  }

  /**
   * Get payment details
   */
  static async getPaymentIntent(
    paymentIntentId: string
  ): Promise<Stripe.PaymentIntent> {
    return stripe.paymentIntents.retrieve(paymentIntentId);
  }

  /**
   * Issue refund
   */
  static async createRefund(
    paymentIntentId: string,
    amount?: number
  ): Promise<Stripe.Refund> {
    const refundParams: Stripe.RefundCreateParams = {
      payment_intent: paymentIntentId,
    };

    if (amount) {
      refundParams.amount = amount * 100; // Convert to cents
    }

    return stripe.refunds.create(refundParams);
  }
}

export default StripeService;
