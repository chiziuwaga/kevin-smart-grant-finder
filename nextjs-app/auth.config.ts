/**
 * Auth.js v5 Configuration
 * Email/password authentication with RBAC
 */

import type { NextAuthConfig } from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import { compare } from 'bcryptjs';
import { prisma } from '@/lib/prisma';

export const authConfig: NextAuthConfig = {
  pages: {
    signIn: '/auth/signin',
    signOut: '/auth/signout',
    error: '/auth/error',
  },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isOnDashboard = nextUrl.pathname.startsWith('/dashboard');
      const isOnChat = nextUrl.pathname.startsWith('/chat');
      const isOnAdmin = nextUrl.pathname.startsWith('/admin');
      const isOnAuth = nextUrl.pathname.startsWith('/auth');

      // Allow public pages
      if (nextUrl.pathname === '/') return true;
      if (isOnAuth) return true;

      // Require login for protected routes
      if ((isOnDashboard || isOnChat || isOnAdmin) && !isLoggedIn) {
        return false; // Redirect to sign in
      }

      // Admin-only routes
      if (isOnAdmin && auth?.user?.role !== 'ADMIN') {
        return Response.redirect(new URL('/chat', nextUrl));
      }

      return true;
    },
    async jwt({ token, user, trigger, session }) {
      if (user) {
        token.id = user.id;
        token.role = user.role;
        token.whitelistStatus = user.whitelistStatus;
      }

      // Handle session update
      if (trigger === 'update' && session) {
        token = { ...token, ...session };
      }

      return token;
    },
    async session({ session, token }) {
      if (token && session.user) {
        session.user.id = token.id as string;
        session.user.role = token.role as 'ADMIN' | 'USER';
        session.user.whitelistStatus = token.whitelistStatus as
          | 'PENDING'
          | 'APPROVED'
          | 'REJECTED'
          | 'BLOCKED';
      }

      return session;
    },
  },
  providers: [], // Providers added in auth.ts
};
