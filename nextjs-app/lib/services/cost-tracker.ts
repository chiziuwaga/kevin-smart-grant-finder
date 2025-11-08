/**
 * API Cost Tracking Service
 * Logs all API usage and costs to database
 */

import { prisma } from '@/lib/prisma';
import { APIService } from '@prisma/client';

export interface APIUsageLogData {
  userId?: string;
  searchId?: string;
  service: keyof typeof APIService;
  operation: string;
  tokensUsed?: number;
  costUSD: number;
  duration?: number;
  success?: boolean;
  error?: string;
  requestData?: any;
  responseData?: any;
}

export class APIUsageLog {
  /**
   * Log API usage to database
   */
  static async log(data: APIUsageLogData): Promise<void> {
    try {
      await prisma.aPIUsageLog.create({
        data: {
          userId: data.userId,
          searchId: data.searchId,
          service: data.service,
          operation: data.operation,
          tokensUsed: data.tokensUsed,
          costUSD: data.costUSD,
          duration: data.duration,
          success: data.success ?? true,
          error: data.error,
          requestData: data.requestData,
          responseData: data.responseData,
        },
      });
    } catch (error) {
      // Don't throw - logging shouldn't break the main flow
      console.error('Failed to log API usage:', error);
    }
  }

  /**
   * Get total cost for a user
   */
  static async getUserCosts(
    userId: string,
    startDate?: Date,
    endDate?: Date
  ): Promise<{
    total: number;
    byService: Record<string, number>;
  }> {
    const where: any = { userId };

    if (startDate || endDate) {
      where.createdAt = {};
      if (startDate) where.createdAt.gte = startDate;
      if (endDate) where.createdAt.lte = endDate;
    }

    const logs = await prisma.aPIUsageLog.findMany({
      where,
      select: {
        service: true,
        costUSD: true,
      },
    });

    const byService: Record<string, number> = {};
    let total = 0;

    for (const log of logs) {
      const cost = Number(log.costUSD);
      total += cost;
      byService[log.service] = (byService[log.service] || 0) + cost;
    }

    return { total, byService };
  }

  /**
   * Get cost summary for a search
   */
  static async getSearchCosts(searchId: string): Promise<{
    deepseek: number;
    agentql: number;
    openai: number;
    pinecone: number;
    total: number;
  }> {
    const logs = await prisma.aPIUsageLog.findMany({
      where: { searchId },
      select: {
        service: true,
        costUSD: true,
      },
    });

    const costs = {
      deepseek: 0,
      agentql: 0,
      openai: 0,
      pinecone: 0,
      total: 0,
    };

    for (const log of logs) {
      const cost = Number(log.costUSD);
      costs.total += cost;

      switch (log.service) {
        case 'DEEPSEEK':
          costs.deepseek += cost;
          break;
        case 'AGENTQL':
          costs.agentql += cost;
          break;
        case 'OPENAI':
          costs.openai += cost;
          break;
        case 'PINECONE':
          costs.pinecone += cost;
          break;
      }
    }

    return costs;
  }

  /**
   * Get daily/monthly cost summary
   */
  static async getCostSummary(
    userId: string,
    period: 'day' | 'week' | 'month' = 'month'
  ): Promise<{
    current: number;
    previous: number;
    percentChange: number;
  }> {
    const now = new Date();
    let currentStart: Date;
    let previousStart: Date;
    let previousEnd: Date;

    switch (period) {
      case 'day':
        currentStart = new Date(now.setHours(0, 0, 0, 0));
        previousStart = new Date(currentStart);
        previousStart.setDate(previousStart.getDate() - 1);
        previousEnd = currentStart;
        break;

      case 'week':
        currentStart = new Date(now);
        currentStart.setDate(now.getDate() - 7);
        previousStart = new Date(currentStart);
        previousStart.setDate(previousStart.getDate() - 7);
        previousEnd = currentStart;
        break;

      case 'month':
      default:
        currentStart = new Date(now.getFullYear(), now.getMonth(), 1);
        previousStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        previousEnd = currentStart;
        break;
    }

    const [currentCosts, previousCosts] = await Promise.all([
      this.getUserCosts(userId, currentStart),
      this.getUserCosts(userId, previousStart, previousEnd),
    ]);

    const percentChange =
      previousCosts.total > 0
        ? ((currentCosts.total - previousCosts.total) / previousCosts.total) * 100
        : 0;

    return {
      current: currentCosts.total,
      previous: previousCosts.total,
      percentChange,
    };
  }
}

export default APIUsageLog;
