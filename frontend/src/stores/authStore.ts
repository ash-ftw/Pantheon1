/**
 * Auth Store — Zustand 5.x
 *
 * Holds current user and org context.
 * Per pantheon-exact-stack.md: one store per domain, no single mega-store.
 */

import { create } from 'zustand';

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'tester' | 'viewer';
}

export interface Org {
  id: string;
  name: string;
}

interface AuthState {
  user: User | null;
  org: Org | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setUser: (user: User | null) => void;
  setOrg: (org: Org | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  org: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setOrg: (org) => set({ org }),
  setToken: (token) => set({ token }),
  logout: () => set({ user: null, org: null, token: null, isAuthenticated: false }),
}));
