import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { AttackGraphPage } from '../pages/AttackGraphPage';

// Mock ResizeObserver for jsdom
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = MockResizeObserver;

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

const mockGraphRuns = [
  {
    id: 'run-graph-101',
    scenario_name: 'SQL Injection Syntax & Tautology Probing',
    scenario_category: 'sqli_resilience',
    status: 'completed',
    current_step: 3,
    total_steps: 3,
    node_count: 5,
    edge_count: 4,
    findings_count: 1,
    created_at: new Date(Date.now() - 3600 * 1000).toISOString(),
    completed_at: new Date(Date.now() - 3500 * 1000).toISOString(),
  },
];

const mockGraphData = {
  test_run_id: 'run-graph-101',
  nodes: [
    {
      id: 'attacker',
      label: 'Range Attacker Pod',
      type: 'attacker',
      status: 'safe',
      step_discovered: 0,
      position: { x: 80, y: 200 },
      metadata: { cluster: 'range' },
    },
    {
      id: 'route_broker',
      label: 'Route Broker Ingress (/r/route-101)',
      type: 'route',
      status: 'safe',
      step_discovered: 0,
      position: { x: 320, y: 200 },
      metadata: { ttl: 1800 },
    },
    {
      id: 'step_1',
      label: 'Probe SQL Injection Signatures',
      type: 'endpoint',
      status: 'compromised',
      step_discovered: 1,
      position: { x: 580, y: 100 },
      metadata: { severity: 'high', cwe_id: 'CWE-89' },
    },
    {
      id: 'resource_1',
      label: 'Vulnerable Target: SQLi in users',
      type: 'database',
      status: 'compromised',
      step_discovered: 1,
      position: { x: 860, y: 100 },
      metadata: { severity: 'high', category: 'injection' },
    },
  ],
  edges: [
    {
      id: 'attacker->route',
      source: 'attacker',
      target: 'route_broker',
      label: 'Ephemeral Tunnel',
      status: 'traversed',
      step_discovered: 0,
      metadata: {},
    },
    {
      id: 'route->step_1',
      source: 'route_broker',
      target: 'step_1',
      label: 'HTTP POST',
      status: 'compromised',
      step_discovered: 1,
      metadata: {},
    },
    {
      id: 'step_1->resource_1',
      source: 'step_1',
      target: 'resource_1',
      label: 'Exploited (HIGH)',
      status: 'compromised',
      step_discovered: 1,
      metadata: {},
    },
  ],
};

describe('AttackGraphPage (Phase 10 — Attack Graph & Replay Engine)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = url.toString();

      if (urlStr.includes('/api/attack-graph/runs')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGraphRuns),
        } as Response);
      }

      if (urlStr.includes('/graph')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockGraphData),
        } as Response);
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response);
    });
  });

  it('renders AttackGraphPage header, run selector, and summary stats', async () => {
    render(
      <MemoryRouter>
        <AttackGraphPage />
      </MemoryRouter>
    );

    // Verify Title & Subtitle
    expect(screen.getByText(/Attack Graph & Replay Engine/i)).toBeDefined();
    expect(screen.getByText(/Visualise full multi-stage attack paths/i)).toBeDefined();

    // Verify Run selector dropdown appears
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /Select Test Run to Inspect/i })).toBeDefined();
      expect(screen.getByText(/SQL Injection Syntax & Tautology Probing/i)).toBeDefined();
    });

    // Verify Summary Stats
    expect(screen.getByText(/Total Graph Nodes/i)).toBeDefined();
    expect(screen.getByText(/Active Attack Paths/i)).toBeDefined();
    expect(screen.getByText(/Compromised Targets/i)).toBeDefined();
  });

  it('renders React Flow canvas and replay controller with timeline controls', async () => {
    render(
      <MemoryRouter>
        <AttackGraphPage />
      </MemoryRouter>
    );

    // Wait for graph data to load
    await waitFor(() => {
      expect(screen.getByText(/Viewing Timeline: Step 1 of 1/i)).toBeDefined();
    });

    // Verify Transport Buttons exist
    expect(screen.getByRole('button', { name: /Start/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Prev/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Play Replay/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Next/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /End/i })).toBeDefined();

    // Verify Scrubber Slider exists
    const slider = screen.getByRole('slider', { name: /Replay Timeline Scrubber/i });
    expect(slider).toBeDefined();

    // Click Prev button to step backward to Step 0
    const prevBtn = screen.getByRole('button', { name: /Prev/i });
    fireEvent.click(prevBtn);
    await waitFor(() => {
      expect(screen.getByText(/Viewing Timeline: Step 0 of 1/i)).toBeDefined();
    });
  });

  it('toggles playback with Play / Pause button', async () => {
    render(
      <MemoryRouter>
        <AttackGraphPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Viewing Timeline: Step 1 of 1/i)).toBeDefined();
      expect(screen.getByRole('button', { name: /Play Replay/i })).toBeDefined();
    });

    const playBtn = screen.getByRole('button', { name: /Play Replay/i });
    fireEvent.click(playBtn);

    // Should switch to Pause
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Pause/i })).toBeDefined();
    });

    // Click pause
    fireEvent.click(screen.getByRole('button', { name: /Pause/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Play Replay/i })).toBeDefined();
    });
  });
});
