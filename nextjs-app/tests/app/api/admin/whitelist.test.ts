import { describe, it, expect, beforeEach, vi } from 'vitest';
import { POST } from '@/app/api/admin/users/[id]/whitelist/route';
import { getServerSession } from 'next-auth';
import { prisma } from '@/lib/prisma';
import { ResendService } from '@/lib/services/resend-service';

vi.mock('next-auth');
vi.mock('@/lib/prisma', () => ({
  prisma: {
    user: {
      findUnique: vi.fn(),
      update: vi.fn(),
    },
  },
}));
vi.mock('@/lib/services/resend-service', () => ({
  ResendService: {
    sendWhitelistApprovalEmail: vi.fn(),
  },
}));

describe('/api/admin/users/[id]/whitelist', () => {
  const mockAdminSession = {
    user: {
      id: 'admin-123',
      email: 'admin@example.com',
      role: 'ADMIN',
    },
  };

  const mockUserSession = {
    user: {
      id: 'user-123',
      email: 'user@example.com',
      role: 'USER',
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('POST /api/admin/users/[id]/whitelist', () => {
    it('should return 401 if not authenticated', async () => {
      vi.mocked(getServerSession).mockResolvedValue(null);

      const request = new Request('http://localhost:3000/api/admin/users/user-456/whitelist', {
        method: 'POST',
        body: JSON.stringify({ action: 'approve' }),
      });

      const response = await POST(request, { params: { id: 'user-456' } });

      expect(response.status).toBe(401);
    });

    it('should return 403 if user is not admin', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockUserSession as any);
      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: 'user-123',
        role: 'USER',
      } as any);

      const request = new Request('http://localhost:3000/api/admin/users/user-456/whitelist', {
        method: 'POST',
        body: JSON.stringify({ action: 'approve' }),
      });

      const response = await POST(request, { params: { id: 'user-456' } });
      const data = await response.json();

      expect(response.status).toBe(403);
      expect(data.error).toContain('Admin access required');
    });

    it('should approve user and send payment email', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockAdminSession as any);
      vi.mocked(prisma.user.findUnique)
        .mockResolvedValueOnce({
          id: 'admin-123',
          role: 'ADMIN',
        } as any)
        .mockResolvedValueOnce({
          id: 'user-456',
          email: 'newuser@example.com',
          name: 'New User',
          whitelistStatus: 'PENDING',
        } as any);

      vi.mocked(prisma.user.update).mockResolvedValue({
        id: 'user-456',
        whitelistStatus: 'APPROVED',
      } as any);

      vi.mocked(ResendService.sendWhitelistApprovalEmail).mockResolvedValue(
        undefined
      );

      const request = new Request('http://localhost:3000/api/admin/users/user-456/whitelist', {
        method: 'POST',
        body: JSON.stringify({ action: 'approve' }),
      });

      const response = await POST(request, { params: { id: 'user-456' } });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);

      expect(prisma.user.update).toHaveBeenCalledWith({
        where: { id: 'user-456' },
        data: {
          whitelistStatus: 'APPROVED',
          whitelistedAt: expect.any(Date),
        },
      });

      expect(ResendService.sendWhitelistApprovalEmail).toHaveBeenCalledWith(
        'newuser@example.com',
        'New User',
        expect.stringContaining('stripe')
      );
    });

    it('should reject user without sending email', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockAdminSession as any);
      vi.mocked(prisma.user.findUnique)
        .mockResolvedValueOnce({
          id: 'admin-123',
          role: 'ADMIN',
        } as any)
        .mockResolvedValueOnce({
          id: 'user-456',
          email: 'newuser@example.com',
          whitelistStatus: 'PENDING',
        } as any);

      vi.mocked(prisma.user.update).mockResolvedValue({
        id: 'user-456',
        whitelistStatus: 'REJECTED',
      } as any);

      const request = new Request('http://localhost:3000/api/admin/users/user-456/whitelist', {
        method: 'POST',
        body: JSON.stringify({ action: 'reject' }),
      });

      const response = await POST(request, { params: { id: 'user-456' } });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);

      expect(prisma.user.update).toHaveBeenCalledWith({
        where: { id: 'user-456' },
        data: {
          whitelistStatus: 'REJECTED',
        },
      });

      expect(ResendService.sendWhitelistApprovalEmail).not.toHaveBeenCalled();
    });

    it('should return 404 if user not found', async () => {
      vi.mocked(getServerSession).mockResolvedValue(mockAdminSession as any);
      vi.mocked(prisma.user.findUnique)
        .mockResolvedValueOnce({
          id: 'admin-123',
          role: 'ADMIN',
        } as any)
        .mockResolvedValueOnce(null);

      const request = new Request('http://localhost:3000/api/admin/users/nonexistent/whitelist', {
        method: 'POST',
        body: JSON.stringify({ action: 'approve' }),
      });

      const response = await POST(request, { params: { id: 'nonexistent' } });

      expect(response.status).toBe(404);
    });
  });
});
