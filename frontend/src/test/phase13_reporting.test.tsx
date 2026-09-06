import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { ReportingPage } from '../pages/ReportingPage';

const mockReports = [
  {
    id: 'report-101',
    org_id: 'org-1',
    test_run_id: 'run-101',
    app_id: 'app-1',
    title: 'Financial Core Security Evaluation Report',
    executive_summary: 'Posture improved by 9.0 points. 1 critical vulnerability resolved from previous baseline.',
    created_at: '2026-09-06T12:00:00Z',
    has_pdf: true,
    has_csv: true,
  },
];

const mockReportDetail = {
  id: 'report-101',
  org_id: 'org-1',
  test_run_id: 'run-101',
  app_id: 'app-1',
  title: 'Financial Core Security Evaluation Report',
  executive_summary: 'Posture improved by 9.0 points. 1 critical vulnerability resolved from previous baseline.',
  markdown_content: '# Financial Core Security Evaluation Report\n\nAll checks passed.',
  pdf_path: '/data/reports/report-101.pdf',
  csv_path: '/data/reports/report-101.csv',
  before_after_comparison: {
    prior_run_id: 'run-baseline-0',
    prior_run_date: '2026-09-01 10:00 UTC',
    prior_findings_count: 2,
    current_findings_count: 1,
    resolved_findings: [
      { title: 'Blind SQL Injection in /api/items', severity: 'critical', category: 'Injection', cwe_id: 'CWE-89' },
    ],
    new_findings: [
      { title: 'Missing Security Header X-Frame-Options', severity: 'low', category: 'Misconfiguration' },
    ],
    posture_delta: 'improved',
    posture_score_delta: 9.0,
    prior_posture_score: 12.0,
    current_posture_score: 3.0,
    summary: 'Security posture improved significantly against baseline.',
  },
  metrics_summary: {
    total_requests: 60,
    failed_requests: 2,
    error_rate_pct: 3.33,
    avg_latency_ms: 34.5,
    p95_latency_ms: 72.0,
    total_steps: 3,
    total_findings: 1,
    severity_counts: {
      critical: 0,
      high: 0,
      medium: 0,
      low: 1,
      info: 0,
    },
  },
  created_at: '2026-09-06T12:00:00Z',
  has_pdf: true,
  has_csv: true,
};

describe('Phase 13 — Reporting Engine UI (PRD Module 12)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      const urlStr = url.toString();

      if (urlStr === '/api/reports') {
        return Promise.resolve({
          ok: true,
          json: async () => mockReports,
        });
      }

      if (urlStr.startsWith('/api/reports/report-101')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockReportDetail,
        });
      }

      if (urlStr === '/api/attack-graph/runs') {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { id: 'run-101', scenario_name: 'SQL Injection Sweep', status: 'completed' },
          ],
        });
      }

      if (urlStr === '/api/reports/generate' && init?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: async () => mockReportDetail,
        });
      }

      if (urlStr.includes('/preview')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            scenario_name: 'SQL Injection Sweep',
            metrics_summary: { total_findings: 1 },
            before_after_comparison: { posture_delta: 'improved' },
          }),
        });
      }

      return Promise.resolve({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      });
    });
  });

  it('renders ReportingPage header, module badge, and statistics cards', async () => {
    render(
      <MemoryRouter>
        <ReportingPage />
      </MemoryRouter>
    );

    expect(screen.getByText('Security & Resilience Reports')).toBeInTheDocument();
    expect(screen.getByText('PRD Module 12')).toBeInTheDocument();
    expect(screen.getByText('Total Reports')).toBeInTheDocument();
    expect(screen.getByText('Improvement Trend')).toBeInTheDocument();
    expect(screen.getByText('Baseline Checks')).toBeInTheDocument();
  });

  it('renders report archive and loads report detail with severity counts', async () => {
    render(
      <MemoryRouter>
        <ReportingPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('Financial Core Security Evaluation Report').length).toBeGreaterThan(0);
    });

    // Wait for detail view to load
    await waitFor(() => {
      expect(screen.getByText('1. Executive Summary')).toBeInTheDocument();
    });

    expect(screen.getByText('Security posture improved significantly against baseline.')).toBeInTheDocument();

    // Export download action buttons
    expect(screen.getByTitle('Download Vector PDF Export')).toBeInTheDocument();
    expect(screen.getByTitle('Download Structured Findings CSV')).toBeInTheDocument();
    expect(screen.getByTitle('Download Authoritative Markdown')).toBeInTheDocument();
  });

  it('switches navigation tabs to Before / After Posture and Findings Matrix', async () => {
    render(
      <MemoryRouter>
        <ReportingPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Before / After Posture')).toBeInTheDocument();
    });

    // Switch to Before / After Posture
    fireEvent.click(screen.getByText('Before / After Posture'));
    expect(screen.getByText(/Resolved Findings Since Baseline/i)).toBeInTheDocument();
    expect(screen.getByText('Blind SQL Injection in /api/items')).toBeInTheDocument();
    expect(screen.getByText('Risk Score Delta & Trajectory')).toBeInTheDocument();

    // Switch to Findings Matrix
    fireEvent.click(screen.getByText('Findings Matrix'));
    expect(screen.getByText('Discovered Findings Matrix')).toBeInTheDocument();
    expect(screen.getByText('Missing Security Header X-Frame-Options')).toBeInTheDocument();

    // Switch to Raw Markdown
    fireEvent.click(screen.getByText('Raw Markdown'));
    expect(screen.getByText('Authoritative Markdown Document (Single Source of Truth)')).toBeInTheDocument();
    expect(screen.getByText(/Copy Markdown/i)).toBeInTheDocument();
  });

  it('opens Generate Report modal and triggers report compilation', async () => {
    render(
      <MemoryRouter>
        <ReportingPage />
      </MemoryRouter>
    );

    const generateBtn = screen.getByRole('button', { name: /Generate Report/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText('Generate Security Test Report')).toBeInTheDocument();
      expect(screen.getByText('Select Completed Test Run')).toBeInTheDocument();
    });

    // Wait for the runs dropdown to be populated
    await waitFor(() => {
      expect(screen.getByText(/SQL Injection Sweep/i)).toBeInTheDocument();
    });

    // Trigger preview
    const previewBtn = screen.getByRole('button', { name: /^Preview$/i });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText(/Preview Generated/i)).toBeInTheDocument();
    });

    // Submit report generation
    const submitBtn = screen.getByRole('button', { name: /Generate & Export/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/reports/generate',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });
});
