import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { DefenceEnginePage } from '../pages/DefenceEnginePage';
import { ObservabilityPage } from '../pages/ObservabilityPage';

const mockTestRuns = [
  {
    id: 'run-101',
    scenario_name: 'SQL Injection Exploitation',
    status: 'completed',
    current_step: 3,
    total_steps: 3,
  },
];

const mockRecommendations = [
  {
    id: 'rec-1',
    org_id: 'org-1',
    test_run_id: 'run-101',
    finding_id: 'find-1',
    app_id: 'app-1',
    title: 'Enforce Parameterized SQL Queries & WAF Database Isolation',
    category: 'Input Sanitization & Data Layer',
    mitigation_type: 'infrastructure',
    mechanically_applicable: true,
    status: 'suggested',
    code_guidance: 'Replace raw SQL strings with ORM parameterized statements.',
    infra_manifest: {
      apiVersion: 'networking.k8s.io/v1',
      kind: 'NetworkPolicy',
      metadata: { name: 'isolate-database-access' },
    },
    target_resource: 'k8s:NetworkPolicy/isolate-database-access',
    applied_at: null,
    reverted_at: null,
    created_at: new Date().toISOString(),
  },
];

const mockRunMetrics = {
  test_run_id: 'run-101',
  app_id: 'app-1',
  scenario_name: 'SQL Injection Exploitation',
  status: 'completed',
  total_steps: 3,
  current_step: 3,
  avg_latency_ms: 45.2,
  p95_latency_ms: 84.1,
  min_latency_ms: 22.0,
  max_latency_ms: 92.5,
  status_code_counts: { '200': 2, '500': 1 },
  cpu_utilization_pct: 24.5,
  memory_utilization_mb: 154.2,
  network_io_kbps: 420.0,
  step_latencies: [
    {
      step_number: 1,
      step_name: 'Syntax Probe',
      latency_ms: 22.0,
      status_code: 200,
      timestamp: new Date().toISOString(),
    },
    {
      step_number: 2,
      step_name: 'Tautology Probe',
      latency_ms: 38.5,
      status_code: 200,
      timestamp: new Date().toISOString(),
    },
    {
      step_number: 3,
      step_name: 'Union Query Probe',
      latency_ms: 92.5,
      status_code: 500,
      timestamp: new Date().toISOString(),
    },
  ],
};

const mockRunEvents = [
  {
    id: 'evt-1',
    timestamp: new Date().toISOString(),
    event_type: 'simulation.started',
    severity: 'info',
    component: 'runner',
    message: 'Attack simulation initiated.',
    metadata: {},
  },
  {
    id: 'evt-2',
    timestamp: new Date().toISOString(),
    event_type: 'safety_guard.verified',
    severity: 'success',
    component: 'security_guard',
    message: 'Safety model verified.',
    metadata: {},
  },
];

const mockPlatformMetrics = {
  active_test_runs: 1,
  completed_test_runs: 5,
  open_routes: 1,
  total_findings: 3,
  total_recommendations: 3,
  applied_mitigations: 1,
  mitigation_rate_pct: 33.3,
  cluster_health: 'healthy',
};

describe('Phase 11 — Defence Engine & Observability Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn().mockImplementation((url: string, _opts?: RequestInit) => {
      if (url.includes('/api/attack-graph/runs')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockTestRuns,
        });
      }
      if (url.includes('/api/defence/recommendations/rec-1/apply')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            recommendation_id: 'rec-1',
            status: 'applied',
            message: 'Mitigation applied',
            target_resource: 'k8s:NetworkPolicy/isolate-database-access',
          }),
        });
      }
      if (url.includes('/api/defence/recommendations')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockRecommendations,
        });
      }
      if (url.includes('/api/observability/platform')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockPlatformMetrics,
        });
      }
      if (url.includes('/api/observability/metrics/runs/')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockRunMetrics,
        });
      }
      if (url.includes('/api/observability/events/runs/')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockRunEvents,
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    });
  });

  it('renders DefenceEnginePage with recommendations and statistics', async () => {
    render(
      <MemoryRouter>
        <DefenceEnginePage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/DEFENCE ENGINE & REMEDIATION/i)).toBeInTheDocument();
    expect(screen.getByText(/DISCOVERED FINDINGS/i)).toBeInTheDocument();
    expect(screen.getByText(/REMEDIATION COVERAGE/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Enforce Parameterized SQL Queries/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/k8s:NetworkPolicy\/isolate-database-access/i)).toBeInTheDocument();
    expect(screen.getAllByText(/SUGGESTED/i).length).toBeGreaterThanOrEqual(1);
  });

  it('triggers 1-Click Apply mitigation on DefenceEnginePage', async () => {
    render(
      <MemoryRouter>
        <DefenceEnginePage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Enforce Parameterized SQL Queries/i)).toBeInTheDocument();
    });

    const applyBtn = screen.getByRole('button', { name: /APPLY/i });
    expect(applyBtn).toBeInTheDocument();

    fireEvent.click(applyBtn);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/defence/recommendations/rec-1/apply'),
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  it('renders ObservabilityPage with latency distributions, status codes, and events', async () => {
    render(
      <MemoryRouter>
        <ObservabilityPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/SYSTEM & TEST RUN OBSERVABILITY/i)).toBeInTheDocument();
    expect(screen.getByText(/TENANT CLUSTER HEALTH/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/PROBE LATENCY & DURATION/i)).toBeInTheDocument();
      expect(screen.getByText(/HTTP STATUS CODE DISTRIBUTION/i)).toBeInTheDocument();
      expect(screen.getByText(/TARGET CONTAINER RESOURCE IMPACT/i)).toBeInTheDocument();
      expect(screen.getByText(/POD & EXECUTION EVENT STREAM/i)).toBeInTheDocument();
    });

    // Check latency metrics displayed
    expect(screen.getByText(/45.2ms/i)).toBeInTheDocument();
    expect(screen.getByText(/84.1ms/i)).toBeInTheDocument();

    // Check status code pills
    expect(screen.getByText(/HTTP 200/i)).toBeInTheDocument();
    expect(screen.getByText(/HTTP 500/i)).toBeInTheDocument();

    // Check event message
    expect(screen.getByText(/Attack simulation initiated./i)).toBeInTheDocument();
  });
});
