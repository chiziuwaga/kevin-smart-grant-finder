import { describe, it, expect, beforeEach, vi } from 'vitest';
import { GET, POST } from '@/app/api/credits/route';
import { getServerSession } from 'next-auth';
import CreditManager from '@/lib/services/credit-manager';

vi.mock('next-auth');
vi.mock('@/lib/services/credit-manager');

describe('/api/credits', () => {
  const mockSession = {
    user: {
      id: 'user-123',
      email: 'test@example.com',
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('GET /api/credits', () => {
    it('should return 401 if not authenticated', async () => {
      vi.mocked(getServerSession).mockResolvedValue(null);

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(401);
      expect(data.error).toBe('Unauthorized');
    });

    it('should return credit balance for authenticated user', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockSession as any);
      vi.mocked(CreditManager.getBalance).mockResolvedValue({
        balance: 15.5,
        lifetimeSpent: 10,
        lifetimeAdded: 25.5,
        canUseService: true,
        isNegative: false,
      });

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toEqual({
        balance: 15.5,
        lifetimeSpent: 10,
        lifetimeAdded: 25.5,
        canUseService: true,
        isNegative: false,
      });
    });

    it('should handle negative balance', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockSession as any);
      vi.mocked(CreditManager.getBalance).mockResolvedValue({
        balance: -5,
        lifetimeSpent: 15,
        lifetimeAdded: 10,
        canUseService: false,
        isNegative: true,
      });

      const response = await GET();
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.balance).toBe(-5);
      expect(data.canUseService).toBe(false);
      expect(data.isNegative).toBe(true);
    });
  });

  describe('POST /api/credits (top-up)', () => {
    it('should return 401 if not authenticated', async () => {
      vi.mocked(getServerSession).mockResolvedValue(null);

      const request = new Request('http://localhost:3000/api/credits', {
        method: 'POST',
        body: JSON.stringify({ amount: 10 }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(401);
      expect(data.error).toBe('Unauthorized');
    });

    it('should reject amount below minimum', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockSession as any);

      const request = new Request('http://localhost:3000/api/credits', {
        method: 'POST',
        body: JSON.stringify({ amount: 3 }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain('minimum');
    });

    it('should successfully add credits', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockSession as any);
      vi.mocked(CreditManager.topUp).mockResolvedValue({
        id: 'txn-123',
        amount: 10,
        balanceBefore: 5,
        balanceAfter: 15,
        description: 'Top-up: $10',
        createdAt: new Date(),
      });

      const request = new Request('http://localhost:3000/api/credits', {
        method: 'POST',
        body: JSON.stringify({ amount: 10 }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.transaction.amount).toBe(10);
      expect(data.transaction.balanceAfter).toBe(15);
    });
  });
});
