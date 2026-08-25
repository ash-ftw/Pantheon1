/**
 * Test Run Store — Zustand 5.x
 *
 * Manages active test run state, real-time progress, and WebSocket connection.
 * Per pantheon-exact-stack.md: one store per domain.
 */

import { create } from 'zustand';

export type TestRunStatus = 'pending' | 'running' | 'completed' | 'stopped' | 'failed';

export interface TestRun {
  id: string;
  scenarioId: string;
  appId: string;
  status: TestRunStatus;
  startedAt: string | null;
  completedAt: string | null;
  progress: number; // 0-100
}

export interface RouteStatus {
  isOpen: boolean;
  target: string | null;
  openedAt: string | null;
  expiresAt: string | null;
}

interface TestRunState {
  activeRun: TestRun | null;
  routeStatus: RouteStatus | null;
  isLoading: boolean;

  // Actions
  setActiveRun: (run: TestRun | null) => void;
  setRouteStatus: (status: RouteStatus | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useTestRunStore = create<TestRunState>((set) => ({
  activeRun: null,
  routeStatus: null,
  isLoading: false,

  setActiveRun: (activeRun) => set({ activeRun }),
  setRouteStatus: (routeStatus) => set({ routeStatus }),
  setLoading: (isLoading) => set({ isLoading }),
}));
