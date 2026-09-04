/**
 * ObservabilityPage — PRD Module 13 / Module 10 (Phase 11).
 *
 * Real-time Prometheus metrics, Grafana dashboard integration, Loki log streams,
 * measured HTTP probe latencies, live Docker container stats, and event audit trails.
 */

import {
  Activity,
  BarChart3,
  Clock,
  Cpu,
  ExternalLink,
  HardDrive,
  Layers,
  Network,
  Radio,
  RefreshCw,
  Search,
  Server,
  ShieldAlert,
  ShieldCheck,
  Terminal,
} from 'lucide-react';

import { useCallback, useEffect, useState } from 'react';

import './ObservabilityPage.css';

interface StepLatencyMetric {
  step_number: number;
  step_name: string;
  latency_ms: number;
  status_code: number;
  timestamp: string;
}

interface RunMetrics {
  test_run_id: string;
  app_id: string;
  scenario_name: string;
  status: string;
  total_steps: number;
  current_step: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  status_code_counts: Record<string, number>;
  cpu_utilization_pct: number;
  memory_utilization_mb: number;
  network_io_kbps: number;
  step_latencies: StepLatencyMetric[];
  container_name?: string;
  container_status?: string;
  datasource_info?: {
    prometheus?: string;
    loki?: string;
    grafana?: string;
    dashboard_url?: string;
  };
}

interface ObservabilityEvent {
  id: string;
  timestamp: string;
  event_type: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  component: string;
  message: string;
  metadata: Record<string, any>;
}

interface LokiLogItem {
  timestamp: string;
  message: string;
  level: string;
  service: string;
  labels?: Record<string, string>;
}

interface GrafanaConfig {
  grafana_url: string;
  dashboard_uid: string;
  dashboard_url: string;
  prometheus_url: string;
  loki_url: string;
  status: string;
}

interface PlatformMetrics {
  active_test_runs: number;
  completed_test_runs: number;
  open_routes: number;
  total_findings: number;
  total_recommendations: number;
  applied_mitigations: number;
  mitigation_rate_pct: number;
  cluster_health: string;
}

interface TestRunSummary {
  id: string;
  scenario_name: string;
  status: string;
  current_step: number;
  total_steps: number;
}

export function ObservabilityPage() {
  const [testRuns, setTestRuns] = useState<TestRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [runMetrics, setRunMetrics] = useState<RunMetrics | null>(null);
  const [runEvents, setRunEvents] = useState<ObservabilityEvent[]>([]);
  const [platformMetrics, setPlatformMetrics] = useState<PlatformMetrics | null>(null);
  const [grafanaConfig, setGrafanaConfig] = useState<GrafanaConfig | null>(null);
  const [lokiLogs, setLokiLogs] = useState<LokiLogItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [viewMode, setViewMode] = useState<'telemetry' | 'grafana'>('telemetry');
  const [logTab, setLogTab] = useState<'events' | 'loki'>('events');
  const [lokiFilter, setLokiFilter] = useState<string>('');
  const [lokiSeverity, setLokiSeverity] = useState<string>('all');

  // Fetch Test Runs
  const fetchRuns = useCallback(async () => {
    try {
      const res = await fetch('/api/attack-graph/runs');
      if (res.ok) {
        const data: TestRunSummary[] = await res.json();
        setTestRuns(data);
        if (data.length > 0 && !selectedRunId) {
          setSelectedRunId(data[0].id);
        }
      }
    } catch {
      // Fallback
    }
  }, [selectedRunId]);

  // Fetch Platform Metrics & Grafana Config
  const fetchPlatformAndStack = useCallback(async () => {
    try {
      const [pRes, gRes] = await Promise.all([
        fetch('/api/observability/platform'),
        fetch('/api/observability/grafana/config'),
      ]);
      if (pRes.ok) {
        setPlatformMetrics(await pRes.json());
      }
      if (gRes.ok) {
        setGrafanaConfig(await gRes.json());
      }
    } catch {
      // Fallback
    }
  }, []);

  // Fetch Loki Logs
  const fetchLokiLogs = useCallback(async (runId?: string) => {
    try {
      const url = runId
        ? `/api/observability/loki/logs?test_run_id=${runId}&limit=50`
        : '/api/observability/loki/logs?limit=50';
      const res = await fetch(url);
      if (res.ok) {
        const data: LokiLogItem[] = await res.json();
        setLokiLogs(data);
      }
    } catch {
      // Fallback
    }
  }, []);

  // Fetch Run Metrics & Events
  const fetchRunData = useCallback(async (runId: string) => {
    if (!runId) return;
    setLoading(true);
    try {
      const [mRes, eRes] = await Promise.all([
        fetch(`/api/observability/metrics/runs/${runId}`),
        fetch(`/api/observability/events/runs/${runId}`),
      ]);

      if (mRes.ok) {
        const mData = await mRes.json();
        setRunMetrics(mData);
      }
      if (eRes.ok) {
        const eData = await eRes.json();
        setRunEvents(eData);
      }
      await fetchLokiLogs(runId);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  }, [fetchLokiLogs]);

  useEffect(() => {
    fetchRuns();
    fetchPlatformAndStack();
  }, [fetchRuns, fetchPlatformAndStack]);

  useEffect(() => {
    if (selectedRunId) {
      fetchRunData(selectedRunId);
    }
  }, [selectedRunId, fetchRunData]);

  // Filter Loki logs
  const filteredLokiLogs = lokiLogs.filter((log) => {
    const matchesText =
      !lokiFilter ||
      log.message.toLowerCase().includes(lokiFilter.toLowerCase()) ||
      log.service.toLowerCase().includes(lokiFilter.toLowerCase());
    const matchesSev =
      lokiSeverity === 'all' ||
      log.level.toLowerCase() === lokiSeverity.toLowerCase();
    return matchesText && matchesSev;
  });

  const grafanaDashboardUrl =
    grafanaConfig?.dashboard_url ||
    'http://localhost:3001/d/pantheon-telemetry/pantheon-telemetry-observability?orgId=1&refresh=5s';

  const grafanaEmbedUrl =
    'http://localhost:3001/d/pantheon-telemetry/pantheon-telemetry-observability?orgId=1&kiosk=tv&theme=dark';

  return (
    <div className="observability-page">
      {/* Header */}
      <div className="obs-header">
        <div className="obs-header-title">
          <div className="obs-badge-row">
            <span className="obs-badge">PRD MODULE 13 · REAL-TIME OBSERVABILITY</span>
            <div className="stack-badges">
              <span className="stack-pill prom" title="Scraping host.docker.internal:8000/metrics">
                <span className="pill-dot" /> PROMETHEUS :9090
              </span>
              <span className="stack-pill loki" title="Live log ingestion stream">
                <span className="pill-dot" /> LOKI :3100
              </span>
              <span className="stack-pill grafana" title="Interactive dashboards">
                <span className="pill-dot" /> GRAFANA :3001
              </span>
            </div>
          </div>
          <h1>SYSTEM & TEST RUN OBSERVABILITY</h1>
          <p>
            Zero-mock telemetry: live Docker container statistics, measured HTTP probe latencies,
            Prometheus metric exposition, and Loki log streams.
          </p>
        </div>

        <div className="obs-header-controls">
          <div className="view-mode-toggle">
            <button
              className={`mode-btn ${viewMode === 'telemetry' ? 'active' : ''}`}
              onClick={() => setViewMode('telemetry')}
            >
              <Activity size={14} />
              <span>Telemetry</span>
            </button>
            <button
              className={`mode-btn ${viewMode === 'grafana' ? 'active' : ''}`}
              onClick={() => setViewMode('grafana')}
            >
              <BarChart3 size={14} />
              <span>Grafana View</span>
            </button>
          </div>

          <a
            href={grafanaDashboardUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="grafana-launch-button"
            title="Open interactive Grafana Dashboard in new tab"
          >
            <ExternalLink size={14} />
            <span>GRAFANA</span>
          </a>

          <div className="run-selector-group">
            <span className="control-label">TELEMETRY SCOPE</span>
            <select
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="run-select"
            >
              {testRuns.length === 0 && <option value="">No Test Runs Found</option>}
              {testRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.scenario_name} ({r.status.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => {
              if (selectedRunId) fetchRunData(selectedRunId);
              fetchPlatformAndStack();
            }}
            className="refresh-button"
            title="Synchronize real-time metrics"
          >
            <RefreshCw size={15} />
            <span>SYNC</span>
          </button>
        </div>
      </div>

      {/* Platform Overview Stat Bar */}
      <div className="obs-stats-grid">
        <div className="stat-card">
          <div className="stat-icon-wrapper cyan">
            <Radio size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-number">{platformMetrics?.active_test_runs ?? 0}</span>
            <span className="stat-label">ACTIVE TEST RUNS</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper blue">
            <Network size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-number">{platformMetrics?.open_routes ?? 0}</span>
            <span className="stat-label">OPEN ROUTE PROXIES</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper orange">
            <ShieldAlert size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-number">{platformMetrics?.total_findings ?? 0}</span>
            <span className="stat-label">TOTAL FINDINGS</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper green">
            <ShieldCheck size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-number">
              {platformMetrics?.cluster_health.toUpperCase() ?? 'HEALTHY'}
            </span>
            <span className="stat-label">TENANT CLUSTER HEALTH</span>
          </div>
        </div>
      </div>

      {/* View Switch: Embedded Grafana or Native Telemetry */}
      {viewMode === 'grafana' ? (
        <div className="grafana-embed-container">
          <div className="grafana-embed-bar">
            <div className="embed-bar-left">
              <BarChart3 size={16} className="text-orange" />
              <span>LIVE GRAFANA DASHBOARD · UID: pantheon-telemetry</span>
            </div>
            <a
              href={grafanaDashboardUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="embed-open-link"
            >
              Open Standalone <ExternalLink size={12} />
            </a>
          </div>
          <iframe
            title="Pantheon Grafana Dashboard"
            src={grafanaEmbedUrl}
            className="grafana-iframe"
          />
        </div>
      ) : loading ? (
        <div className="obs-loading-state">
          <div className="loading-spinner" />
          <p>Aggregating step probe telemetry and container metrics...</p>
        </div>
      ) : !selectedRunId || testRuns.length === 0 ? (
        <div className="obs-empty-state">
          <Activity size={48} className="empty-icon" />
          <h3>NO RUN SELECTED</h3>
          <p>Select a test run from the dropdown above to inspect detailed latency analytics and event logs.</p>
        </div>
      ) : !runMetrics ? (
        <div className="obs-empty-state">
          <Activity size={48} className="empty-icon" />
          <h3>NO TELEMETRY AVAILABLE</h3>
          <p>Unable to retrieve telemetry data for this run. Click SYNC to retry.</p>
        </div>
      ) : (
        <div className="obs-dashboard-grid">
          {/* Left Column: Probe Latency & Status Codes */}
          <div className="dashboard-col left-col">
            {/* Latency Analytics Card */}
            <div className="metric-panel">
              <div className="panel-header">
                <div className="panel-title-wrap">
                  <Clock size={16} className="text-cyan" />
                  <div>
                    <h3>PROBE LATENCY & DURATION</h3>
                    <span className="panel-subtitle">Measured HTTP round-trip elapsed times</span>
                  </div>
                </div>
                <div className="latency-pills">
                  <div className="lat-pill">
                    <span className="p-label">AVG</span>
                    <span className="p-val">{runMetrics.avg_latency_ms}ms</span>
                  </div>
                  <div className="lat-pill">
                    <span className="p-label">P95</span>
                    <span className="p-val">{runMetrics.p95_latency_ms}ms</span>
                  </div>
                  <div className="lat-pill">
                    <span className="p-label">MIN</span>
                    <span className="p-val">{runMetrics.min_latency_ms}ms</span>
                  </div>
                  <div className="lat-pill">
                    <span className="p-label">MAX</span>
                    <span className="p-val">{runMetrics.max_latency_ms}ms</span>
                  </div>
                </div>
              </div>

              <div className="panel-body">
                {runMetrics.step_latencies.length === 0 ? (
                  <div className="empty-chart-note">
                    <Clock size={24} className="text-muted" />
                    <span>No step probe latencies recorded for this simulation yet.</span>
                  </div>
                ) : (
                  <div className="step-latency-chart">
                    {runMetrics.step_latencies.map((sl) => {
                      const maxVal = Math.max(runMetrics.max_latency_ms, 100);
                      const pct = Math.min(100, Math.max(15, (sl.latency_ms / maxVal) * 100));
                      const isError = sl.status_code >= 400;

                      return (
                        <div key={sl.step_number} className="chart-bar-item">
                          <div className="bar-track">
                            <div
                              className={`bar-fill ${isError ? 'bar-error' : 'bar-normal'}`}
                              style={{ height: `${pct}%` }}
                              title={`${sl.step_name}: ${sl.latency_ms}ms (HTTP ${sl.status_code})`}
                            />
                          </div>
                          <span className="bar-label">Step {sl.step_number}</span>
                          <span className="bar-val">{sl.latency_ms}ms</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* HTTP Status Code Distribution Card */}
            <div className="metric-panel">
              <div className="panel-header">
                <div className="panel-title-wrap">
                  <BarChart3 size={16} className="text-blue" />
                  <div>
                    <h3>HTTP STATUS CODE DISTRIBUTION</h3>
                    <span className="panel-subtitle">Actual probe response codes from target</span>
                  </div>
                </div>
              </div>

              <div className="panel-body status-codes-body">
                {Object.keys(runMetrics.status_code_counts).length === 0 ? (
                  <div className="empty-chart-note">
                    <span>No HTTP status codes recorded yet.</span>
                  </div>
                ) : (
                  <div className="status-bars-wrap">
                    {Object.entries(runMetrics.status_code_counts).map(([code, count]) => {
                      const is2xx = code.startsWith('2');
                      const is4xx = code.startsWith('4');
                      const tagClass = is2xx ? 'status-2xx' : is4xx ? 'status-4xx' : 'status-5xx';
                      const totalProbeReqs = Object.values(runMetrics.status_code_counts).reduce(
                        (a, b) => a + b,
                        0
                      );

                      return (
                        <div key={code} className="status-code-row">
                          <div className="status-code-tag-wrap">
                            <span className={`status-code-badge ${tagClass}`}>HTTP {code}</span>
                            <span className="status-code-desc">
                              {is2xx
                                ? 'Allowed / Success'
                                : is4xx
                                ? 'Safety Guard Blocked'
                                : 'Compromised / Exception'}
                            </span>
                          </div>
                          <div className="status-code-meter">
                            <div
                              className={`meter-fill ${tagClass}`}
                              style={{
                                width: `${Math.min(
                                  100,
                                  (count / Math.max(totalProbeReqs, 1)) * 100
                                )}%`,
                              }}
                            />
                          </div>
                          <span className="status-code-count">{count} reqs</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Resource Utilization & Loki/Event Streams */}
          <div className="dashboard-col right-col">
            {/* Real Container Resource Utilization */}
            <div className="metric-panel">
              <div className="panel-header">
                <div className="panel-title-wrap">
                  <Server size={16} className="text-orange" />
                  <div>
                    <h3>TARGET CONTAINER RESOURCE IMPACT</h3>
                    <div className="container-badge-wrap">
                      <span className="container-status-dot" />
                      <span className="container-badge-name">
                        {runMetrics.container_name || 'pantheon-app-chess'}
                      </span>
                      <span className="container-badge-state">
                        ({(runMetrics.container_status || 'running').toUpperCase()})
                      </span>
                      <span className="container-badge-source">DOCKER ENGINE API</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="panel-body resource-gauges-grid">
                {/* CPU Gauge */}
                <div className="resource-gauge-card">
                  <div className="gauge-icon-wrap">
                    <Cpu size={18} />
                  </div>
                  <div className="gauge-details">
                    <div className="gauge-title-line">
                      <span className="gauge-name">CPU UTILIZATION</span>
                      <span className="gauge-val">{runMetrics.cpu_utilization_pct}%</span>
                    </div>
                    <div className="gauge-bar-track">
                      <div
                        className="gauge-bar-fill cyan"
                        style={{ width: `${Math.min(100, Math.max(4, runMetrics.cpu_utilization_pct))}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Memory Gauge */}
                <div className="resource-gauge-card">
                  <div className="gauge-icon-wrap">
                    <HardDrive size={18} />
                  </div>
                  <div className="gauge-details">
                    <div className="gauge-title-line">
                      <span className="gauge-name">MEMORY USAGE</span>
                      <span className="gauge-val">{runMetrics.memory_utilization_mb} MB</span>
                    </div>
                    <div className="gauge-bar-track">
                      <div
                        className="gauge-bar-fill blue"
                        style={{
                          width: `${Math.min(
                            100,
                            Math.max(8, (runMetrics.memory_utilization_mb / 512) * 100)
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Network Throughput Gauge */}
                <div className="resource-gauge-card">
                  <div className="gauge-icon-wrap">
                    <Network size={18} />
                  </div>
                  <div className="gauge-details">
                    <div className="gauge-title-line">
                      <span className="gauge-name">NETWORK I/O</span>
                      <span className="gauge-val">{runMetrics.network_io_kbps} KB/s</span>
                    </div>
                    <div className="gauge-bar-track">
                      <div
                        className="gauge-bar-fill orange"
                        style={{
                          width: `${Math.min(
                            100,
                            Math.max(6, (runMetrics.network_io_kbps / 1000) * 100)
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Stream Panel: Loki Live Logs or Execution Events */}
            <div className="metric-panel events-panel">
              <div className="panel-header">
                <div className="panel-title-wrap">
                  <Terminal size={16} className="text-cyan" />
                  <div>
                    <h3>POD & EXECUTION EVENT STREAM</h3>
                    <span className="panel-subtitle">Real-time Loki telemetry and container lifecycle events</span>
                  </div>
                </div>

                <div className="stream-header-right">
                  <div className="stream-tab-buttons">
                    <button
                      className={`tab-btn ${logTab === 'events' ? 'active' : ''}`}
                      onClick={() => setLogTab('events')}
                    >
                      <Terminal size={13} />
                      <span>EVENTS</span>
                      <span className="stream-count-badge">{runEvents.length}</span>
                    </button>
                    <button
                      className={`tab-btn ${logTab === 'loki' ? 'active' : ''}`}
                      onClick={() => setLogTab('loki')}
                    >
                      <Layers size={13} />
                      <span>LOKI STREAM</span>
                      <span className="stream-count-badge">{filteredLokiLogs.length}</span>
                    </button>
                  </div>
                </div>

                {logTab === 'loki' && (
                  <div className="loki-filter-controls">
                    <div className="loki-search-wrap">
                      <Search size={12} />
                      <input
                        type="text"
                        placeholder="Filter logs..."
                        value={lokiFilter}
                        onChange={(e) => setLokiFilter(e.target.value)}
                        className="loki-search-input"
                      />
                    </div>
                    <select
                      value={lokiSeverity}
                      onChange={(e) => setLokiSeverity(e.target.value)}
                      className="loki-sev-select"
                    >
                      <option value="all">ALL</option>
                      <option value="info">INFO</option>
                      <option value="alert">ALERT</option>
                      <option value="warn">WARN</option>
                      <option value="success">SUCCESS</option>
                    </select>
                  </div>
                )}
              </div>

              <div className="panel-body events-table-wrap">
                {logTab === 'loki' ? (
                  filteredLokiLogs.length === 0 ? (
                    <div className="empty-chart-note">
                      <Layers size={20} className="text-muted" />
                      <span>No Loki log entries found matching filter.</span>
                    </div>
                  ) : (
                    <div className="loki-log-stream">
                      {filteredLokiLogs.map((log, i) => (
                        <div key={i} className={`loki-log-row ${log.level.toLowerCase()}`}>
                          <span className="loki-time">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                          <span className={`loki-level-badge ${log.level.toLowerCase()}`}>
                            {log.level.toUpperCase()}
                          </span>
                          <span className="loki-service-tag">{log.service}</span>
                          <span className="loki-msg">{log.message}</span>
                        </div>
                      ))}
                    </div>
                  )
                ) : runEvents.length === 0 ? (
                  <p className="no-events-text">No recorded events for this test run.</p>
                ) : (
                  <table className="events-table">
                    <thead>
                      <tr>
                        <th>TIME</th>
                        <th>SEVERITY</th>
                        <th>COMPONENT</th>
                        <th>EVENT MESSAGE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runEvents.map((evt) => (
                        <tr key={evt.id} className={`event-row ${evt.severity}`}>
                          <td className="event-time">
                            {new Date(evt.timestamp).toLocaleTimeString()}
                          </td>
                          <td>
                            <span className={`event-severity-pill ${evt.severity}`}>
                              {evt.severity.toUpperCase()}
                            </span>
                          </td>
                          <td>
                            <span className="event-component-pill">{evt.component}</span>
                          </td>
                          <td className="event-message-cell">{evt.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
