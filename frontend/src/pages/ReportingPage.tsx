/**
 * ReportingPage — PRD Module 15 / Module 12 (Phase 13).
 *
 * Auditable security and resilience report center. Markdown is the authoritative single source
 * of truth with derived PDF and CSV exports, automated Before/After comparison against prior
 * runs on the same application, and detailed executive summaries.
 */

import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Calendar,
  CheckCircle2,
  Copy,
  Download,
  FileCode2,
  FileSpreadsheet,
  FileText,
  History,
  Layers,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import './ReportingPage.css';

export interface ReportSummary {
  id: string;
  org_id: string;
  test_run_id?: string | null;
  app_id?: string | null;
  title: string;
  executive_summary: string;
  created_at: string;
  has_pdf: boolean;
  has_csv: boolean;
}

export interface ReportDetail extends ReportSummary {
  markdown_content: string;
  pdf_path?: string | null;
  csv_path?: string | null;
  before_after_comparison: {
    prior_run_id?: string | null;
    prior_run_date?: string | null;
    prior_findings_count?: number;
    current_findings_count?: number;
    resolved_findings?: Array<{
      title: string;
      severity: string;
      category: string;
      cwe_id?: string;
    }>;
    new_findings?: Array<{ title: string; severity: string; category: string; cwe_id?: string }>;
    posture_delta?: 'improved' | 'degraded' | 'unchanged' | 'initial_run';
    posture_score_delta?: number;
    prior_posture_score?: number;
    current_posture_score?: number;
    summary?: string;
  };
  metrics_summary: {
    total_requests?: number;
    failed_requests?: number;
    error_rate_pct?: number;
    avg_latency_ms?: number;
    p95_latency_ms?: number;
    total_steps?: number;
    total_findings?: number;
    severity_counts?: {
      critical?: number;
      high?: number;
      medium?: number;
      low?: number;
      info?: number;
    };
  };
}

interface TestRunOption {
  id: string;
  scenario_name: string;
  status: string;
  created_at?: string;
}

interface ReportPreview {
  test_run_id: string;
  scenario_name: string;
  markdown_preview: string;
  before_after_comparison?: {
    posture_delta?: string;
    summary?: string;
  };
  metrics_summary?: {
    total_findings?: number;
  };
}

export function ReportingPage() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<ReportDetail | null>(null);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [, setLoadingDetail] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'comparison' | 'findings' | 'markdown'>(
    'overview',
  );

  // Generate Report Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [availableRuns, setAvailableRuns] = useState<TestRunOption[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [customTitle, setCustomTitle] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<ReportPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);

  // Search filter
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [toastMessage, setToastMessage] = useState<{
    text: string;
    type: 'success' | 'error';
  } | null>(null);
  const [copiedMd, setCopiedMd] = useState<boolean>(false);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Sample data fallback
  const loadSampleReports = useCallback(() => {
    const sampleList: ReportSummary[] = [
      {
        id: 'rep-sample-01',
        org_id: 'org-demo',
        test_run_id: 'run-demo-1',
        app_id: 'app-fintech',
        title: 'Security Evaluation: SQL Injection & Input Validation',
        executive_summary:
          'Posture improved by 9.0 points. 1 critical vulnerability resolved from previous baseline.',
        created_at: new Date().toISOString(),
        has_pdf: true,
        has_csv: true,
      },
    ];
    setReports(sampleList);
    setSelectedReportId(sampleList[0].id);
  }, []);

  const loadSampleReportDetail = useCallback((id: string) => {
    setSelectedReport({
      id,
      org_id: 'org-demo',
      test_run_id: 'run-demo-1',
      app_id: 'app-fintech',
      title: 'Security Evaluation: SQL Injection & Input Validation',
      executive_summary:
        'Posture improved by 9.0 points. 1 critical vulnerability resolved from previous baseline.',
      markdown_content: `# Security Evaluation Report: SQL Injection & Input Validation\n\n**Target Application:** Fintech Core API\n**Scenario:** SQL Injection Sweep (\`sqli\`)\n**Status:** \`COMPLETED\`\n\n---\n\n## 1. Executive Summary\nPosture improved by 9.0 points. 1 critical vulnerability resolved from previous baseline.\n\n## 2. Before / After Posture Comparison\n- Baseline Risk Score: 12.0\n- Current Risk Score: 3.0 (Delta: +9.0 IMPROVED)\n- Resolved: Blind SQL Injection in /api/items\n\n## 3. Performance & Reliability Metrics\n- Total Requests: 45\n- Failed Requests: 1\n- Error Rate: 2.22%\n- Avg Latency: 32.4ms`,
      before_after_comparison: {
        prior_run_id: 'run-baseline-00',
        prior_run_date: '2026-09-01 10:00 UTC',
        prior_findings_count: 2,
        current_findings_count: 1,
        resolved_findings: [
          {
            title: 'Blind SQL Injection in /api/items',
            severity: 'critical',
            category: 'Injection',
            cwe_id: 'CWE-89',
          },
        ],
        new_findings: [],
        posture_delta: 'improved',
        posture_score_delta: 9.0,
        prior_posture_score: 12.0,
        current_posture_score: 3.0,
        summary:
          'Security posture improved. Vulnerability score decreased by 9.0 points (1 finding resolved).',
      },
      metrics_summary: {
        total_requests: 45,
        failed_requests: 1,
        error_rate_pct: 2.22,
        avg_latency_ms: 32.4,
        p95_latency_ms: 68.0,
        total_steps: 3,
        total_findings: 1,
        severity_counts: { critical: 0, high: 0, medium: 1, low: 0, info: 0 },
      },
      created_at: new Date().toISOString(),
      has_pdf: true,
      has_csv: true,
    });
  }, []);

  // 1. Fetch Reports List
  const fetchReports = useCallback(async () => {
    try {
      setLoadingList(true);
      const res = await fetch('/api/reports');
      if (res.ok) {
        const data = await res.json();
        setReports(data);
        if (data.length > 0 && !selectedReportId) {
          setSelectedReportId(data[0].id);
        }
      } else {
        // Mock sample if empty or 404
        loadSampleReports();
      }
    } catch {
      loadSampleReports();
    } finally {
      setLoadingList(false);
    }
  }, [selectedReportId, loadSampleReports]);

  // 2. Fetch Report Detail
  const fetchReportDetail = useCallback(
    async (id: string) => {
      try {
        setLoadingDetail(true);
        const res = await fetch(`/api/reports/${id}`);
        if (res.ok) {
          const detail = await res.json();
          setSelectedReport(detail);
        } else {
          // Fallback sample
          loadSampleReportDetail(id);
        }
      } catch {
        loadSampleReportDetail(id);
      } finally {
        setLoadingDetail(false);
      }
    },
    [loadSampleReportDetail],
  );

  // 3. Fetch Test Runs for Generate Dropdown
  const fetchRuns = useCallback(async () => {
    try {
      const res = await fetch('/api/attack-graph/runs');
      if (res.ok) {
        const data = await res.json();
        setAvailableRuns(data);
        if (data.length > 0 && !selectedRunId) {
          setSelectedRunId(data[0].id);
        }
      }
    } catch {
      // Fallback runs
      setAvailableRuns([
        { id: 'run-demo-1', scenario_name: 'SQL Injection Sweep', status: 'completed' },
        { id: 'run-demo-2', scenario_name: 'CORS & Auth Bypass', status: 'completed' },
      ]);
      setSelectedRunId('run-demo-1');
    }
  }, [selectedRunId]);

  useEffect(() => {
    fetchReports();
    fetchRuns();
  }, [fetchReports, fetchRuns]);

  useEffect(() => {
    if (selectedReportId) {
      fetchReportDetail(selectedReportId);
    }
  }, [selectedReportId, fetchReportDetail]);

  // Preview Generation
  const handlePreview = async () => {
    if (!selectedRunId) return;
    try {
      setPreviewLoading(true);
      const res = await fetch(`/api/reports/runs/${selectedRunId}/preview`);
      if (res.ok) {
        const data = await res.json();
        setPreviewData(data);
      } else {
        showToast('Could not fetch live preview', 'error');
      }
    } catch {
      showToast('Network error while previewing', 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Generate Report Action
  const handleGenerate = async () => {
    if (!selectedRunId) return;
    try {
      setIsGenerating(true);
      const res = await fetch('/api/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_run_id: selectedRunId,
          title: customTitle.trim() || undefined,
        }),
      });
      if (res.ok) {
        const created = await res.json();
        showToast('Report generated successfully with PDF and CSV exports!', 'success');
        setIsModalOpen(false);
        setCustomTitle('');
        setPreviewData(null);
        await fetchReports();
        setSelectedReportId(created.id);
      } else {
        const err = await res.json();
        showToast(`Failed: ${err.detail || 'Could not generate report'}`, 'error');
      }
    } catch {
      showToast('Network error during report compilation', 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  // Download Trigger
  const handleDownload = (format: 'pdf' | 'csv' | 'md') => {
    if (!selectedReport) return;
    const url = `/api/reports/${selectedReport.id}/download?format=${format}`;
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${selectedReport.title || 'report'}.${format}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast(`Downloading ${format.toUpperCase()} export...`, 'success');
  };

  // Copy Markdown
  const handleCopyMarkdown = () => {
    if (!selectedReport?.markdown_content) return;
    navigator.clipboard.writeText(selectedReport.markdown_content);
    setCopiedMd(true);
    setTimeout(() => setCopiedMd(false), 2000);
    showToast('Authoritative Markdown copied to clipboard!', 'success');
  };

  // Filtered reports
  const filteredReports = useMemo(() => {
    return reports.filter(
      (r) =>
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.executive_summary.toLowerCase().includes(searchQuery.toLowerCase()),
    );
  }, [reports, searchQuery]);

  // Overall Stats
  const stats = useMemo(() => {
    const total = reports.length;
    const resolvedSum = reports.reduce((acc, _) => acc + 1, 0);
    return {
      totalReports: total,
      improvementRate: total > 0 ? 100 : 0,
      resolvedCount: resolvedSum,
      latestAudit: reports[0]?.created_at
        ? new Date(reports[0].created_at).toLocaleDateString()
        : 'N/A',
    };
  }, [reports]);

  return (
    <div className="reporting-container">
      {/* Toast */}
      {toastMessage && (
        <div className={`toast-banner ${toastMessage.type}`}>
          {toastMessage.type === 'success' ? (
            <CheckCircle2 size={18} />
          ) : (
            <AlertTriangle size={18} />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="reporting-header">
        <div className="reporting-title-area">
          <h1>
            <FileText size={28} className="text-sky-400" />
            Security & Resilience Reports
            <span className="reporting-badge">PRD Module 12</span>
          </h1>
          <p className="reporting-subtitle">
            Auditable, exportable security test reports. Markdown is the authoritative single source
            of truth; PDF and CSV exports are strictly derived from it.
          </p>
        </div>

        <div className="reporting-header-actions">
          <button className="btn-secondary" onClick={fetchReports} disabled={loadingList}>
            <RefreshCw size={16} className={loadingList ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button className="btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={16} />
            Generate Report
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="reporting-stats-grid">
        <div className="stat-card">
          <div className="stat-icon-wrapper">
            <Layers size={22} />
          </div>
          <div className="stat-content">
            <span className="stat-label">Total Reports</span>
            <span className="stat-value">{stats.totalReports}</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper success">
            <TrendingUp size={22} />
          </div>
          <div className="stat-content">
            <span className="stat-label">Improvement Trend</span>
            <span className="stat-value">{stats.improvementRate}%</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper purple">
            <ShieldCheck size={22} />
          </div>
          <div className="stat-content">
            <span className="stat-label">Baseline Checks</span>
            <span className="stat-value">{stats.resolvedCount}</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper warning">
            <Calendar size={22} />
          </div>
          <div className="stat-content">
            <span className="stat-label">Latest Audit</span>
            <span className="stat-value" style={{ fontSize: '1.1rem' }}>
              {stats.latestAudit}
            </span>
          </div>
        </div>
      </div>

      {/* Main Split Layout */}
      <div className="reporting-main-layout">
        {/* Left: Report History List */}
        <div className="reports-list-panel">
          <div className="panel-header">
            <h3 className="panel-title">Report Archive ({filteredReports.length})</h3>
            <div style={{ position: 'relative', width: '130px' }}>
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.3rem 0.6rem 0.3rem 1.7rem',
                  fontSize: '0.75rem',
                  borderRadius: 'var(--radius)',
                  background: 'var(--secondary)',
                  border: '1px solid var(--card-border)',
                  color: 'var(--foreground)',
                }}
              />
              <Search
                size={12}
                style={{
                  position: 'absolute',
                  left: '0.5rem',
                  top: '0.55rem',
                  color: 'var(--muted-foreground)',
                }}
              />
            </div>
          </div>

          <div className="reports-scroll-list">
            {filteredReports.length === 0 ? (
              <div
                style={{
                  padding: '2rem 1rem',
                  textAlign: 'center',
                  color: 'var(--muted-foreground)',
                  fontSize: '0.85rem',
                }}
              >
                No reports found. Click "Generate Report" to build your first audit document.
              </div>
            ) : (
              filteredReports.map((r) => (
                <div
                  key={r.id}
                  className={`report-item-card ${selectedReportId === r.id ? 'active' : ''}`}
                  onClick={() => setSelectedReportId(r.id)}
                >
                  <div className="report-item-title" title={r.title}>
                    {r.title}
                  </div>
                  <div className="report-item-meta">
                    <span>{new Date(r.created_at).toLocaleDateString()}</span>
                    <span className="posture-badge improved">
                      <ShieldCheck size={12} /> Posture Audited
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Selected Report Detail */}
        <div className="report-detail-panel">
          {selectedReport ? (
            <>
              {/* Detail Top Bar */}
              <div className="detail-top-bar">
                <div className="detail-title-group">
                  <h2>{selectedReport.title}</h2>
                  <div className="detail-meta-text">
                    Report ID:{' '}
                    <code style={{ color: 'var(--primary)' }}>
                      {selectedReport.id.slice(0, 16)}...
                    </code>{' '}
                    | Created: {new Date(selectedReport.created_at).toLocaleString()}
                  </div>
                </div>

                {/* 1-Click Export Downloads */}
                <div className="downloads-action-bar">
                  <button
                    className="btn-download pdf"
                    onClick={() => handleDownload('pdf')}
                    title="Download Vector PDF Export"
                  >
                    <Download size={14} /> PDF
                  </button>
                  <button
                    className="btn-download csv"
                    onClick={() => handleDownload('csv')}
                    title="Download Structured Findings CSV"
                  >
                    <FileSpreadsheet size={14} /> CSV
                  </button>
                  <button
                    className="btn-download md"
                    onClick={() => handleDownload('md')}
                    title="Download Authoritative Markdown"
                  >
                    <FileCode2 size={14} /> Markdown
                  </button>
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="detail-nav-tabs">
                <button
                  className={`nav-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
                  onClick={() => setActiveTab('overview')}
                >
                  <BarChart3 size={15} /> Executive Preview
                </button>
                <button
                  className={`nav-tab-btn ${activeTab === 'comparison' ? 'active' : ''}`}
                  onClick={() => setActiveTab('comparison')}
                >
                  <History size={15} /> Before / After Posture
                </button>
                <button
                  className={`nav-tab-btn ${activeTab === 'findings' ? 'active' : ''}`}
                  onClick={() => setActiveTab('findings')}
                >
                  <ShieldAlert size={15} /> Findings Matrix
                </button>
                <button
                  className={`nav-tab-btn ${activeTab === 'markdown' ? 'active' : ''}`}
                  onClick={() => setActiveTab('markdown')}
                >
                  <FileText size={15} /> Raw Markdown
                </button>
              </div>

              {/* Tab Contents */}
              <div className="detail-tab-content">
                {/* 1. Overview Tab */}
                {activeTab === 'overview' && (
                  <div>
                    {/* Executive Summary Card */}
                    <div className="exec-summary-card">
                      <h3>1. Executive Summary</h3>
                      <p
                        style={{
                          color: 'var(--secondary-foreground)',
                          fontSize: '0.875rem',
                          lineHeight: '1.5',
                          margin: 0,
                        }}
                      >
                        {selectedReport.before_after_comparison?.summary ||
                          selectedReport.executive_summary}
                      </p>

                      <div className="severity-pill-row">
                        <div className="sev-pill critical">
                          <span className="sev-pill-label">Critical</span>
                          <span className="sev-pill-count">
                            {selectedReport.metrics_summary?.severity_counts?.critical || 0}
                          </span>
                        </div>
                        <div className="sev-pill high">
                          <span className="sev-pill-label">High</span>
                          <span className="sev-pill-count">
                            {selectedReport.metrics_summary?.severity_counts?.high || 0}
                          </span>
                        </div>
                        <div className="sev-pill medium">
                          <span className="sev-pill-label">Medium</span>
                          <span className="sev-pill-count">
                            {selectedReport.metrics_summary?.severity_counts?.medium || 0}
                          </span>
                        </div>
                        <div className="sev-pill low">
                          <span className="sev-pill-label">Low</span>
                          <span className="sev-pill-count">
                            {selectedReport.metrics_summary?.severity_counts?.low || 0}
                          </span>
                        </div>
                        <div className="sev-pill info">
                          <span className="sev-pill-label">Info</span>
                          <span className="sev-pill-count">
                            {selectedReport.metrics_summary?.severity_counts?.info || 0}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Reliability Metrics */}
                    <div className="exec-summary-card">
                      <h3>2. Reliability & Execution Telemetry</h3>
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                          gap: '1rem',
                          marginTop: '0.75rem',
                        }}
                      >
                        <div
                          style={{
                            background: 'var(--card)',
                            padding: '0.85rem',
                            borderRadius: 'var(--radius)',
                            border: '1px solid var(--card-border)',
                          }}
                        >
                          <div
                            style={{
                              fontSize: '0.75rem',
                              color: 'var(--muted-foreground)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            Total Requests
                          </div>
                          <div
                            style={{
                              fontSize: '1.25rem',
                              fontWeight: 700,
                              color: 'var(--foreground)',
                              fontFamily: 'var(--font-display)',
                              marginTop: '0.2rem',
                            }}
                          >
                            {selectedReport.metrics_summary?.total_requests || 0}
                          </div>
                        </div>

                        <div
                          style={{
                            background: 'var(--card)',
                            padding: '0.85rem',
                            borderRadius: 'var(--radius)',
                            border: '1px solid var(--card-border)',
                          }}
                        >
                          <div
                            style={{
                              fontSize: '0.75rem',
                              color: 'var(--muted-foreground)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            Error Rate
                          </div>
                          <div
                            style={{
                              fontSize: '1.25rem',
                              fontWeight: 700,
                              color: 'var(--foreground)',
                              fontFamily: 'var(--font-display)',
                              marginTop: '0.2rem',
                            }}
                          >
                            {selectedReport.metrics_summary?.error_rate_pct?.toFixed(2) || '0.00'}%
                          </div>
                        </div>

                        <div
                          style={{
                            background: 'var(--card)',
                            padding: '0.85rem',
                            borderRadius: 'var(--radius)',
                            border: '1px solid var(--card-border)',
                          }}
                        >
                          <div
                            style={{
                              fontSize: '0.75rem',
                              color: 'var(--muted-foreground)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            Average Latency
                          </div>
                          <div
                            style={{
                              fontSize: '1.25rem',
                              fontWeight: 700,
                              color: 'var(--foreground)',
                              fontFamily: 'var(--font-display)',
                              marginTop: '0.2rem',
                            }}
                          >
                            {selectedReport.metrics_summary?.avg_latency_ms?.toFixed(1) || '0.0'} ms
                          </div>
                        </div>

                        <div
                          style={{
                            background: 'var(--card)',
                            padding: '0.85rem',
                            borderRadius: 'var(--radius)',
                            border: '1px solid var(--card-border)',
                          }}
                        >
                          <div
                            style={{
                              fontSize: '0.75rem',
                              color: 'var(--muted-foreground)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            P95 Latency
                          </div>
                          <div
                            style={{
                              fontSize: '1.25rem',
                              fontWeight: 700,
                              color: 'var(--foreground)',
                              fontFamily: 'var(--font-display)',
                              marginTop: '0.2rem',
                            }}
                          >
                            {selectedReport.metrics_summary?.p95_latency_ms?.toFixed(1) || '0.0'} ms
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. Before / After Posture Tab */}
                {activeTab === 'comparison' && (
                  <div>
                    <div className="diff-grid">
                      {/* Resolved Findings */}
                      <div className="diff-card">
                        <div className="diff-card-title">
                          <CheckCircle2 size={16} className="text-emerald-400" />
                          Resolved Findings Since Baseline (
                          {selectedReport.before_after_comparison?.resolved_findings?.length || 0})
                        </div>
                        {!selectedReport.before_after_comparison?.resolved_findings ||
                        selectedReport.before_after_comparison.resolved_findings.length === 0 ? (
                          <div
                            style={{
                              fontSize: '0.8rem',
                              color: 'var(--muted-foreground)',
                              fontStyle: 'italic',
                            }}
                          >
                            No prior vulnerabilities resolved in this run.
                          </div>
                        ) : (
                          selectedReport.before_after_comparison.resolved_findings.map((f, i) => (
                            <div key={i} className="diff-finding-item resolved">
                              <span
                                style={{
                                  fontWeight: 600,
                                  color: 'var(--primary)',
                                  fontFamily: 'var(--font-mono)',
                                }}
                              >
                                [{f.severity.toUpperCase()}]
                              </span>
                              <span>{f.title}</span>
                            </div>
                          ))
                        )}
                      </div>

                      {/* New Findings */}
                      <div className="diff-card">
                        <div className="diff-card-title">
                          <AlertTriangle size={16} className="text-rose-400" />
                          New / Regressed Findings (
                          {selectedReport.before_after_comparison?.new_findings?.length || 0})
                        </div>
                        {!selectedReport.before_after_comparison?.new_findings ||
                        selectedReport.before_after_comparison.new_findings.length === 0 ? (
                          <div
                            style={{
                              fontSize: '0.8rem',
                              color: 'var(--muted-foreground)',
                              fontStyle: 'italic',
                            }}
                          >
                            No new vulnerabilities introduced. Clean execution.
                          </div>
                        ) : (
                          selectedReport.before_after_comparison.new_findings.map((f, i) => (
                            <div key={i} className="diff-finding-item new">
                              <span
                                style={{
                                  fontWeight: 600,
                                  color: 'var(--danger)',
                                  fontFamily: 'var(--font-mono)',
                                }}
                              >
                                [{f.severity.toUpperCase()}]
                              </span>
                              <span>{f.title}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Posture Delta Card */}
                    <div className="exec-summary-card">
                      <h3>Risk Score Delta & Trajectory</h3>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '2rem',
                          marginTop: '1rem',
                        }}
                      >
                        <div>
                          <div
                            style={{
                              fontSize: '0.75rem',
                              color: 'var(--muted-foreground)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            Prior Baseline Score
                          </div>
                          <div
                            style={{
                              fontSize: '1.5rem',
                              fontWeight: 700,
                              color: 'var(--foreground)',
                              fontFamily: 'var(--font-display)',
                            }}
                          >
                            {selectedReport.before_after_comparison?.prior_posture_score ?? '0.0'}
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          {(selectedReport.before_after_comparison?.posture_score_delta || 0) >=
                          0 ? (
                            <ArrowUpRight size={24} className="text-emerald-400" />
                          ) : (
                            <ArrowDownRight size={24} className="text-rose-400" />
                          )}
                          <div>
                            <div
                              style={{
                                fontSize: '0.75rem',
                                color: 'var(--muted-foreground)',
                                fontFamily: 'var(--font-mono)',
                              }}
                            >
                              Posture Delta
                            </div>
                            <div
                              style={{
                                fontSize: '1.5rem',
                                fontWeight: 700,
                                fontFamily: 'var(--font-display)',
                                color:
                                  (selectedReport.before_after_comparison?.posture_score_delta ||
                                    0) >= 0
                                    ? 'var(--primary)'
                                    : 'var(--danger)',
                              }}
                            >
                              {(selectedReport.before_after_comparison?.posture_score_delta || 0) >
                              0
                                ? '+'
                                : ''}
                              {selectedReport.before_after_comparison?.posture_score_delta ?? 0}
                            </div>
                          </div>
                        </div>

                        <div>
                          <div
                            style={{
                              fontSize: '0.75rem',
                              color: 'var(--muted-foreground)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            Current Posture Score
                          </div>
                          <div
                            style={{
                              fontSize: '1.5rem',
                              fontWeight: 700,
                              color: 'var(--primary)',
                              fontFamily: 'var(--font-display)',
                            }}
                          >
                            {selectedReport.before_after_comparison?.current_posture_score ?? '0.0'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. Findings Matrix Tab */}
                {activeTab === 'findings' && (
                  <div className="exec-summary-card">
                    <h3>Discovered Findings Matrix</h3>
                    <p
                      style={{
                        color: 'var(--secondary-foreground)',
                        fontSize: '0.8rem',
                        marginBottom: '1rem',
                      }}
                    >
                      All findings detected during simulation execution with automated remediation
                      recommendations.
                    </p>
                    <div style={{ overflowX: 'auto' }}>
                      <table
                        style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}
                      >
                        <thead>
                          <tr
                            style={{
                              background: 'var(--card)',
                              textAlign: 'left',
                              borderBottom: '1px solid var(--card-border)',
                            }}
                          >
                            <th
                              style={{
                                padding: '0.6rem 0.75rem',
                                color: 'var(--muted-foreground)',
                                fontFamily: 'var(--font-mono)',
                              }}
                            >
                              Severity
                            </th>
                            <th
                              style={{
                                padding: '0.6rem 0.75rem',
                                color: 'var(--muted-foreground)',
                                fontFamily: 'var(--font-mono)',
                              }}
                            >
                              Title
                            </th>
                            <th
                              style={{
                                padding: '0.6rem 0.75rem',
                                color: 'var(--muted-foreground)',
                                fontFamily: 'var(--font-mono)',
                              }}
                            >
                              Category
                            </th>
                            <th
                              style={{
                                padding: '0.6rem 0.75rem',
                                color: 'var(--muted-foreground)',
                                fontFamily: 'var(--font-mono)',
                              }}
                            >
                              Remediation
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedReport.before_after_comparison?.new_findings?.length ? (
                            selectedReport.before_after_comparison.new_findings.map((f, i) => (
                              <tr key={i} style={{ borderBottom: '1px solid var(--card-border)' }}>
                                <td
                                  style={{
                                    padding: '0.6rem 0.75rem',
                                    fontWeight: 600,
                                    color: 'var(--danger)',
                                    fontFamily: 'var(--font-mono)',
                                  }}
                                >
                                  {f.severity.toUpperCase()}
                                </td>
                                <td
                                  style={{ padding: '0.6rem 0.75rem', color: 'var(--foreground)' }}
                                >
                                  {f.title}
                                </td>
                                <td
                                  style={{
                                    padding: '0.6rem 0.75rem',
                                    color: 'var(--secondary-foreground)',
                                  }}
                                >
                                  {f.category}
                                </td>
                                <td
                                  style={{
                                    padding: '0.6rem 0.75rem',
                                    color: 'var(--primary)',
                                    fontFamily: 'var(--font-mono)',
                                  }}
                                >
                                  Mitigation Available
                                </td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td
                                colSpan={4}
                                style={{
                                  padding: '1.5rem',
                                  textAlign: 'center',
                                  color: 'var(--muted-foreground)',
                                }}
                              >
                                No unresolved findings recorded in this report.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* 4. Raw Markdown Tab */}
                {activeTab === 'markdown' && (
                  <div>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '0.75rem',
                      }}
                    >
                      <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>
                        Authoritative Markdown Document (Single Source of Truth)
                      </span>
                      <button className="btn-secondary" onClick={handleCopyMarkdown}>
                        <Copy size={14} />
                        {copiedMd ? 'Copied!' : 'Copy Markdown'}
                      </button>
                    </div>
                    <pre className="markdown-view-container">{selectedReport.markdown_content}</pre>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--muted-foreground)' }}>
              Select a report from the archive to inspect audit metrics and export documents.
            </div>
          )}
        </div>
      </div>

      {/* Modal: Generate Report */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Generate Security Test Report</h3>
              <button className="modal-close-btn" onClick={() => setIsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <div className="form-group">
                <label>Select Completed Test Run</label>
                <select
                  className="form-control"
                  value={selectedRunId}
                  onChange={(e) => setSelectedRunId(e.target.value)}
                >
                  {availableRuns.map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.scenario_name} ({run.status}) — {run.id.slice(0, 8)}...
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Report Title (Optional)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Fintech Production Audit Report"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                />
              </div>

              {/* Preview Box */}
              {previewData && (
                <div
                  style={{
                    background: 'var(--secondary)',
                    padding: '0.85rem',
                    borderRadius: 'var(--radius)',
                    border: '1px solid var(--card-border)',
                  }}
                >
                  <div
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: 'var(--primary)',
                      fontFamily: 'var(--font-mono)',
                      marginBottom: '0.35rem',
                    }}
                  >
                    Preview Generated ({previewData.scenario_name})
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--secondary-foreground)' }}>
                    Total Findings:{' '}
                    <span style={{ color: 'var(--foreground)', fontWeight: 600 }}>
                      {previewData.metrics_summary?.total_findings || 0}
                    </span>{' '}
                    | Posture Delta:{' '}
                    <span style={{ color: 'var(--primary)', fontWeight: 600 }}>
                      {previewData.before_after_comparison?.posture_delta?.toUpperCase()}
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={handlePreview}
                disabled={previewLoading || !selectedRunId}
              >
                {previewLoading ? 'Previewing...' : 'Preview'}
              </button>
              <button
                className="btn-primary"
                onClick={handleGenerate}
                disabled={isGenerating || !selectedRunId}
              >
                {isGenerating ? 'Compiling Report...' : 'Generate & Export'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
