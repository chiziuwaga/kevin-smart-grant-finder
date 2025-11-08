'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';

export default function AdminPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/admin/users');
      const data = await res.json();
      setUsers(data.users || []);
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleWhitelist = async (userId: string, action: 'approve' | 'reject') => {
    try {
      const res = await fetch(`/api/admin/users/${userId}/whitelist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });

      if (res.ok) {
        toast.success(
          action === 'approve'
            ? 'User approved and payment email sent!'
            : 'User rejected'
        );
        fetchUsers();
      } else {
        toast.error('Action failed');
      }
    } catch (error) {
      toast.error('Action failed');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  const pendingUsers = users.filter((u) => u.whitelistStatus === 'PENDING');
  const approvedUsers = users.filter((u) => u.whitelistStatus === 'APPROVED');

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <a
            href="/chat"
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
          >
            Back to Chat
          </a>
        </div>

        {/* Pending Users */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">
            Pending Approval ({pendingUsers.length})
          </h2>
          {pendingUsers.length === 0 ? (
            <div className="p-8 border rounded-lg text-center text-muted-foreground">
              No pending users
            </div>
          ) : (
            <div className="space-y-4">
              {pendingUsers.map((user) => (
                <div
                  key={user.id}
                  className="p-4 border rounded-lg flex items-center justify-between"
                >
                  <div>
                    <div className="font-semibold">{user.email}</div>
                    <div className="text-sm text-muted-foreground">
                      {user.name || 'No name'} • Signed up{' '}
                      {new Date(user.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleWhitelist(user.id, 'approve')}
                      className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleWhitelist(user.id, 'reject')}
                      className="px-4 py-2 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Approved Users */}
        <div>
          <h2 className="text-2xl font-bold mb-4">
            Approved Users ({approvedUsers.length})
          </h2>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left p-3">Email</th>
                  <th className="text-left p-3">Name</th>
                  <th className="text-left p-3">Approved</th>
                  <th className="text-left p-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {approvedUsers.map((user) => (
                  <tr key={user.id} className="border-t">
                    <td className="p-3">{user.email}</td>
                    <td className="p-3">{user.name || '-'}</td>
                    <td className="p-3">
                      {user.whitelistedAt
                        ? new Date(user.whitelistedAt).toLocaleDateString()
                        : '-'}
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-1 bg-primary/10 text-primary rounded text-sm">
                        Active
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
