import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { RouteBrokerPage } from '../pages/RouteBrokerPage';

const mockRoutes = [
  {
    id: 'route-active-1',
    org_id: 'org-test-123',
    test_run_id: 'test-run-123',
    app_id: 'app-test-123',
    target_service: 'vuln-shop-frontend',
    target_port: 8080,
    path_prefix: '/',
    route_url: '/r/route-active-1',
    public_url: '/r/route-active-1',
    internal_url: 'http://pantheon-route-active-1.tenant-org-test.svc.cluster.local:8080',
    status: 'active',
    ttl_seconds: 1800,
    created_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 1800 * 1000).toISOString(),
    revoked_at: null,
    revocation_reason: null,
    ingress_name: 'pantheon-route-active-1',
    namespace: 'tenant-org-test',
    ttl_remaining_seconds: 1795,
  },
  {
    id: 'route-revoked-2',
    org_id: 'org-test-123',
    test_run_id: null,
    app_id: null,
    target_service: 'auth-service',
    target_port: 4000,
    path_prefix: '/auth',
    route_url: '/r/route-revoked-2',
    public_url: '/r/route-revoked-2',
    internal_url: 'http://pantheon-route-revoked-2.tenant-org-test.svc.cluster.local:4000',
    status: 'revoked',
    ttl_seconds: 900,
    created_at: new Date(Date.now() - 3600 * 1000).toISOString(),
    expires_at: new Date(Date.now() - 2700 * 1000).toISOString(),
    revoked_at: new Date(Date.now() - 3000 * 1000).toISOString(),
    revocation_reason: 'manual_kill_switch',
    ingress_name: 'pantheon-route-revoked-2',
    namespace: 'tenant-org-test',
    ttl_remaining_seconds: 0,
  },
];

const mockApps = [
  {
    id: 'app-test-123',
    name: 'VulnShop',
    source_type: 'git',
    status: 'running',
  },
];

describe('RouteBrokerPage (Phase 8 — Route Broker & Kill Switch)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    global.fetch = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const urlStr = url.toString();

      if (urlStr.includes('/api/routes') && init?.method === 'DELETE') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: 'route-active-1',
              status: 'revoked',
              revoked_at: new Date().toISOString(),
              revocation_reason: 'manual_kill_switch',
              ttl_remaining_seconds: 0,
            }),
        } as Response);
      }

      if (urlStr.includes('/api/routes') && init?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: 'route-new-3',
              org_id: 'org-test-123',
              test_run_id: null,
              app_id: null,
              target_service: 'api-service',
              target_port: 5000,
              path_prefix: '/',
              route_url: 'http://route-new-3.pantheon-range.svc.cluster.local:80/',
              status: 'active',
              ttl_seconds: 3600,
              created_at: new Date().toISOString(),
              expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
              revoked_at: null,
              revocation_reason: null,
              ingress_name: 'pantheon-route-new-3',
              namespace: 'tenant-org-test',
              ttl_remaining_seconds: 3600,
            }),
        } as Response);
      }

      if (urlStr.includes('/api/routes')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockRoutes),
        } as Response);
      }

      if (urlStr.includes('/api/apps')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockApps),
        } as Response);
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response);
    });
  });

  it('renders Route Broker header, kill switch button, and stat counters', async () => {
    render(
      <MemoryRouter>
        <RouteBrokerPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Route Broker & Kill Switch/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Active Routes/i)).toBeInTheDocument();
    expect(screen.getByText(/Kill Switch Revocations/i)).toBeInTheDocument();
    expect(screen.getByText(/Emergency SLA/i)).toBeInTheDocument();

    const killAllBtn = screen.getByTestId('emergency-kill-all-btn');
    expect(killAllBtn).toBeInTheDocument();
    expect(killAllBtn).not.toBeDisabled();
  });

  it('displays route cards with target service and live countdown timer', async () => {
    render(
      <MemoryRouter>
        <RouteBrokerPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('vuln-shop-frontend')).toBeInTheDocument();
    });

    expect(screen.getByText('auth-service')).toBeInTheDocument();
    expect(screen.getByText(/REVOKED: manual_kill_switch/i)).toBeInTheDocument();

    // Verify kill button is available for active route
    const killBtn = screen.getByTestId('kill-route-btn-route-active-1');
    expect(killBtn).toBeInTheDocument();
  });

  it('opens modal on Open Route button click with security policy notice', async () => {
    render(
      <MemoryRouter>
        <RouteBrokerPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('open-route-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('open-route-btn'));

    expect(screen.getByText(/Open Ephemeral Attack Route/i)).toBeInTheDocument();
    expect(screen.getByText(/Application-Layer Scoping/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Target Kubernetes Service Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Target HTTP\/HTTPS Port/i)).toBeInTheDocument();
  });

  it('triggers synchronous emergency kill switch on single route', async () => {
    render(
      <MemoryRouter>
        <RouteBrokerPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('kill-route-btn-route-active-1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('kill-route-btn-route-active-1'));

    await waitFor(() => {
      expect(screen.getByText(/EMERGENCY KILL SWITCH: Route route-ac revoked in <500ms./i)).toBeInTheDocument();
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/routes/route-active-1?reason=manual_kill_switch'),
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('renders Human Test URL and toggles collapsible Attacker Pod Technical Details', async () => {
    render(
      <MemoryRouter>
        <RouteBrokerPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('vuln-shop-frontend')).toBeInTheDocument();
    });

    // Verify Human Test URL is displayed
    expect(screen.getAllByText(/Human Test URL/i).length).toBeGreaterThan(0);

    // Verify Test Link button exists
    const testLink = screen.getByTestId('test-link-route-active-1');
    expect(testLink).toBeInTheDocument();
    expect(testLink).toHaveAttribute('href', expect.stringContaining('/r/'));

    // Verify technical details accordion button exists
    const techToggleBtns = screen.getAllByText(/Attacker Pod Route & Technical Details/i);
    expect(techToggleBtns.length).toBeGreaterThan(0);

    // Expand technical details
    fireEvent.click(techToggleBtns[0]);

    await waitFor(() => {
      expect(screen.getByText(/Internal Attacker URL/i)).toBeInTheDocument();
    });
  });
});
