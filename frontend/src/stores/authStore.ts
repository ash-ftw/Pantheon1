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

const getStoredToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('pantheon_token');
};

const getStoredUser = (): User | null => {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem('pantheon_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const getStoredOrg = (): Org | null => {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem('pantheon_org');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const initialToken = getStoredToken();
const initialUser = getStoredUser();
const initialOrg = getStoredOrg();

export const useAuthStore = create<AuthState>((set) => ({
  user: initialUser,
  org: initialOrg,
  token: initialToken,
  isAuthenticated: !!initialToken || !!initialUser,
  isLoading: false,

  setUser: (user) => {
    if (typeof window !== 'undefined') {
      if (user) localStorage.setItem('pantheon_user', JSON.stringify(user));
      else localStorage.removeItem('pantheon_user');
    }
    set({ user, isAuthenticated: !!user });
  },
  setOrg: (org) => {
    if (typeof window !== 'undefined') {
      if (org) localStorage.setItem('pantheon_org', JSON.stringify(org));
      else localStorage.removeItem('pantheon_org');
    }
    set({ org });
  },
  setToken: (token) => {
    if (typeof window !== 'undefined') {
      if (token) localStorage.setItem('pantheon_token', token);
      else localStorage.removeItem('pantheon_token');
    }
    set({ token, isAuthenticated: !!token });
  },
  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('pantheon_token');
      localStorage.removeItem('pantheon_user');
      localStorage.removeItem('pantheon_org');
    }
    set({ user: null, org: null, token: null, isAuthenticated: false });
  },
}));
