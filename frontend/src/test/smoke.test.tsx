import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
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
});
