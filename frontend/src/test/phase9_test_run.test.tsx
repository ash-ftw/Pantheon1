import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { TestRunPage } from '../pages/TestRunPage';

// Mock WebSocket
class MockWebSocket {
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((error: unknown) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 10);
  }

  send() {}
  close() {
    if (this.onclose) this.onclose();
  }
}

// @ts-expect-error global mock
global.WebSocket = MockWebSocket;

const mockApps = [
  {
    id: 'app-vuln-1',
    name: 'Chess Arena Pro',
    source_type: 'git',
    status: 'running',
    target_profile: {
      exposed_ports: [8085],
    },
  },
];

const mockScenarios = [
  {
    id: 'preset-owasp-sqli',
    name: 'OWASP Top 10 — SQL Injection Suite',
    category: 'injection',
    description: 'Autonomous injection heuristics against query params and body payloads.',
  },
  {
    id: 'scen-custom-1',
    name: 'Custom Auth Bypass Attempt',
    category: 'auth_bypass',
    description: 'Tests token tampering and auth header bypasses.',
  },
];

const mockRuns = [
  {
    id: 'run-history-1',
    org_id: 'org-test-123',
    app_id: 'app-vuln-1',
    app_name: 'Chess Arena Pro',
    scenario_id: 'scen-custom-1',
    scenario_name: 'Custom Auth Bypass Attempt',
    scenario_category: 'auth_bypass',
    scenario_type: 'custom',
    status: 'completed',
    created_at: new Date(Date.now() - 3600 * 1000).toISOString(),
    started_at: new Date(Date.now() - 3590 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 3500 * 1000).toISOString(),
    stopped_at: null,
    total_steps: 4,
    current_step: 4,
    completed_steps: 4,
    current_step_name: 'Completed',
    total_findings: 1,
    critical_findings: 0,
    high_findings: 1,
    medium_findings: 0,
    low_findings: 0,
    route_id: 'route-test-1',
    route_url: '/r/route-test-1',
    metrics: {
      requests_sent: 50,
      successful_requests: 48,
      blocked_requests: 2,
      avg_latency_ms: 15,
      target_rps: 10,
    },
    logs: [
      { timestamp: '12:00:00', level: 'info', message: 'Test run initialized.' },
      { timestamp: '12:00:10', level: 'warning', message: 'Auth bypass vulnerability detected!' },
    ],
    findings: [
      {
        id: 'finding-1',
        title: 'Authentication Header Bypass Vulnerability',
        severity: 'high',
        category: 'auth_bypass',
        description: 'Server accepts requests without valid JWT signature.',
        endpoint: '/api/admin/users',
        http_method: 'GET',
        evidence: { status_code: 200 },
        created_at: new Date().toISOString(),
      },
    ],
  },
];

describe('TestRunPage (Phase 9 — Simulation Engine & Test Run Execution)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    global.fetch = vi.fn((url: string | URL | Request, init?: RequestInit) => {
      const urlStr = url.toString();

      if (urlStr.includes('/api/apps')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockApps),
        } as Response);
      }

      if (urlStr.includes('/api/scenarios')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockScenarios),
        } as Response);
      }

      if (urlStr.includes('/stop') && init?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: 'run-new-999',
              status: 'stopped',
              stopped_at: new Date().toISOString(),
              logs: [{ timestamp: '14:30:05', level: 'error', message: 'EMERGENCY STOP executed.' }],
            }),
        } as Response);
      }

      if (urlStr.includes('/api/test-runs') && init?.method === 'POST') {
        const body = JSON.parse(init.body as string);
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: 'run-new-999',
              org_id: 'org-test-123',
              app_id: body.app_id,
              scenario_name: 'OWASP Top 10 — SQL Injection Suite',
              scenario_category: 'injection',
              scenario_type: 'preset',
              status: 'running',
              created_at: new Date().toISOString(),
              started_at: new Date().toISOString(),
              completed_at: null,
              stopped_at: null,
              total_steps: 4,
              current_step: 1,
              completed_steps: 0,
              current_step_name: 'Pre-flight safety inspection',
              total_findings: 0,
              critical_findings: 0,
              high_findings: 0,
              medium_findings: 0,
              low_findings: 0,
              route_id: 'route-ephemeral-999',
              route_url: '/r/route-ephemeral-999',
              metrics: {
                requests_sent: 5,
                successful_requests: 5,
                blocked_requests: 0,
                avg_latency_ms: 12,
                target_rps: 10,
              },
              logs: [{ timestamp: '14:30:00', level: 'info', message: 'Test run launched.' }],
              findings: [],
            }),
        } as Response);
      }

      if (urlStr.includes('/api/test-runs/run-new-999')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: 'run-new-999',
              status: 'running',
              total_steps: 4,
              current_step: 2,
              completed_steps: 1,
              current_step_name: 'Fuzzing SQL parameter payloads',
              route_id: 'route-ephemeral-999',
              route_url: '/r/route-ephemeral-999',
              metrics: {
                requests_sent: 15,
                successful_requests: 14,
                blocked_requests: 1,
                avg_latency_ms: 14,
                target_rps: 10,
              },
              logs: [
                { timestamp: '14:30:00', level: 'info', message: 'Test run launched.' },
                { timestamp: '14:30:02', level: 'info', message: 'Ephemeral route opened.' },
              ],
              findings: [],
            }),
        } as Response);
      }

      if (urlStr.includes('/api/test-runs')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockRuns),
        } as Response);
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response);
    });
  });

  it('renders TestRunPage with header, launch button, and history table', async () => {
    render(
      <MemoryRouter>
        <TestRunPage />
      </MemoryRouter>
    );

    // Verify Title & Subtitle
    expect(screen.getByText(/Simulation Engine & Test Runs/i)).toBeDefined();
    expect(screen.getByText(/Orchestrate live attack scenarios/i)).toBeDefined();

    // Verify Launch Button exists
    expect(screen.getByRole('button', { name: /Launch Simulation Run/i })).toBeDefined();

    // Wait for history runs to load
    await waitFor(() => {
      expect(screen.getAllByText(/Custom Auth Bypass Attempt/i).length).toBeGreaterThan(0);
    });
  });

  it('opens Launch Simulation modal and displays scenarios', async () => {
    render(
      <MemoryRouter>
        <TestRunPage />
      </MemoryRouter>
    );

    const launchBtn = screen.getByRole('button', { name: /Launch Simulation Run/i });
    fireEvent.click(launchBtn);

    // Verify modal appears
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Launch Attack Simulation/i })).toBeDefined();
      expect(screen.getByText(/OWASP Top 10 — SQL Injection Suite/i)).toBeDefined();
      expect(screen.getByText(/Simulation Guard Pre-Check/i)).toBeDefined();
    });
  });

  it('launches a new test run and shows live panel with Kill Switch', async () => {
    render(
      <MemoryRouter>
        <TestRunPage />
      </MemoryRouter>
    );

    // Open launcher modal
    fireEvent.click(screen.getByRole('button', { name: /Launch Simulation Run/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Start Simulation/i })).toBeDefined();
    });

    // Select app
    const appSelect = screen.getByLabelText(/Target Deployed Application/i);
    fireEvent.change(appSelect, { target: { value: 'app-vuln-1' } });

    // Click Start Simulation
    fireEvent.click(screen.getByRole('button', { name: /Start Simulation/i }));

    // Verify Live Monitor view is rendered
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /EMERGENCY STOP/i })).toBeDefined();
      expect(screen.getByText(/Live Simulation Log Stream/i)).toBeDefined();
    });

    // Test Emergency Stop button
    const stopBtn = screen.getByRole('button', { name: /EMERGENCY STOP/i });
    fireEvent.click(stopBtn);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/stop'),
        expect.objectContaining({ method: 'POST' })
      );
    });
  });
});
