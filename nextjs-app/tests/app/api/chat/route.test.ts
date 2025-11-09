import { describe, it, expect, beforeEach, vi } from 'vitest';
import { POST } from '@/app/api/chat/route';
import { getServerSession } from 'next-auth';
import { prisma } from '@/lib/prisma';
import CreditManager from '@/lib/services/credit-manager';

vi.mock('next-auth');
vi.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findUnique: vi.fn(),
    },
    chatHistory: {
      findUnique: vi.fn(),
      findMany: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      count: vi.fn(),
    },
    message: {
      create: vi.fn(),
      findMany: vi.fn(),
    },
  },
}));
vi.mock('@/lib/services/credit-manager');
vi.mock('@/lib/ai/deepseek-provider', () => ({
  createDeepSeek: () => ({
    chat: () => ({}),
  }),
}));

describe('/api/chat', () => {
  const mockSession = {
    user: {
      id: 'user-123',
      email: 'test@example.com',
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('POST /api/chat', () => {
    it('should return 401 if not authenticated', async () => {
      vi.mocked(getServerSession).mockResolvedValue(null);

      const request = new Request('http://localhost:3000/api/chat', {
        method: 'POST',
        body: JSON.stringify({ messages: [] }),
      });

      const response = await POST(request);

      expect(response.status).toBe(401);
    });

    it('should return 403 if user not whitelisted', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockSession as any);
      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: 'user-123',
        whitelistStatus: 'PENDING',
      } as any);

      const request = new Request('http://localhost:3000/api/chat', {
        method: 'POST',
        body: JSON.stringify({ messages: [] }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(403);
      expect(data.error).toContain('pending approval');
    });

    it('should return 402 if insufficient credits', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockSession as any);
      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: 'user-123',
        whitelistStatus: 'APPROVED',
      } as any);
      vi.mocked(CreditManager.canUseService).mockResolvedValue({
        allowed: false,
        balance: 0,
        reason: 'Your balance is $0',
      });

      const request = new Request('http://localhost:3000/api/chat', {
        method: 'POST',
        body: JSON.stringify({ messages: [] }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(402);
      expect(data.error).toContain('balance is $0');
    });

    it('should enforce 50 message limit per thread', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockSession as any);
      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: 'user-123',
        whitelistStatus: 'APPROVED',
      } as any);
      vi.mocked(CreditManager.canUseService).mockResolvedValue({
        allowed: true,
        balance: 10,
      });
      vi.mocked(prisma.chatHistory.findUnique).mockResolvedValue({
        id: 'chat-123',
        messageCount: 50,
        isActive: false,
      } as any);

      const request = new Request('http://localhost:3000/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'Hello' }],
          chatId: 'chat-123',
        }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain('50 message limit');
    });

    it('should enforce 10 thread limit per user', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockSession as any);
      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: 'user-123',
        whitelistStatus: 'APPROVED',
      } as any);
      vi.mocked(CreditManager.canUseService).mockResolvedValue({
        allowed: true,
        balance: 10,
      });
      vi.mocked(prisma.chatHistory.count).mockResolvedValue(10);

      const request = new Request('http://localhost:3000/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'Hello' }],
        }),
      });

      const response = await POST(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain('10 active threads');
    });
  });
});
