import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { TargetAnalysisPage } from '../pages/TargetAnalysisPage';
import { EndpointDiscoveryPage } from '../pages/EndpointDiscoveryPage';
import { SimulationLibraryPage } from '../pages/SimulationLibraryPage';
import { ScenarioBuilderPage } from '../pages/ScenarioBuilderPage';
import { CustomScenarioPage } from '../pages/CustomScenarioPage';

// Mock global fetch for clean component rendering
global.fetch = vi.fn((url: string | URL | Request) => {
  const urlStr = url.toString();
  if (urlStr.includes('/api/apps')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve([
          {
            id: '11111111-1111-1111-1111-111111111111',
            name: 'Target Demo App',
            status: 'running',
            discovery_status: 'completed',
            target_profile: {
              detected_language: 'Python',
              detected_framework: 'FastAPI',
              exposed_ports: [8000],
              detected_database: 'PostgreSQL',
              auth_mechanisms: ['Bearer JWT'],
              auth_env_variables: ['JWT_SECRET'],
              confidence: 'high',
              confidence_basis: 'Matched FastAPI signatures',
            },
            discovered_endpoints: {
              endpoints: [
                {
                  path: '/api/v1/auth/login',
                  method: 'POST',
                  category: 'likely_auth',
                  description: 'Authenticate user',
                  requires_auth: false,
                  confidence: 0.95,
                  confidence_basis: 'Matches auth heuristic',
                },
              ],
            },
          },
        ]),
    } as Response);
  }

  if (urlStr.includes('/api/scenarios/presets')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve([
          {
            id: 'preset-sqli',
            name: 'SQLi Resilience Audit',
            category: 'sqli_resilience',
            description: 'Inject SQL syntax payloads',
            source: 'preset',
            is_preset: true,
            definition: {
              name: 'SQLi Resilience Audit',
              description: 'Inject SQL syntax payloads',
              category: 'sqli_resilience',
              target: { service: 'web', path: '/search', method: 'GET' },
              payload_category: 'sqli_resilience',
              concurrency: 5,
              duration: 30,
              expected_signals: ['500 Internal Server Error'],
            },
          },
        ]),
    } as Response);
  }

  if (urlStr.includes('/api/safety/policies')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          allowed_categories: ['sqli_resilience', 'brute_force'],
          disallowed_attack_classes: ['Reverse shells', 'Ransomware'],
          scope_constraints: ['Internal tenant namespaces only'],
          enforcement_level: 'Zero-Bypass Kernel Gate',
        }),
    } as Response);
  }

  if (urlStr.includes('/api/scenarios/generate')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          name: 'AI Generated SQLi Test',
          description: 'Testing SQL injection vulnerability',
          category: 'sqli_resilience',
          method: 'GET',
          target: { service: 'web', path: '/search', port: 8080, protocol: 'http' },
          concurrency: 15,
          duration: 30,
          expected_signals: ['500 Internal Server Error'],
          estimated_impact: 'medium',
          estimated_duration_seconds: 30,
          source: 'ai',
          tags: ['ai-generated', 'sqli_resilience'],
        }),
    } as Response);
  }

  if (urlStr.endsWith('/api/scenarios') || urlStr.includes('/api/scenarios?')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'scen-saved-123',
          name: 'AI Generated SQLi Test',
          category: 'sqli_resilience',
          source: 'ai',
          is_preset: false,
        }),
    } as Response);
  }

  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve([]),
  } as Response);
});

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('Pantheon Frontend Phase 5 - Phase 7 Verification Tests', () => {
  it('Phase 5: renders Target Analysis Page', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <TargetAnalysisPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('Target Analysis')).toBeInTheDocument();
    expect(screen.getByText(/Automated profiling of deployed applications/i)).toBeInTheDocument();
  });

  it('Phase 5: renders Endpoint Discovery Page', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <EndpointDiscoveryPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('Endpoint Discovery')).toBeInTheDocument();
    expect(screen.getByText(/Automatic OpenAPI\/Swagger spec detection/i)).toBeInTheDocument();
  });

  it('Phase 6 & 7: renders Simulation Library Page', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SimulationLibraryPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('Simulation Library')).toBeInTheDocument();
    expect(screen.getByText('AI Builder')).toBeInTheDocument();
    expect(screen.getByText('Author Custom')).toBeInTheDocument();
  });

  it('Phase 6: renders AI Scenario Builder Page', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ScenarioBuilderPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('AI Scenario Builder')).toBeInTheDocument();
    expect(screen.getByText(/Describe the security simulation/i)).toBeInTheDocument();
    expect(screen.getByText('Generate Scenario')).toBeInTheDocument();
  });

  it('Phase 6: AI Scenario Builder generates scenario and successfully saves to library', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ScenarioBuilderPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const textarea = screen.getByPlaceholderText(/Describe your simulation scenario/i);
    fireEvent.change(textarea, {
      target: { value: 'Test SQL injection resilience on search parameters' },
    });

    const generateBtn = screen.getByText('Generate Scenario');
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText('AI Generated SQLi Test')).toBeInTheDocument();
    });

    const saveBtn = screen.getByText('Save to Library');
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/Scenario saved successfully to your organization's Simulation Library!/i),
      ).toBeInTheDocument();
    });
  });

  it('Phase 6 & 7: renders Custom Scenario Page with Safety Guard Policies button', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CustomScenarioPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('Custom Scenario Authoring')).toBeInTheDocument();
    expect(screen.getByText('Safety Guard Policies')).toBeInTheDocument();
    expect(screen.getByText('Validate Schema')).toBeInTheDocument();
  });
});
