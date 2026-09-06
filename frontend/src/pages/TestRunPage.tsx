/**
 * TestRunPage — PRD Module 10: Simulation Engine & Live Test Run Execution.
 *
 * Implements:
 * 1. Attack Scenario Launcher with pre-flight safety policy check
 * 2. Real-time Live Run View with WebSocket streaming log terminal
 * 3. Prominent Emergency Stop (Kill Switch) with < 5s revocation guarantee
 * 4. Step-by-step progress tracker & target response performance metrics
 * 5. Dynamic security findings detection list
 * 6. Historical Test Run inspection and filter tabs
 */

import {
  AlertTriangle,
  Flame,
  Play,
  RefreshCw,
  Shield,
  ShieldAlert,
  Square,
  Terminal,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useAuthStore } from '../stores/authStore';
import './TestRunPage.css';

/* ------------------------------------------------------------------ */
/*  Types & Interfaces                                                */
/* ------------------------------------------------------------------ */

interface FindingItem {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: string;
  cwe_id?: string;
  owasp_category?: string;
  description: string;
  evidence: Record<string, unknown>;
  remediation_guidance: string;
  created_at: string;
}

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

interface TestRunMetrics {
  requests_sent: number;
  successful_requests: number;
  blocked_requests: number;
  error_requests: number;
  avg_latency_ms: number;
  target_rps: number;
  duration_seconds: number;
}

interface TestRunRecord {
  id: string;
  org_id: string;
  app_id: string;
  scenario_id?: string;
  scenario_name: string;
  scenario_category: string;
  route_id?: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'stopped';
  current_step: number;
  total_steps: number;
  current_step_name?: string;
  parameters: Record<string, unknown>;
  metrics: TestRunMetrics;
  logs: LogEntry[];
  findings: FindingItem[];
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

interface AppOption {
  id: string;
  name: string;
  status: string;
  target_profile?: {
    exposed_ports?: number[];
  };
}

interface ScenarioOption {
  id: string;
  name: string;
  category: string;
  description: string;
}

const API_BASE = '/api';

export function TestRunPage() {
  const token = useAuthStore((s) => s.token);

  // Data states
  const [testRuns, setTestRuns] = useState<TestRunRecord[]>([]);
  const [apps, setApps] = useState<AppOption[]>([]);
  const [scenarios, setScenarios] = useState<ScenarioOption[]>([]);
  const [activeRun, setActiveRun] = useState<TestRunRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Launch modal states
  const [isLaunchModalOpen, setIsLaunchModalOpen] = useState(false);
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [launching, setLaunching] = useState(false);
  const [ratePerSecond, setRatePerSecond] = useState(25);

  // Kill switch action state
  const [stopping, setStopping] = useState(false);

  // Terminal container ref (scrolls ONLY terminal element, never window)
  const terminalBodyRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // WebSocket ref
  const wsRef = useRef<WebSocket | null>(null);

  // Stats memoization
  const activeRoutesCount = useMemo(
    () => testRuns.filter((r) => r.status === 'running' || r.status === 'queued').length,
    [testRuns],
  );
  const completedRunsCount = useMemo(
    () => testRuns.filter((r) => r.status === 'completed').length,
    [testRuns],
  );
  const stoppedRunsCount = useMemo(
    () => testRuns.filter((r) => r.status === 'stopped').length,
    [testRuns],
  );
  const failedRunsCount = useMemo(
    () => testRuns.filter((r) => r.status === 'failed').length,
    [testRuns],
  );
  const findingsCount = useMemo(
    () => testRuns.reduce((acc, r) => acc + (r.findings?.length || 0), 0),
    [testRuns],
  );

  /* ------------------------------------------------------------------ */
  /*  Data Fetching                                                     */
  /* ------------------------------------------------------------------ */

  const fetchTestRuns = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/test-runs`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data: TestRunRecord[] = await res.json();
        setTestRuns(data);

        // Functional update to decouple fetchTestRuns identity from activeRun
        setActiveRun((currentActive) => {
          if (currentActive) {
            const updated = data.find((r) => r.id === currentActive.id);
            if (!updated) return currentActive;
            // If actively executing, preserve live streaming logs and findings
            if (currentActive.status === 'running') {
              return {
                ...updated,
                logs:
                  currentActive.logs.length > updated.logs.length
                    ? currentActive.logs
                    : updated.logs,
                findings:
                  currentActive.findings.length > updated.findings.length
                    ? currentActive.findings
                    : updated.findings,
                current_step: Math.max(currentActive.current_step, updated.current_step),
                metrics: currentActive.metrics || updated.metrics,
              };
            }
            return updated;
          } else {
            const inProgress = data.find((r) => r.status === 'running' || r.status === 'queued');
            return inProgress || null;
          }
        });
      }
    } catch {
      // Non-blocking
    }
  }, [token]);

  const fetchMetadata = useCallback(async () => {
    try {
      const [appsRes, scenRes] = await Promise.all([
        fetch(`${API_BASE}/apps`, { headers: token ? { Authorization: `Bearer ${token}` } : {} }),
        fetch(`${API_BASE}/scenarios`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }),
      ]);
      if (appsRes.ok) {
        const appsData = await appsRes.json();
        setApps(appsData);
        setSelectedAppId((curr) => curr || (appsData.length > 0 ? appsData[0].id : ''));
      }
      if (scenRes.ok) {
        const scenData = await scenRes.json();
        setScenarios(scenData);
        setSelectedScenarioId((curr) => curr || (scenData.length > 0 ? scenData[0].id : ''));
      }
    } catch {
      // Non-blocking
    }
  }, [token]);

  useEffect(() => {
    let mounted = true;
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchTestRuns(), fetchMetadata()]);
      if (mounted) setLoading(false);
    };
    init();
    return () => {
      mounted = false;
    };
  }, [fetchTestRuns, fetchMetadata]);

  /* ------------------------------------------------------------------ */
  /*  Real-Time WebSocket Streaming                                     */
  /* ------------------------------------------------------------------ */

  const activeRunId = activeRun?.id;
  const isTerminal =
    !activeRun ||
    activeRun.status === 'completed' ||
    activeRun.status === 'stopped' ||
    activeRun.status === 'failed';

  const fetchTestRunsRef = useRef(fetchTestRuns);
  fetchTestRunsRef.current = fetchTestRuns;

  useEffect(() => {
    if (!activeRunId || isTerminal) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/test-runs/${activeRunId}/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const { event: evtType, data } = payload;

        setActiveRun((prev) => {
          if (!prev || prev.id !== activeRunId) return prev;

          if (evtType === 'step_started') {
            return {
              ...prev,
              current_step: data.current_step,
              total_steps: data.total_steps,
              current_step_name: data.step_name,
              logs: [
                ...prev.logs,
                {
                  timestamp: new Date().toISOString(),
                  level: 'STEP',
                  message: `Step ${data.current_step}/${data.total_steps}: ${data.step_name}`,
                },
              ],
            };
          }

          if (evtType === 'step_completed') {
            return {
              ...prev,
              metrics: data.metrics || prev.metrics,
            };
          }

          if (evtType === 'finding_discovered') {
            const exists = prev.findings.some((f) => f.id === data.id);
            if (exists) return prev;

            return {
              ...prev,
              findings: [
                ...prev.findings,
                {
                  id: data.id,
                  title: data.title,
                  severity: data.severity,
                  category: data.category,
                  cwe_id: data.cwe_id,
                  description: data.description,
                  evidence: data.evidence || {},
                  remediation_guidance: data.remediation_guidance || '',
                  created_at: new Date().toISOString(),
                },
              ],
            };
          }

          if (evtType === 'run_completed') {
            return {
              ...prev,
              status: 'completed',
              completed_at: data.completed_at,
              metrics: data.metrics || prev.metrics,
              logs: [
                ...prev.logs,
                {
                  timestamp: new Date().toISOString(),
                  level: 'SUCCESS',
                  message: `Simulation completed. ${data.findings_count} findings discovered.`,
                },
              ],
            };
          }

          if (evtType === 'run_stopped') {
            return {
              ...prev,
              status: 'stopped',
              completed_at: data.completed_at,
              logs: [
                ...prev.logs,
                {
                  timestamp: new Date().toISOString(),
                  level: 'ALERT',
                  message: `EMERGENCY STOP: ${data.reason}`,
                },
              ],
            };
          }

          return prev;
        });

        // Refresh list to keep counters current
        if (evtType === 'run_completed' || evtType === 'run_stopped') {
          fetchTestRunsRef.current();
        }
      } catch {
        // Non-fatal parse error
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [activeRunId, isTerminal]);

  // Terminal Auto-scroll (scrolls ONLY terminal element, never browser window)
  useEffect(() => {
    if (autoScroll && terminalBodyRef.current) {
      terminalBodyRef.current.scrollTop = terminalBodyRef.current.scrollHeight;
    }
  }, [activeRun?.logs?.length, autoScroll]);

  /* ------------------------------------------------------------------ */
  /*  Actions                                                           */
  /* ------------------------------------------------------------------ */

  const handleLaunchRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId) return;

    setLaunching(true);
    setError(null);

    const chosenScenario = scenarios.find((s) => s.id === selectedScenarioId);

    try {
      const res = await fetch(`${API_BASE}/test-runs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          app_id: selectedAppId,
          scenario_id: selectedScenarioId || null,
          scenario_name: chosenScenario?.name || 'Automated Security Probe',
          scenario_category: chosenScenario?.category || 'api_abuse',
          parameters: { rate_per_second: Number(ratePerSecond) },
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to launch test run');
      }

      const createdRun: TestRunRecord = await res.json();
      setTestRuns((prev) => [createdRun, ...prev]);
      setActiveRun(createdRun);
      setIsLaunchModalOpen(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown launch error');
    } finally {
      setLaunching(false);
    }
  };

  const handleEmergencyStop = async () => {
    if (!activeRun) return;

    setStopping(true);
    try {
      const res = await fetch(`${API_BASE}/test-runs/${activeRun.id}/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ reason: 'Operator Emergency Kill Switch' }),
      });

      if (res.ok) {
        const updated = await res.json();
        setActiveRun(updated);
        setTestRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      }
    } catch {
      // Non-blocking
    } finally {
      setStopping(false);
    }
  };

  /* ------------------------------------------------------------------ */
  /*  Helpers                                                           */
  /* ------------------------------------------------------------------ */

  const filteredRuns = testRuns.filter((r) => {
    if (statusFilter === 'all') return true;
    return r.status === statusFilter;
  });

  const getAppName = (appId?: string | null) => {
    if (!appId) return 'Target App';
    const app = apps.find((a) => a.id === appId);
    return app ? app.name : appId.slice(0, 8);
  };

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return 'badge-danger';
      case 'high':
        return 'badge-warning';
      case 'medium':
        return 'badge-info';
      default:
        return 'badge-secondary';
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'running':
        return 'badge-success';
      case 'completed':
        return 'badge-primary';
      case 'stopped':
        return 'badge-danger';
      case 'failed':
        return 'badge-danger';
      default:
        return 'badge-secondary';
    }
  };

  const calculateProgressPercent = (current: number, total: number) => {
    if (total <= 0) return 0;
    return Math.min(100, Math.round((current / total) * 100));
  };

  /* ------------------------------------------------------------------ */
  /*  Render                                                            */
  /* ------------------------------------------------------------------ */

  return (
    <div className="page-container test-run-container animate-fade-in">
      {/* Top Header matching RouteBrokerPage standard */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            <Flame className="page-title-icon" /> Simulation Engine & Test Runs
          </h1>
          <p className="page-subtitle">
            Orchestrate live attack scenarios against customer workloads with real-time streaming,
            sub-5s Emergency Stop, and automated finding discovery.
          </p>
        </div>

        <div className="test-run-header-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchTestRuns}
            title="Refresh runs"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setIsLaunchModalOpen(true)}
            id="launch-test-run-btn"
          >
            <Play size={14} /> Launch Simulation Run
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger animate-fade-in">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button
            type="button"
            className="alert-close"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Stats Cards matching RouteBrokerPage */}
      <div className="test-run-stats">
        <div className="test-run-stat-card">
          <div className="test-run-stat-label">Total Test Runs</div>
          <div className="test-run-stat-value">{testRuns.length}</div>
        </div>

        <div className="test-run-stat-card active">
          <div className="test-run-stat-label">Active Running</div>
          <div className="test-run-stat-value" style={{ color: 'var(--primary)' }}>
            {activeRoutesCount}
          </div>
        </div>

        <div className="test-run-stat-card danger">
          <div className="test-run-stat-label">Findings Discovered</div>
          <div className="test-run-stat-value" style={{ color: 'var(--danger)' }}>
            {findingsCount}
          </div>
        </div>

        <div className="test-run-stat-card">
          <div className="test-run-stat-label">Completed Runs</div>
          <div className="test-run-stat-value" style={{ color: 'var(--foreground)' }}>
            {completedRunsCount}
          </div>
        </div>
      </div>

      {/* Active Run Live Panel */}
      {activeRun && (
        <div className="active-run-card animate-scale-up" id="active-run-panel">
          <div className="active-run-header">
            <div className="active-run-title-area">
              <div className="active-run-badge-row">
                {activeRun.status === 'running' && <span className="pulsing-indicator" />}
                <span className={`badge ${getStatusBadgeClass(activeRun.status)} uppercase`}>
                  {activeRun.status}
                </span>
                <span className="badge badge-secondary">{activeRun.scenario_category}</span>
                <span className="text-xs text-muted font-mono">ID: {activeRun.id.slice(0, 8)}</span>
              </div>
              <h2 className="active-run-title">{activeRun.scenario_name}</h2>
              <span className="active-run-subtitle">
                Target App: <strong>{getAppName(activeRun.app_id)}</strong>
              </span>
            </div>

            <div className="flex items-center gap-3">
              {activeRun.status === 'running' && (
                <button
                  type="button"
                  className="btn-emergency-stop"
                  onClick={handleEmergencyStop}
                  disabled={stopping}
                  id="emergency-stop-btn"
                >
                  <Square size={14} />
                  {stopping ? 'Stopping...' : 'EMERGENCY STOP (KILL SWITCH)'}
                </button>
              )}
              <button
                type="button"
                className="btn-close-monitor"
                onClick={() => setActiveRun(null)}
                title="Close Live Monitor View"
              >
                <X size={15} /> Close Monitor
              </button>
            </div>
          </div>

          {/* Progress Section */}
          <div className="run-progress-box">
            <div className="progress-labels">
              <span>
                Step {activeRun.current_step} of {activeRun.total_steps}:{' '}
                <strong style={{ color: '#00d4aa' }}>
                  {activeRun.current_step_name || 'In progress'}
                </strong>
              </span>
              <span>
                {calculateProgressPercent(activeRun.current_step, activeRun.total_steps)}%
              </span>
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${calculateProgressPercent(activeRun.current_step, activeRun.total_steps)}%`,
                }}
              />
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="run-metrics-grid">
            <div className="metric-pill">
              <div className="metric-pill-val">{activeRun.metrics?.requests_sent || 0}</div>
              <div className="metric-pill-label">Requests Sent</div>
            </div>
            <div className="metric-pill">
              <div className="metric-pill-val" style={{ color: '#10b981' }}>
                {activeRun.metrics?.successful_requests || 0}
              </div>
              <div className="metric-pill-label">Successful (&lt;400)</div>
            </div>
            <div className="metric-pill">
              <div className="metric-pill-val" style={{ color: '#f59e0b' }}>
                {activeRun.metrics?.blocked_requests || 0}
              </div>
              <div className="metric-pill-label">Defended / Blocked</div>
            </div>
            <div className="metric-pill">
              <div className="metric-pill-val" style={{ color: '#3b82f6' }}>
                {activeRun.metrics?.avg_latency_ms || 0} ms
              </div>
              <div className="metric-pill-label">Avg Latency</div>
            </div>
            <div className="metric-pill">
              <div className="metric-pill-val">{activeRun.metrics?.target_rps || 0}</div>
              <div className="metric-pill-label">Target RPS</div>
            </div>
            <div className="metric-pill">
              <div className="metric-pill-val" style={{ color: '#ef4444' }}>
                {activeRun.findings?.length || 0}
              </div>
              <div className="metric-pill-label">Findings</div>
            </div>
          </div>

          {/* Live Terminal Stream */}
          <div className="terminal-window">
            <div className="terminal-header">
              <div className="flex items-center gap-3">
                <div className="terminal-dots">
                  <span className="terminal-dot dot-red" />
                  <span className="terminal-dot dot-yellow" />
                  <span className="terminal-dot dot-green" />
                </div>
                <span>
                  <Terminal size={12} className="inline mr-1" />
                  Live Simulation Log Stream
                </span>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                />
                Auto-scroll
              </label>
            </div>
            <div className="terminal-body" ref={terminalBodyRef}>
              {activeRun.logs && activeRun.logs.length > 0 ? (
                activeRun.logs.map((log, idx) => (
                  <div key={idx} className="log-line">
                    <span className="log-ts">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    <span className={`log-level level-${log.level.toLowerCase()}`}>
                      [{log.level}]
                    </span>
                    <span className="log-msg">{log.message}</span>
                  </div>
                ))
              ) : (
                <div className="text-muted italic">Waiting for execution stream...</div>
              )}
            </div>
          </div>

          {/* Findings Discovered */}
          {activeRun.findings && activeRun.findings.length > 0 && (
            <div className="findings-section">
              <h3
                className="text-md font-bold flex items-center gap-2"
                style={{ color: '#ef4444' }}
              >
                <ShieldAlert size={18} />
                Identified Security Findings ({activeRun.findings.length})
              </h3>
              {activeRun.findings.map((finding) => (
                <div key={finding.id} className="finding-card">
                  <div className="finding-card-header">
                    <div className="finding-title">{finding.title}</div>
                    <div className="finding-badges">
                      <span
                        className={`badge ${getSeverityBadgeClass(finding.severity)} uppercase`}
                      >
                        {finding.severity}
                      </span>
                      {finding.cwe_id && (
                        <span className="badge badge-secondary font-mono">{finding.cwe_id}</span>
                      )}
                    </div>
                  </div>
                  <div className="finding-desc">{finding.description}</div>
                  {finding.remediation_guidance && (
                    <div className="finding-remediation">
                      <strong>Remediation:</strong> {finding.remediation_guidance}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Filter Tabs matching RouteBrokerPage */}
      <div className="test-run-filter-tabs">
        <button
          type="button"
          className={`test-run-filter-tab ${statusFilter === 'all' ? 'active' : ''}`}
          onClick={() => setStatusFilter('all')}
        >
          All Runs <span className="count">{testRuns.length}</span>
        </button>
        <button
          type="button"
          className={`test-run-filter-tab ${statusFilter === 'running' ? 'active' : ''}`}
          onClick={() => setStatusFilter('running')}
        >
          Running <span className="count">{activeRoutesCount}</span>
        </button>
        <button
          type="button"
          className={`test-run-filter-tab ${statusFilter === 'completed' ? 'active' : ''}`}
          onClick={() => setStatusFilter('completed')}
        >
          Completed <span className="count">{completedRunsCount}</span>
        </button>
        <button
          type="button"
          className={`test-run-filter-tab ${statusFilter === 'stopped' ? 'active' : ''}`}
          onClick={() => setStatusFilter('stopped')}
        >
          Stopped <span className="count">{stoppedRunsCount}</span>
        </button>
        <button
          type="button"
          className={`test-run-filter-tab ${statusFilter === 'failed' ? 'active' : ''}`}
          onClick={() => setStatusFilter('failed')}
        >
          Failed <span className="count">{failedRunsCount}</span>
        </button>
      </div>

      {/* Test Run History Section */}
      <div className="runs-card">
        <div className="runs-table-container">
          {loading ? (
            <div className="p-8 text-center text-muted">Loading test runs...</div>
          ) : filteredRuns.length === 0 ? (
            <div className="empty-runs-message">No test runs match the selected filter.</div>
          ) : (
            <table className="runs-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Scenario</th>
                  <th>Target App</th>
                  <th>Progress</th>
                  <th>Findings</th>
                  <th>Started At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRuns.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <span className={`badge ${getStatusBadgeClass(run.status)} capitalize`}>
                        {run.status}
                      </span>
                    </td>
                    <td>
                      <strong>{run.scenario_name}</strong>
                      <div className="text-xs text-muted font-mono">{run.scenario_category}</div>
                    </td>
                    <td>{getAppName(run.app_id)}</td>
                    <td>
                      <span className="font-mono text-xs">
                        {run.current_step} / {run.total_steps}
                      </span>
                    </td>
                    <td>
                      {run.findings && run.findings.length > 0 ? (
                        <span className="badge badge-danger font-bold">{run.findings.length}</span>
                      ) : (
                        <span className="text-xs text-muted">0</span>
                      )}
                    </td>
                    <td className="text-xs font-mono">
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn-inspect"
                        onClick={() => setActiveRun(run)}
                      >
                        Inspect View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Launch Test Run Modal */}
      {isLaunchModalOpen && (
        <div className="modal-backdrop animate-fade-in" onClick={() => setIsLaunchModalOpen(false)}>
          <div
            className="modal-card animate-scale-up"
            style={{ maxWidth: '580px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div className="flex items-center gap-2">
                <Flame size={20} color="#00d4aa" />
                <h2 className="modal-title font-display">Launch Attack Simulation</h2>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setIsLaunchModalOpen(false)}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleLaunchRun} className="modal-body">
              {/* App Select */}
              <div className="form-group">
                <label htmlFor="app-select">Target Deployed Application</label>
                <select
                  id="app-select"
                  required
                  value={selectedAppId}
                  onChange={(e) => setSelectedAppId(e.target.value)}
                >
                  <option value="" disabled>
                    Select target application...
                  </option>
                  {apps.map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.name} ({app.status} — Port:{' '}
                      {app.target_profile?.exposed_ports?.[0] || 8085})
                    </option>
                  ))}
                </select>
              </div>

              {/* Scenario Select */}
              <div className="form-group">
                <label htmlFor="scenario-select">Attack Simulation Scenario</label>
                <select
                  id="scenario-select"
                  value={selectedScenarioId}
                  onChange={(e) => setSelectedScenarioId(e.target.value)}
                >
                  <option value="">Select pre-configured scenario...</option>
                  {scenarios.map((scen) => (
                    <option key={scen.id} value={scen.id}>
                      {scen.name} ({scen.category})
                    </option>
                  ))}
                </select>
              </div>

              {/* Rate per Second */}
              <div className="form-group">
                <label htmlFor="rate-input">Probe Concurrency / Rate (RPS)</label>
                <input
                  id="rate-input"
                  type="number"
                  min="1"
                  max="1000"
                  value={ratePerSecond}
                  onChange={(e) => setRatePerSecond(Number(e.target.value))}
                />
              </div>

              {/* Simulation Guard Pre-check Indicator */}
              <div className="modal-safety-notice">
                <Shield size={20} color="#00d4aa" style={{ flexShrink: 0, marginTop: '2px' }} />
                <span>
                  <strong>Simulation Guard Pre-Check:</strong> Target will be dynamically validated
                  against Safety Policies (PRD §7.6) and destination-locked before execution.
                </span>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsLaunchModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={launching || !selectedAppId}
                  id="confirm-launch-btn"
                >
                  {launching ? 'Launching...' : 'Start Simulation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
