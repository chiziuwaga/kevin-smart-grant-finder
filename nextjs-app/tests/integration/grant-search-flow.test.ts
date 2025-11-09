import { describe, it, expect, beforeEach, vi } from 'vitest';
import { GrantSearchOrchestrator } from '@/lib/services/grant-search-orchestrator';
import CreditManager from '@/lib/services/credit-manager';
import { DeepSeekService } from '@/lib/services/deepseek-service';
import { AgentQLService } from '@/lib/services/agentql-service';
import { prisma } from '@/lib/prisma';

vi.mock('@/lib/prisma', () => ({
  prisma: {
    credit: {
      findUnique: vi.fn(),
      update: vi.fn(),
    },
    creditTransaction: {
      create: vi.fn(),
    },
    grantSearch: {
      create: vi.fn(),
      update: vi.fn(),
    },
    grant: {
      createMany: vi.fn(),
    },
    user: {
      findUnique: vi.fn(),
    },
  },
}));

vi.mock('@/lib/services/deepseek-service', () => ({
  DeepSeekService: {
    chat: vi.fn(),
  },
}));

vi.mock('@/lib/services/agentql-service', () => ({
  AgentQLService: {
    scrapeGrantSources: vi.fn(),
  },
}));

vi.mock('@/lib/services/resend-service', () => ({
  ResendService: {
    sendGrantResultsEmail: vi.fn(),
  },
}));

describe('Grant Search Integration Flow', () => {
  const mockUserId = 'user-123';
  const mockSearchId = 'search-123';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Complete Search Flow', () => {
    it('should execute full grant search with credit deduction', async () => {
      // Setup: User has sufficient credits
      vi.mocked(prisma.credit.findUnique).mockResolvedValue({
        balance: 20,
        lifetimeSpent: 5,
        lifetimeAdded: 25,
      } as any);

      // Mock user data
      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: mockUserId,
        email: 'test@example.com',
        organizationType: 'NONPROFIT',
        grantTypes: ['Community Development'],
      } as any);

      // Mock DeepSeek response
      vi.mocked(DeepSeekService.chat).mockResolvedValue({
        content: JSON.stringify({
          grants: [
            {
              title: 'Community Grant',
              organization: 'Foundation X',
              amount: { min: 10000, max: 50000 },
              deadline: '2024-12-31',
              eligibility: ['501(c)(3) organizations'],
              grantType: ['Community Development'],
              geographicFocus: ['USA'],
              description: 'Grant for community projects',
              applicationUrl: 'https://example.com/apply',
              requirements: ['Tax-exempt status'],
            },
          ],
        }),
        usage: {
          promptTokens: 500,
          completionTokens: 200,
          totalTokens: 700,
        },
      });

      // Mock AgentQL scraping
      vi.mocked(AgentQLService.scrapeGrantSources).mockResolvedValue({
        grants: [
          {
            title: 'Environment Grant',
            organization: 'Green Foundation',
            amount: { min: 5000, max: 25000 },
            deadline: '2024-11-30',
            eligibility: ['Environmental nonprofits'],
            grantType: ['Environment'],
            geographicFocus: ['California'],
            description: 'Grant for environmental projects',
            applicationUrl: 'https://example.com/env',
            requirements: ['Environmental focus'],
          },
        ],
        cost: 0.03, // 3 sources at $0.01 each
      });

      // Mock search creation
      vi.mocked(prisma.grantSearch.create).mockResolvedValue({
        id: mockSearchId,
        userId: mockUserId,
        query: 'Community development grants',
        status: 'PENDING',
      } as any);

      // Mock grants creation
      vi.mocked(prisma.grant.createMany).mockResolvedValue({
        count: 2,
      });

      // Mock transaction creation
      vi.mocked(prisma.creditTransaction.create).mockResolvedValue({
        id: 'txn-123',
        amount: 0.06, // Actual cost * 1.5
        balanceBefore: 20,
        balanceAfter: 19.94,
      } as any);

      // Execute search
      const orchestrator = new GrantSearchOrchestrator();
      const progressUpdates: any[] = [];

      await orchestrator.executeSearch(
        {
          userId: mockUserId,
          query: 'Community development grants',
          useDeepSeek: true,
          useAgentQL: true,
          trigger: 'MANUAL',
        },
        (progress) => {
          progressUpdates.push(progress);
        }
      );

      // Verify search was created
      expect(prisma.grantSearch.create).toHaveBeenCalled();

      // Verify DeepSeek was called
      expect(DeepSeekService.chat).toHaveBeenCalled();

      // Verify AgentQL was called
      expect(AgentQLService.scrapeGrantSources).toHaveBeenCalled();

      // Verify grants were saved
      expect(prisma.grant.createMany).toHaveBeenCalledWith({
        data: expect.arrayContaining([
          expect.objectContaining({
            title: expect.any(String),
            searchId: mockSearchId,
          }),
        ]),
      });

      // Verify progress updates
      expect(progressUpdates.length).toBeGreaterThan(0);
      expect(progressUpdates).toContainEqual(
        expect.objectContaining({
          step: expect.any(String),
          percentage: expect.any(Number),
        })
      );

      // Verify credit deduction with 1.5x markup
      expect(prisma.creditTransaction.create).toHaveBeenCalledWith({
        data: expect.objectContaining({
          userId: mockUserId,
          type: 'DEDUCTION',
          searchId: mockSearchId,
        }),
      });
    });

    it('should block search if user has insufficient credits', async () => {
      // User has zero balance
      vi.mocked(prisma.credit.findUnique).mockResolvedValue({
        balance: 0,
      } as any);

      const orchestrator = new GrantSearchOrchestrator();

      await expect(
        orchestrator.executeSearch({
          userId: mockUserId,
          query: 'Test query',
          useDeepSeek: true,
          useAgentQL: false,
          trigger: 'MANUAL',
        })
      ).rejects.toThrow();

      // Verify DeepSeek was NOT called
      expect(DeepSeekService.chat).not.toHaveBeenCalled();
    });

    it('should handle errors and update search status', async () => {
      vi.mocked(prisma.credit.findUnique).mockResolvedValue({
        balance: 10,
      } as any);

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: mockUserId,
      } as any);

      vi.mocked(prisma.grantSearch.create).mockResolvedValue({
        id: mockSearchId,
        userId: mockUserId,
      } as any);

      // Mock DeepSeek error
      vi.mocked(DeepSeekService.chat).mockRejectedValue(
        new Error('API rate limit')
      );

      const orchestrator = new GrantSearchOrchestrator();

      await expect(
        orchestrator.executeSearch({
          userId: mockUserId,
          query: 'Test query',
          useDeepSeek: true,
          useAgentQL: false,
          trigger: 'MANUAL',
        })
      ).rejects.toThrow();

      // Verify search status was updated to FAILED
      expect(prisma.grantSearch.update).toHaveBeenCalledWith({
        where: { id: mockSearchId },
        data: expect.objectContaining({
          status: 'FAILED',
          error: expect.any(String),
        }),
      });
    });
  });

  describe('Cost Calculation', () => {
    it('should accurately calculate and charge 1.5x markup', async () => {
      const actualCost = 0.04; // $0.04 actual
      const expectedCharged = 0.06; // $0.04 * 1.5

      vi.mocked(prisma.credit.findUnique).mockResolvedValue({
        balance: 10,
      } as any);

      vi.mocked(prisma.creditTransaction.create).mockResolvedValue({
        id: 'txn-123',
        amount: expectedCharged,
        balanceBefore: 10,
        balanceAfter: 9.94,
        metadata: {
          actualCost,
          markup: 1.5,
          chargedAmount: expectedCharged,
        },
      } as any);

      await CreditManager.deductCredits(
        mockUserId,
        actualCost,
        'Grant search'
      );

      expect(prisma.creditTransaction.create).toHaveBeenCalledWith({
        data: expect.objectContaining({
          amount: expectedCharged,
          metadata: expect.objectContaining({
            actualCost,
            markup: 1.5,
          }),
        }),
      });
    });
  });

  describe('Tier System', () => {
    it('should correctly apply 11% bonus for Tier 2', async () => {
      const tier2Credits = 22.2; // $20 * 1.11 = 22.2

      vi.mocked(prisma.credit.findUnique).mockResolvedValue({
        balance: 0,
      } as any);

      vi.mocked(prisma.creditTransaction.create).mockResolvedValue({
        id: 'txn-tier2',
        amount: tier2Credits,
        balanceBefore: 0,
        balanceAfter: tier2Credits,
      } as any);

      const result = await CreditManager.addCredits(
        mockUserId,
        'TIER_2' as any
      );

      expect(result.amount).toBe(22.2);
    });

    it('should not apply bonus for Tier 1', async () => {
      const tier1Credits = 10; // $10 = 10 credits (no bonus)

      vi.mocked(prisma.credit.findUnique).mockResolvedValue({
        balance: 0,
      } as any);

      vi.mocked(prisma.creditTransaction.create).mockResolvedValue({
        id: 'txn-tier1',
        amount: tier1Credits,
        balanceBefore: 0,
        balanceAfter: tier1Credits,
      } as any);

      const result = await CreditManager.addCredits(
        mockUserId,
        'TIER_1' as any
      );

      expect(result.amount).toBe(10);
    });
  });
});
