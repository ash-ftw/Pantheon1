import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { PlaceholderPage } from '../pages/PlaceholderPage';
import { DesignPreviewPage } from '../pages/DesignPreviewPage';
import { InfrastructureViewPage } from '../pages/InfrastructureViewPage';
import { TeamManagementPage } from '../pages/TeamManagementPage';
import { AppOnboardingPage } from '../pages/AppOnboardingPage';
import { Shield } from 'lucide-react';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('Pantheon Frontend Phase 0 - Phase 4 Verification Tests', () => {
  it('Phase 0: renders placeholder page with title and phase badge', () => {
    render(
      <PlaceholderPage
        title="Dashboard"
        phase="Phase 14"
        description="Org-level overview"
        icon={<Shield data-testid="shield-icon" />}
      />,
    );

    expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0);
    expect(screen.getByText('Phase 14')).toBeInTheDocument();
    expect(screen.getAllByText('Org-level overview').length).toBeGreaterThan(0);
  });

  it('Phase 1: renders Design System Foundation Preview page', () => {
    render(
      <MemoryRouter>
        <DesignPreviewPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Design System Foundation')).toBeInTheDocument();
    expect(screen.getByText('Phase 1 Preview')).toBeInTheDocument();
    expect(screen.getByText('Button Primitives')).toBeInTheDocument();
  });

  it('Phase 2: renders Team Management Page', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <TeamManagementPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('Auth, Organization & Team Management')).toBeInTheDocument();
    expect(screen.getByText('Phase 2')).toBeInTheDocument();
    expect(screen.getByText('Invite Teammate')).toBeInTheDocument();
  });

  it('Phase 3: renders Infrastructure View Page', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <InfrastructureViewPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('Infrastructure & Provisioning')).toBeInTheDocument();
    expect(screen.getByText('Network Isolation')).toBeInTheDocument();
  });

  it('Phase 4: renders App Onboarding Page', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AppOnboardingPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getAllByText(/App Onboarding|Import Application/i).length).toBeGreaterThan(0);
  });

  it('Phase 4: renders Start, Stop, and Delete controls for applications', async () => {
    // Mock apps endpoint with running, stopped, and failed apps
    const origFetch = global.fetch;
    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = url.toString();
      if (urlStr.includes('/api/apps')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve([
              {
                id: 'app-run-1',
                org_id: 'org-1',
                name: 'Chess Run',
                source_type: 'git',
                source_url: 'https://github.com/example/chess.git',
                status: 'running',
                discovery_status: 'completed',
              },
              {
                id: 'app-stop-2',
                org_id: 'org-1',
                name: 'Chess Stopped',
                source_type: 'git',
                source_url: 'https://github.com/example/chess.git',
                status: 'stopped',
                discovery_status: 'pending',
              },
              {
                id: 'app-fail-3',
                org_id: 'org-1',
                name: 'Chess Failed',
                source_type: 'git',
                source_url: 'https://github.com/example/chess.git',
                status: 'failed',
                discovery_status: 'failed',
              },
            ]),
        } as Response);
      }
      return origFetch ? origFetch(url) : Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AppOnboardingPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText('Chess Run')).toBeInTheDocument();
    expect(await screen.findByText('Chess Stopped')).toBeInTheDocument();
    expect(await screen.findByText('Chess Failed')).toBeInTheDocument();

    // Verify Start App button is present for stopped app
    expect(screen.getByTestId('start-app-btn-app-stop-2')).toBeInTheDocument();

    // Verify Stop button is present for running app
    expect(screen.getByTestId('stop-app-btn-app-run-1')).toBeInTheDocument();

    // Verify Delete buttons are present for all apps including failed
    expect(screen.getByTestId('delete-app-btn-app-fail-3')).toBeInTheDocument();
    expect(screen.getByTestId('delete-app-btn-app-stop-2')).toBeInTheDocument();
    expect(screen.getByTestId('delete-app-btn-app-run-1')).toBeInTheDocument();

    global.fetch = origFetch;
  });
});
