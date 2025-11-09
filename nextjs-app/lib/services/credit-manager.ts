/**
 * Credit Management Service
 * Handles credit balance, transactions, and tier system
 *
 * TIER 1: $10 = 10 credits (1:1)
 * TIER 2: $20 = 22.2 credits (11% bonus)
 * Markup: 1.5x actual cost charged to user
 * Block at: $0 balance
 * Top-up min: $5
 */

import { prisma } from '@/lib/prisma';
import { CreditTier, TransactionType } from '@prisma/client';
import { Decimal } from '@prisma/client/runtime/library';

export interface CreditBalance {
  balance: number;
  lifetimeSpent: number;
  lifetimeAdded: number;
  canUseService: boolean;
  isNegative: boolean;
}

export interface CreditTransaction {
  id: string;
  amount: number;
  balanceBefore: number;
  balanceAfter: number;
  description: string;
  createdAt: Date;
}

export class CreditError extends Error {
  constructor(
    message: string,
    public code:
      | 'INSUFFICIENT_FUNDS'
      | 'NEGATIVE_BALANCE'
      | 'INVALID_AMOUNT'
      | 'USER_NOT_FOUND'
  ) {
    super(message);
    this.name = 'CreditError';
  }
}

export class CreditManager {
  // Credit tier configuration
  private static readonly TIERS = {
    TIER_1: {
      payment: 10, // $10
      credits: 10, // 10 credits
    },
    TIER_2: {
      payment: 20, // $20
      credits: 22, // 22 credits (11% bonus)
    },
  };

  private static readonly MARKUP_MULTIPLIER = 1.5; // Charge users 1.5x actual cost
  private static readonly MIN_TOP_UP = 5; // $5 minimum top-up

  /**
   * Get user's credit balance
   */
  static async getBalance(userId: string): Promise<CreditBalance> {
    const credit = await prisma.credit.findUnique({
      where: { userId },
    });

    if (!credit) {
      // Create credit record for new user
      const newCredit = await prisma.credit.create({
        data: {
          userId,
          balance: 0,
        },
      });

      return {
        balance: 0,
        lifetimeSpent: 0,
        lifetimeAdded: 0,
        canUseService: false,
        isNegative: false,
      };
    }

    const balance = Number(credit.balance);
    const isNegative = balance < 0;
    const canUseService = balance > 0;

    return {
      balance,
      lifetimeSpent: Number(credit.lifetimeSpent),
      lifetimeAdded: Number(credit.lifetimeAdded),
      canUseService,
      isNegative,
    };
  }

  /**
   * Add credits via payment (Tier 1 or Tier 2)
   */
  static async addCredits(
    userId: string,
    tier: CreditTier,
    stripePaymentId?: string
  ): Promise<CreditTransaction> {
    const tierConfig = this.TIERS[tier];
    const amount = tierConfig.credits;

    // Get or create credit record
    let credit = await prisma.credit.findUnique({ where: { userId } });

    if (!credit) {
      credit = await prisma.credit.create({
        data: { userId, balance: 0 },
      });
    }

    const balanceBefore = Number(credit.balance);
    const balanceAfter = balanceBefore + amount;

    // Create transaction
    const transaction = await prisma.creditTransaction.create({
      data: {
        userId,
        type: TransactionType.DEPOSIT,
        amount,
        balanceBefore,
        balanceAfter,
        tier,
        description: `Added ${amount} credits (${tier})`,
        metadata: {
          stripePaymentId,
          paymentAmount: tierConfig.payment,
        },
      },
    });

    // Update credit balance
    await prisma.credit.update({
      where: { userId },
      data: {
        balance: balanceAfter,
        lifetimeAdded: {
          increment: amount,
        },
        lastTopUpAt: new Date(),
        lastTopUpTier: tier,
      },
    });

    return {
      id: transaction.id,
      amount,
      balanceBefore,
      balanceAfter,
      description: transaction.description,
      createdAt: transaction.createdAt,
    };
  }

  /**
   * Add custom amount (for top-ups)
   */
  static async topUp(
    userId: string,
    paymentAmount: number,
    stripePaymentId?: string
  ): Promise<CreditTransaction> {
    if (paymentAmount < this.MIN_TOP_UP) {
      throw new CreditError(
        `Minimum top-up is $${this.MIN_TOP_UP}`,
        'INVALID_AMOUNT'
      );
    }

    // Convert payment to credits (1:1)
    const credits = paymentAmount;

    let credit = await prisma.credit.findUnique({ where: { userId } });

    if (!credit) {
      credit = await prisma.credit.create({
        data: { userId, balance: 0 },
      });
    }

    const balanceBefore = Number(credit.balance);
    const balanceAfter = balanceBefore + credits;

    const transaction = await prisma.creditTransaction.create({
      data: {
        userId,
        type: TransactionType.DEPOSIT,
        amount: credits,
        balanceBefore,
        balanceAfter,
        description: `Top-up: $${paymentAmount}`,
        metadata: {
          stripePaymentId,
          paymentAmount,
        },
      },
    });

    await prisma.credit.update({
      where: { userId },
      data: {
        balance: balanceAfter,
        lifetimeAdded: {
          increment: credits,
        },
        lastTopUpAt: new Date(),
      },
    });

    return {
      id: transaction.id,
      amount: credits,
      balanceBefore,
      balanceAfter,
      description: transaction.description,
      createdAt: transaction.createdAt,
    };
  }

  /**
   * Deduct credits for API usage
   * Applies 1.5x markup to actual cost
   */
  static async deductCredits(
    userId: string,
    actualCost: number,
    description: string,
    searchId?: string,
    metadata?: any
  ): Promise<CreditTransaction> {
    // Apply markup
    const chargedAmount = actualCost * this.MARKUP_MULTIPLIER;

    const credit = await prisma.credit.findUnique({ where: { userId } });

    if (!credit) {
      throw new CreditError('User credit record not found', 'USER_NOT_FOUND');
    }

    const balanceBefore = Number(credit.balance);

    // Allow negative balance (user will need to pay difference + min to resume)
    const balanceAfter = balanceBefore - chargedAmount;

    const transaction = await prisma.creditTransaction.create({
      data: {
        userId,
        searchId,
        type: TransactionType.DEDUCTION,
        amount: chargedAmount,
        balanceBefore,
        balanceAfter,
        description,
        metadata: {
          ...metadata,
          actualCost,
          markup: this.MARKUP_MULTIPLIER,
          chargedAmount,
        },
      },
    });

    await prisma.credit.update({
      where: { userId },
      data: {
        balance: balanceAfter,
        lifetimeSpent: {
          increment: chargedAmount,
        },
      },
    });

    return {
      id: transaction.id,
      amount: chargedAmount,
      balanceBefore,
      balanceAfter,
      description,
      createdAt: transaction.createdAt,
    };
  }

  /**
   * Check if user can use service
   * Blocked if balance <= 0
   */
  static async canUseService(userId: string): Promise<{
    allowed: boolean;
    balance: number;
    reason?: string;
  }> {
    const credit = await prisma.credit.findUnique({ where: { userId } });

    if (!credit) {
      return {
        allowed: false,
        balance: 0,
        reason: 'No credit account found. Please add credits to continue.',
      };
    }

    const balance = Number(credit.balance);

    if (balance <= 0) {
      const debt = Math.abs(balance);
      return {
        allowed: false,
        balance,
        reason:
          balance < 0
            ? `Your balance is -$${debt.toFixed(2)}. Please pay the difference plus minimum $${this.MIN_TOP_UP} to resume.`
            : `Your balance is $0. Please add credits to continue.`,
      };
    }

    return {
      allowed: true,
      balance,
    };
  }

  /**
   * Estimate cost for a grant search
   * Helps user understand cost before running
   */
  static estimateSearchCost(options: {
    useDeepSeek: boolean;
    useAgentQL: boolean;
    numberOfSources?: number;
  }): {
    actualCost: number;
    chargedCost: number;
    breakdown: Record<string, number>;
  } {
    let actualCost = 0;
    const breakdown: Record<string, number> = {};

    if (options.useDeepSeek) {
      // Estimate: ~2000 tokens per search at $0.14/M input + $0.28/M output
      const estimatedCost = (2000 / 1_000_000) * 0.28; // Conservative estimate
      actualCost += estimatedCost;
      breakdown.deepseek = estimatedCost;
    }

    if (options.useAgentQL) {
      // $0.01 per page scrape
      const sources = options.numberOfSources || 3;
      const estimatedCost = 0.01 * sources;
      actualCost += estimatedCost;
      breakdown.agentql = estimatedCost;
    }

    // OpenAI embeddings (small cost)
    const embeddingCost = 0.0001;
    actualCost += embeddingCost;
    breakdown.openai = embeddingCost;

    // Pinecone (negligible for single search)
    const pineconeCost = 0.00001;
    actualCost += pineconeCost;
    breakdown.pinecone = pineconeCost;

    const chargedCost = actualCost * this.MARKUP_MULTIPLIER;

    return {
      actualCost,
      chargedCost,
      breakdown,
    };
  }

  /**
   * Get transaction history for user
   */
  static async getTransactionHistory(
    userId: string,
    limit: number = 50
  ): Promise<CreditTransaction[]> {
    const transactions = await prisma.creditTransaction.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
      take: limit,
    });

    return transactions.map((t) => ({
      id: t.id,
      amount: Number(t.amount),
      balanceBefore: Number(t.balanceBefore),
      balanceAfter: Number(t.balanceAfter),
      description: t.description,
      createdAt: t.createdAt,
    }));
  }

  /**
   * Calculate amount needed to resume service (if negative balance)
   */
  static calculateResumePayment(currentBalance: number): number {
    if (currentBalance >= 0) return 0;

    const debt = Math.abs(currentBalance);
    return debt + this.MIN_TOP_UP;
  }

  /**
   * Issue refund
   */
  static async refund(
    userId: string,
    amount: number,
    reason: string
  ): Promise<CreditTransaction> {
    const credit = await prisma.credit.findUnique({ where: { userId } });

    if (!credit) {
      throw new CreditError('User credit record not found', 'USER_NOT_FOUND');
    }

    const balanceBefore = Number(credit.balance);
    const balanceAfter = balanceBefore + amount;

    const transaction = await prisma.creditTransaction.create({
      data: {
        userId,
        type: TransactionType.REFUND,
        amount,
        balanceBefore,
        balanceAfter,
        description: `Refund: ${reason}`,
      },
    });

    await prisma.credit.update({
      where: { userId },
      data: {
        balance: balanceAfter,
      },
    });

    return {
      id: transaction.id,
      amount,
      balanceBefore,
      balanceAfter,
      description: transaction.description,
      createdAt: transaction.createdAt,
    };
  }
}

export default CreditManager;
