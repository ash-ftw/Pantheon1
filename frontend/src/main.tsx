/**
 * Pantheon Frontend — Application Entry Point
 *
 * Wires: React 19, React Router 7 data router, TanStack Query 5 provider.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';

import './index.css';
import { router } from './router';

/**
 * TanStack Query client.
 * Query keys are namespaced by org/tenant to prevent cross-tenant cache bleed:
 *   ['org', orgId, 'apps']
 *   ['org', orgId, 'testRuns', testRunId]
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
