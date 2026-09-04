/**
 * AppOnboardingPage — PRD Module 4 (Phase 4)
 *
 * Full app ingestion flow:
 * - Paste a Git URL or Docker Compose YAML to deploy
 * - View list of deployed apps with live status
 * - Stream real-time build logs via WebSocket
 * - Redeploy existing apps
 */

import {
  AlertCircle,
  Box,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  GitBranch,
  Loader2,
  Package,
  Play,
  RefreshCw,
  Square,
  Terminal,
  Trash2,
  Upload,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import './AppOnboardingPage.css';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AppRecord {
  id: string;
  org_id: string;
  name: string;
  source_type: 'git' | 'compose';
  source_url: string | null;
  status: 'queued' | 'building' | 'pushing' | 'deploying' | 'running' | 'stopped' | 'failed';
  discovery_status: string;
}

interface AppVersion {
  id: string;
  app_id: string;
  version_number: number;
  commit_hash: string | null;
  image_tag: string | null;
  detected_framework: string | null;
  build_logs: string | null;
}

/* ------------------------------------------------------------------ */
/*  API helpers (uses Vite proxy → /api → localhost:8000)               */
/* ------------------------------------------------------------------ */

const API_BASE = '/api';

async function apiGet<T>(path: string, token: string | null): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

async function apiPost<T>(path: string, body: unknown, token: string | null): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error ${res.status}`);
  }
  return res.json();
}

async function apiDelete<T>(path: string, token: string | null): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error ${res.status}`);
  }
  return res.json();
}

/* ------------------------------------------------------------------ */
/*  Status badge helper                                                */
/* ------------------------------------------------------------------ */

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    queued: { cls: 'badge-info', label: 'Queued' },
    building: { cls: 'badge-warning', label: 'Building' },
    pushing: { cls: 'badge-warning', label: 'Pushing' },
    deploying: { cls: 'badge-info', label: 'Deploying' },
    running: { cls: 'badge-success', label: 'Running' },
    stopped: { cls: 'badge-warning', label: 'Stopped' },
    failed: { cls: 'badge-danger', label: 'Failed' },
  };
  const { cls, label } = map[status] || { cls: 'badge-info', label: status };
  return <span className={`badge ${cls}`}>{label}</span>;
}

/* ------------------------------------------------------------------ */
/*  Build Log Panel (WebSocket streaming)                              */
/* ------------------------------------------------------------------ */

function BuildLogPanel({ appId, onClose }: { appId: string; onClose: () => void }) {
  const [lines, setLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket for live build logs (dynamically resolves host for LAN/network readiness)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl =
      import.meta.env.VITE_WS_URL ||
      `${protocol}//${window.location.host}/api/apps/${appId}/logs/ws`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onmessage = (event) => {
      setLines((prev) => [...prev, event.data]);
    };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    return () => {
      ws.close();
    };
  }, [appId]);

  // Auto-scroll to bottom
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  return (
    <div className="build-log-panel card animate-slide-in">
      <div
        className="card-header"
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Terminal size={14} />
          <span className="card-title">Build Logs</span>
          {connected ? (
            <span className="badge badge-success">● Live</span>
          ) : (
            <span className="badge badge-info">Disconnected</span>
          )}
        </div>
        <button className="log-close-btn" onClick={onClose} aria-label="Close logs">
          <X size={14} />
        </button>
      </div>
      <div className="build-log-content font-mono">
        {lines.length === 0 && <div className="log-empty">Waiting for build output...</div>}
        {lines.map((line, i) => (
          <div
            key={i}
            className={`log-line ${
              line.includes('===')
                ? 'log-step'
                : line.includes('ERROR') || line.includes('failed')
                  ? 'log-error'
                  : line.includes('WARNING')
                    ? 'log-warn'
                    : line.includes('successfully') || line.includes('complete')
                      ? 'log-success'
                      : ''
            }`}
          >
            {line}
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Version History Panel                                              */
/* ------------------------------------------------------------------ */

function VersionHistoryPanel({ appId, token }: { appId: string; token: string | null }) {
  const [versions, setVersions] = useState<AppVersion[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet<AppVersion[]>(`/apps/${appId}/versions`, token)
      .then(setVersions)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [appId, token]);

  if (loading)
    return <div style={{ color: 'var(--muted-foreground)', padding: 12 }}>Loading versions...</div>;
  if (versions.length === 0) return null;

  return (
    <div className="version-history">
      {versions.map((v) => (
        <div key={v.id} className="version-item">
          <button
            className="version-header"
            onClick={() => setExpanded(expanded === v.id ? null : v.id)}
          >
            {expanded === v.id ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <span className="font-mono" style={{ fontSize: 11 }}>
              v{v.version_number}
            </span>
            {v.detected_framework && (
              <span className="badge badge-info">{v.detected_framework}</span>
            )}
            {v.image_tag && (
              <span style={{ color: 'var(--muted-foreground)', fontSize: 10, marginLeft: 'auto' }}>
                {v.image_tag.split('/').pop()}
              </span>
            )}
          </button>
          {expanded === v.id && v.build_logs && (
            <div className="version-logs font-mono">
              {v.build_logs.split('\n').map((line, i) => (
                <div key={i} className="log-line">
                  {line}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Discovery Summary Inline (Phase 5)                                 */
/* ------------------------------------------------------------------ */

interface DiscoverySummary {
  discovery_status: string;
  language: string | null;
  framework: string | null;
  exposed_ports: number[];
  detected_db: string | null;
  endpoint_count: number;
  classification_counts: Record<string, number>;
}

function DiscoverySummaryInline({ appId, token }: { appId: string; token: string | null }) {
  const [summary, setSummary] = useState<DiscoverySummary | null>(null);

  useEffect(() => {
    apiGet<DiscoverySummary>(`/discovery/${appId}/summary`, token)
      .then(setSummary)
      .catch(() => {});
  }, [appId, token]);

  if (!summary || summary.discovery_status !== 'completed') return null;

  return (
    <div
      style={{
        padding: '12px 16px',
        borderTop: '1px solid var(--card-border)',
        background: 'rgba(0, 212, 170, 0.03)',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        flexWrap: 'wrap',
        fontSize: 11,
      }}
    >
      <span
        className="font-mono"
        style={{
          fontSize: 9,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--muted-foreground)',
        }}
      >
        Discovery:
      </span>
      {summary.language && <span className="badge badge-info">{summary.language}</span>}
      {summary.framework && <span className="badge badge-primary">{summary.framework}</span>}
      {summary.detected_db && <span className="badge badge-warning">{summary.detected_db}</span>}
      {summary.endpoint_count > 0 && (
        <span style={{ color: 'var(--secondary-foreground)' }}>
          {summary.endpoint_count} endpoint{summary.endpoint_count !== 1 ? 's' : ''}
        </span>
      )}
      <a
        href="/target-analysis"
        style={{
          marginLeft: 'auto',
          fontSize: 10,
          color: 'var(--primary)',
          fontFamily: 'var(--font-mono)',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}
      >
        View Full Profile →
      </a>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Live App Preview Modal                                             */
/* ------------------------------------------------------------------ */

function LivePreviewModal({ app, onClose }: { app: AppRecord; onClose: () => void }) {
  const [port, setPort] = useState(8085);
  const proxyUrl = `/api/apps/${app.id}/preview?target_port=${port}`;
  const [previewUrl, setPreviewUrl] = useState(proxyUrl);

  const handlePortChange = (newPort: number) => {
    setPort(newPort);
    setPreviewUrl(`/api/apps/${app.id}/preview?target_port=${newPort}`);
  };

  return (
    <div
      className="modal-backdrop animate-fade-in"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 7, 9, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        className="card shadow-2xl animate-scale-up"
        style={{
          width: '100%',
          maxWidth: '1100px',
          height: '85vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0b0f17',
          border: '1px solid rgba(0, 212, 170, 0.3)',
          borderRadius: '16px',
          overflow: 'hidden',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '14px 20px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            backgroundColor: '#07090d',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: '#00d4aa',
                boxShadow: '0 0 10px #00d4aa',
              }}
            />
            <span style={{ fontWeight: 700, fontSize: 16, color: '#ffffff' }}>
              Live App Preview: {app.name}
            </span>
            <span className="badge badge-success">Running</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <a
              href={`http://${window.location.hostname}:${port}`}
              target="_blank"
              rel="noreferrer"
              className="btn-secondary"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 14px',
                fontSize: 12,
                borderRadius: 8,
                textDecoration: 'none',
              }}
            >
              <ExternalLink size={14} /> Open Direct Window (Port {port})
            </a>
            <button className="log-close-btn" onClick={onClose} aria-label="Close modal">
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Browser Navigation Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '10px 20px',
            backgroundColor: '#0f141f',
            borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          }}
        >
          <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'monospace' }}>
            Port:
          </span>
          <select
            value={port}
            onChange={(e) => handlePortChange(Number(e.target.value))}
            style={{
              backgroundColor: '#07090d',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '8px',
              padding: '6px 10px',
              color: '#00d4aa',
              fontSize: '12px',
              fontFamily: 'monospace',
            }}
          >
            <option value={8085}>8085 (Default Tenant Port)</option>
            <option value={3000}>3000 (React / Next)</option>
            <option value={5000}>5000 (Flask / Python)</option>
            <option value={8000}>8000 (FastAPI)</option>
            <option value={8080}>8080 (Jenkins / Alt)</option>
          </select>
          <span style={{ fontSize: 11, color: 'var(--muted-foreground)', fontFamily: 'monospace' }}>
            Preview Proxy:
          </span>
          <input
            type="text"
            value={previewUrl}
            onChange={(e) => setPreviewUrl(e.target.value)}
            style={{
              flex: 1,
              backgroundColor: '#07090d',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '8px',
              padding: '6px 14px',
              color: '#00d4aa',
              fontSize: '13px',
              fontFamily: 'monospace',
            }}
          />
          <button
            className="btn-secondary"
            onClick={() => {
              const current = previewUrl;
              setPreviewUrl('');
              setTimeout(() => setPreviewUrl(current), 50);
            }}
            style={{ padding: '6px 12px', fontSize: 12 }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        {/* Live Frame / Canvas */}
        <div style={{ flex: 1, position: 'relative', backgroundColor: '#ffffff' }}>
          {previewUrl ? (
            <iframe
              src={previewUrl}
              title={`Preview ${app.name}`}
              style={{ width: '100%', height: '100%', border: 'none' }}
            />
          ) : (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#666',
              }}
            >
              Loading preview frame...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page Component                                                */
/* ------------------------------------------------------------------ */

export function AppOnboardingPage() {
  // Form state
  const [mode, setMode] = useState<'git' | 'compose'>('git');
  const [appName, setAppName] = useState('');
  const [gitUrl, setGitUrl] = useState('');
  const [composeYaml, setComposeYaml] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // App list state
  const [apps, setApps] = useState<AppRecord[]>([]);
  const [loadingApps, setLoadingApps] = useState(true);
  const [selectedLogApp, setSelectedLogApp] = useState<string | null>(null);
  const [selectedPreviewApp, setSelectedPreviewApp] = useState<AppRecord | null>(null);
  const [expandedApp, setExpandedApp] = useState<string | null>(null);

  // Auth — for now use a simple token from localStorage (set after login)
  const [token] = useState<string | null>(() =>
    typeof localStorage !== 'undefined' && typeof localStorage.getItem === 'function'
      ? localStorage.getItem('pantheon_token')
      : null,
  );

  // Fetch apps list
  const fetchApps = useCallback(() => {
    apiGet<AppRecord[]>('/apps', token)
      .then(setApps)
      .catch(() => {})
      .finally(() => setLoadingApps(false));
  }, [token]);

  useEffect(() => {
    fetchApps();
    // Poll for status updates every 5s
    const interval = setInterval(fetchApps, 5000);
    return () => clearInterval(interval);
  }, [fetchApps]);

  // Submit handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (!appName.trim()) {
      setError('App name is required');
      return;
    }

    if (mode === 'git' && !gitUrl.trim()) {
      setError('Git repository URL is required');
      return;
    }

    if (mode === 'compose' && !composeYaml.trim()) {
      setError('Docker Compose YAML is required');
      return;
    }

    setSubmitting(true);

    try {
      let result: AppRecord;

      if (mode === 'git') {
        result = await apiPost<AppRecord>(
          '/apps/ingest/git',
          {
            name: appName.trim(),
            git_url: gitUrl.trim(),
          },
          token,
        );
      } else {
        result = await apiPost<AppRecord>(
          '/apps/ingest/compose',
          {
            name: appName.trim(),
            compose_yaml: composeYaml.trim(),
          },
          token,
        );
      }

      setSuccessMsg(`App "${result.name}" submitted for ingestion!`);
      setAppName('');
      setGitUrl('');
      setComposeYaml('');
      setSelectedLogApp(result.id);
      fetchApps();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit app');
    } finally {
      setSubmitting(false);
    }
  };

  // Redeploy handler
  const handleRedeploy = async (appId: string) => {
    try {
      await apiPost<AppRecord>(`/apps/${appId}/redeploy`, {}, token);
      setSelectedLogApp(appId);
      fetchApps();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Redeploy failed');
    }
  };

  // Action loading state (tracks start/stop/delete per app)
  const [actionLoading, setActionLoading] = useState<Record<string, string>>({});

  // Start app container handler
  const handleStartApp = async (appId: string) => {
    setActionLoading((prev) => ({ ...prev, [appId]: 'start' }));
    setError(null);
    try {
      await apiPost<AppRecord>(`/apps/${appId}/start`, {}, token);
      setSuccessMsg('Application container started successfully!');
      fetchApps();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start app');
    } finally {
      setActionLoading((prev) => {
        const copy = { ...prev };
        delete copy[appId];
        return copy;
      });
    }
  };

  // Stop app container handler
  const handleStopApp = async (appId: string) => {
    setActionLoading((prev) => ({ ...prev, [appId]: 'stop' }));
    setError(null);
    try {
      await apiPost<AppRecord>(`/apps/${appId}/stop`, {}, token);
      setSuccessMsg('Application container stopped.');
      fetchApps();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to stop app');
    } finally {
      setActionLoading((prev) => {
        const copy = { ...prev };
        delete copy[appId];
        return copy;
      });
    }
  };

  // Delete app handler (removes app and all container/build records)
  const handleDeleteApp = async (app: AppRecord) => {
    if (
      !window.confirm(
        `Are you sure you want to remove application "${app.name}"? This will delete build history and container resources.`,
      )
    ) {
      return;
    }

    setActionLoading((prev) => ({ ...prev, [app.id]: 'delete' }));
    setError(null);
    try {
      await apiDelete(`/apps/${app.id}`, token);
      setApps((prev) => prev.filter((a) => a.id !== app.id));
      setSuccessMsg(`Application "${app.name}" removed successfully.`);
      if (selectedLogApp === app.id) setSelectedLogApp(null);
      if (selectedPreviewApp?.id === app.id) setSelectedPreviewApp(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete app');
    } finally {
      setActionLoading((prev) => {
        const copy = { ...prev };
        delete copy[app.id];
        return copy;
      });
    }
  };

  return (
    <div className="page-container animate-fade-in">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">App Onboarding</h1>
        <p className="page-subtitle">
          Deploy your application from a Git repository or Docker Compose file. The ingestion
          pipeline will clone, build, scan, and deploy to your tenant namespace.
        </p>
      </div>

      <div className="onboarding-grid">
        {/* ---- Left: Ingestion Form ---- */}
        <div className="onboarding-form-section">
          <div className="card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Upload size={14} />
                <span className="card-title">Import Application</span>
              </div>
            </div>
            <div className="card-body">
              {/* Mode Toggle */}
              <div className="mode-toggle">
                <button
                  className={`mode-btn ${mode === 'git' ? 'mode-active' : ''}`}
                  onClick={() => setMode('git')}
                  type="button"
                >
                  <GitBranch size={14} />
                  Git Repository
                </button>
                <button
                  className={`mode-btn ${mode === 'compose' ? 'mode-active' : ''}`}
                  onClick={() => setMode('compose')}
                  type="button"
                >
                  <Package size={14} />
                  Docker Compose
                </button>
              </div>

              <form onSubmit={handleSubmit}>
                {/* App Name */}
                <div className="form-group">
                  <label className="form-label" htmlFor="app-name">
                    Application Name
                  </label>
                  <input
                    id="app-name"
                    type="text"
                    className="input"
                    placeholder="my-awesome-app"
                    value={appName}
                    onChange={(e) => setAppName(e.target.value)}
                    disabled={submitting}
                  />
                </div>

                {/* Git URL Input */}
                {mode === 'git' && (
                  <div className="form-group">
                    <label className="form-label" htmlFor="git-url">
                      Git Repository URL
                    </label>
                    <input
                      id="git-url"
                      type="url"
                      className="input"
                      placeholder="https://github.com/username/repo.git"
                      value={gitUrl}
                      onChange={(e) => setGitUrl(e.target.value)}
                      disabled={submitting}
                    />
                    <p className="form-hint">
                      Public repos only for now. Paste the full HTTPS clone URL.
                    </p>
                  </div>
                )}

                {/* Compose YAML Input */}
                {mode === 'compose' && (
                  <div className="form-group">
                    <label className="form-label" htmlFor="compose-yaml">
                      Docker Compose YAML
                    </label>
                    <textarea
                      id="compose-yaml"
                      className="input compose-textarea font-mono"
                      placeholder={`version: '3.8'\nservices:\n  web:\n    image: nginx:alpine\n    ports:\n      - "80:80"`}
                      value={composeYaml}
                      onChange={(e) => setComposeYaml(e.target.value)}
                      disabled={submitting}
                      rows={10}
                    />
                  </div>
                )}

                {/* Error / Success Messages */}
                {error && (
                  <div className="form-message form-error animate-fade-in">
                    <AlertCircle size={14} />
                    {error}
                  </div>
                )}
                {successMsg && (
                  <div className="form-message form-success animate-fade-in">
                    <CheckCircle2 size={14} />
                    {successMsg}
                  </div>
                )}

                {/* Submit Button */}
                <button type="submit" className="btn-primary submit-btn" disabled={submitting}>
                  {submitting ? (
                    <>
                      <Loader2 size={14} className="spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Play size={14} />
                      Start Ingestion
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Pipeline Overview */}
          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-body">
              <div className="pipeline-steps">
                <div className="pipeline-step">
                  <div className="step-number">1</div>
                  <div>
                    <div className="step-title">Clone</div>
                    <div className="step-desc">Shallow git clone (depth=1)</div>
                  </div>
                </div>
                <div className="pipeline-step">
                  <div className="step-number">2</div>
                  <div>
                    <div className="step-title">Build</div>
                    <div className="step-desc">Docker BuildKit or Buildpacks</div>
                  </div>
                </div>
                <div className="pipeline-step">
                  <div className="step-number">3</div>
                  <div>
                    <div className="step-title">Scan</div>
                    <div className="step-desc">Trivy vulnerability analysis</div>
                  </div>
                </div>
                <div className="pipeline-step">
                  <div className="step-number">4</div>
                  <div>
                    <div className="step-title">Push</div>
                    <div className="step-desc">Registry → MinIO S3 storage</div>
                  </div>
                </div>
                <div className="pipeline-step">
                  <div className="step-number">5</div>
                  <div>
                    <div className="step-title">Deploy</div>
                    <div className="step-desc">K8s Deployment + Service + Secret</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ---- Right: App List + Logs ---- */}
        <div className="onboarding-list-section">
          {/* App List */}
          <div className="card">
            <div
              className="card-header"
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Box size={14} />
                <span className="card-title">Deployed Applications</span>
                <span className="badge badge-primary">{apps.length}</span>
              </div>
              <button className="btn-secondary" onClick={fetchApps} style={{ padding: '4px 10px' }}>
                <RefreshCw size={12} />
              </button>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              {loadingApps && apps.length === 0 ? (
                <div className="app-list-empty">
                  <Loader2 size={20} className="spin" style={{ opacity: 0.4 }} />
                  <span>Loading apps...</span>
                </div>
              ) : apps.length === 0 ? (
                <div className="app-list-empty">
                  <Box size={32} style={{ opacity: 0.2 }} />
                  <span style={{ color: 'var(--muted-foreground)' }}>
                    No apps deployed yet. Import your first app above!
                  </span>
                </div>
              ) : (
                <div className="app-list">
                  {apps.map((app) => (
                    <div key={app.id} className="app-item">
                      <div className="app-item-header">
                        <div className="app-item-info">
                          <button
                            className="app-expand-btn"
                            onClick={() => setExpandedApp(expandedApp === app.id ? null : app.id)}
                          >
                            {expandedApp === app.id ? (
                              <ChevronDown size={12} />
                            ) : (
                              <ChevronRight size={12} />
                            )}
                          </button>
                          <div className="app-item-icon">
                            {app.source_type === 'git' ? (
                              <GitBranch size={14} />
                            ) : (
                              <Package size={14} />
                            )}
                          </div>
                          <div>
                            <div className="app-item-name">{app.name}</div>
                            {app.source_url && (
                              <div className="app-item-url font-mono">{app.source_url}</div>
                            )}
                          </div>
                        </div>
                        <div className="app-item-actions">
                          <StatusBadge status={app.status} />
                          {(app.status === 'building' ||
                            app.status === 'pushing' ||
                            app.status === 'deploying' ||
                            app.status === 'queued') && (
                            <Loader2
                              size={14}
                              className="spin"
                              style={{ color: 'var(--warning)' }}
                            />
                          )}

                          {/* Start button: for stopped apps or reopening system */}
                          {app.status === 'stopped' && (
                            <button
                              type="button"
                              className="btn-start-app"
                              onClick={() => handleStartApp(app.id)}
                              disabled={actionLoading[app.id] === 'start'}
                              title="Start application container"
                              data-testid={`start-app-btn-${app.id}`}
                            >
                              {actionLoading[app.id] === 'start' ? (
                                <Loader2 size={12} className="spin" />
                              ) : (
                                <Play size={12} />
                              )}
                              Start App
                            </button>
                          )}

                          {/* Live Preview and Stop button for running apps */}
                          {app.status === 'running' && (
                            <>
                              <button
                                type="button"
                                className="mode-btn mode-active"
                                onClick={() => setSelectedPreviewApp(app)}
                                title="View Live App Preview"
                                style={{
                                  padding: '3px 10px',
                                  fontSize: 11,
                                  textTransform: 'none',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 4,
                                }}
                              >
                                <ExternalLink size={12} />
                                Live Preview
                              </button>

                              <button
                                type="button"
                                className="btn-stop-app"
                                onClick={() => handleStopApp(app.id)}
                                disabled={actionLoading[app.id] === 'stop'}
                                title="Stop application container"
                                data-testid={`stop-app-btn-${app.id}`}
                              >
                                {actionLoading[app.id] === 'stop' ? (
                                  <Loader2 size={12} className="spin" />
                                ) : (
                                  <Square size={11} />
                                )}
                                Stop
                              </button>
                            </>
                          )}

                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() =>
                              setSelectedLogApp(selectedLogApp === app.id ? null : app.id)
                            }
                            title="View build logs"
                            style={{ padding: '3px 8px', fontSize: 10 }}
                          >
                            <Terminal size={12} />
                          </button>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => handleRedeploy(app.id)}
                            title="Redeploy"
                            style={{ padding: '3px 8px', fontSize: 10 }}
                          >
                            <RefreshCw size={12} />
                          </button>

                          {/* Delete button: removes failed or unwanted apps */}
                          <button
                            type="button"
                            className="btn-delete-app"
                            onClick={() => handleDeleteApp(app)}
                            disabled={actionLoading[app.id] === 'delete'}
                            title="Remove application ingestion"
                            data-testid={`delete-app-btn-${app.id}`}
                          >
                            {actionLoading[app.id] === 'delete' ? (
                              <Loader2 size={12} className="spin" />
                            ) : (
                              <Trash2 size={13} />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Version History (expanded) */}
                      {expandedApp === app.id && (
                        <>
                          <VersionHistoryPanel appId={app.id} token={token} />
                          {/* Phase 5 — Compact Discovery Summary */}
                          {app.discovery_status === 'completed' && (
                            <DiscoverySummaryInline appId={app.id} token={token} />
                          )}
                          {app.discovery_status === 'running' && (
                            <div
                              style={{
                                padding: '10px 16px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 8,
                                fontSize: 11,
                                color: 'var(--warning)',
                                fontFamily: 'var(--font-mono)',
                              }}
                            >
                              <Loader2 size={12} className="spin" />
                              Discovery running — analyzing application...
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Live Build Logs */}
          {selectedLogApp && (
            <BuildLogPanel appId={selectedLogApp} onClose={() => setSelectedLogApp(null)} />
          )}
        </div>
      </div>

      {/* Live App Preview Modal */}
      {selectedPreviewApp && (
        <LivePreviewModal app={selectedPreviewApp} onClose={() => setSelectedPreviewApp(null)} />
      )}
    </div>
  );
}
