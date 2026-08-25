/**
 * Tenant Store — Zustand 5.x
 *
 * Tracks tenant cluster provisioning status and infrastructure state.
 * Per pantheon-exact-stack.md: one store per domain.
 */

import { create } from 'zustand';

export type ProvisioningStatus = 'pending' | 'provisioning' | 'ready' | 'error';

export interface TenantCluster {
  id: string;
  orgId: string;
  status: ProvisioningStatus;
  endpoint: string | null;
  createdAt: string;
}

interface TenantState {
  cluster: TenantCluster | null;
  isLoading: boolean;

  // Actions
  setCluster: (cluster: TenantCluster | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useTenantStore = create<TenantState>((set) => ({
  cluster: null,
  isLoading: false,

  setCluster: (cluster) => set({ cluster }),
  setLoading: (isLoading) => set({ isLoading }),
}));
