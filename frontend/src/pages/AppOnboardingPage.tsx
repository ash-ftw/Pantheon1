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
  Database,
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

interface StorageRepository {
  repository: string;
  name: string;
  clean_app_name: string;
  org_id: string;
  tags: string[];
  size_human: string;
  object_count: number;
  is_orphaned: boolean;
  bucket: string;
  minio_path: string;
}

interface RegistryStorageResponse {
  bucket: string;
  total_repositories: number;
  orphaned_count: number;
  repositories: StorageRepository[];
}

interface AppRecord {
  id: string;
  org_id: string;
  name: string;
  source_type: 'git' | 'compose';
  source_url: string | null;
  status: 'queued' | 'building' | 'pushing' | 'deploying' | 'running' | 'stopped' | 'failed';
  discovery_status: string;
  target_profile?: {
    host_port?: number;
    exposed_ports?: Array<{ container_port: number; host_port: number } | number>;
    [key: string]: any;
  } | null;
  discovered_endpoints?: Record<string, any> | null;
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
  // Use the dynamically assigned host_port from target_profile (set by the backend port allocator)
  const assignedPort = app.target_profile?.host_port;
  const defaultPort = assignedPort || 8085;
  const [port, setPort] = useState(defaultPort);
  const proxyUrl = `/api/apps/${app.id}/preview?target_port=${defaultPort}`;
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
                backgroundColor: 'var(--primary)',
                boxShadow: '0 0 10px var(--primary)',
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
              color: 'var(--primary)',
              fontSize: '12px',
              fontFamily: 'monospace',
            }}
          >
            {assignedPort && assignedPort !== 8085 && (
              <option value={assignedPort}>{assignedPort} (Assigned Port)</option>
            )}
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
              color: 'var(--primary)',
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
/*  Delete App Confirmation Modal (with MinIO Purge Option)           */
/* ------------------------------------------------------------------ */

interface DeleteAppModalProps {
  app: AppRecord;
  purgeMinio: boolean;
  onPurgeMinioChange: (val: boolean) => void;
  onConfirm: () => void;
  onClose: () => void;
  loading: boolean;
}

function DeleteAppModal({
  app,
  purgeMinio,
  onPurgeMinioChange,
  onConfirm,
  onClose,
  loading,
}: DeleteAppModalProps) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1050,
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div className="delete-confirm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="delete-confirm-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Trash2 size={16} className="text-secondary-foreground" />
            <h3 className="delete-modal-title">Remove Application</h3>
          </div>
          <button
            className="log-close-btn"
            onClick={onClose}
            disabled={loading}
            aria-label="Close modal"
          >
            <X size={16} />
          </button>
        </div>

        <div className="delete-modal-body">
          <p className="delete-modal-text">
            Are you sure you want to remove application{' '}
            <strong style={{ color: 'var(--foreground)' }}>"{app.name}"</strong>? This will delete
            build history and running container resources.
          </p>

          <label className="delete-checkbox-card">
            <input
              type="checkbox"
              checked={purgeMinio}
              onChange={(e) => onPurgeMinioChange(e.target.checked)}
              disabled={loading}
              data-testid="purge-minio-checkbox"
              className="delete-checkbox-input"
            />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span className="delete-checkbox-title">
                Also remove from MinIO S3 bucket & Docker cache
              </span>
              <span className="delete-checkbox-sub">
                Purges image layers and blobs from MinIO bucket{' '}
                <code className="font-mono">pantheon-registry</code> and frees local disk space.
              </span>
            </div>
          </label>
        </div>

        <div className="delete-confirm-footer">
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-confirm-delete"
            onClick={onConfirm}
            disabled={loading}
            data-testid="confirm-delete-app-btn"
          >
            {loading ? <Loader2 size={13} className="spin" /> : <Trash2 size={13} />}
            Delete Application
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  MinIO S3 & Docker Registry Storage Management Modal               */
/* ------------------------------------------------------------------ */

interface MinioStorageModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: string | null;
  onStorageChanged?: () => void;
}

function MinioStorageModal({ isOpen, onClose, token, onStorageChanged }: MinioStorageModalProps) {
  const [data, setData] = useState<RegistryStorageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [purging, setPurging] = useState<Record<string, boolean>>({});
  const [customPath, setCustomPath] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchStorage = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await apiGet<RegistryStorageResponse>('/apps/storage/registry', token);
      setData(res);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to fetch MinIO storage');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (isOpen) {
      fetchStorage();
    }
  }, [isOpen, fetchStorage]);

  const handlePurgeRepo = async (repoPath: string) => {
    if (
      !window.confirm(
        `Permanently remove repository "${repoPath}" from MinIO S3 bucket and local Docker cache?`,
      )
    ) {
      return;
    }
    setPurging((prev) => ({ ...prev, [repoPath]: true }));
    setStatusMsg(null);
    setErrorMsg(null);
    try {
      await apiDelete(
        `/apps/storage/registry/${encodeURIComponent(repoPath)}?purge_docker=true`,
        token,
      );
      setStatusMsg(`Successfully purged "${repoPath}" from MinIO bucket.`);
      fetchStorage();
      onStorageChanged?.();
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to purge repository');
    } finally {
      setPurging((prev) => {
        const copy = { ...prev };
        delete copy[repoPath];
        return copy;
      });
    }
  };

  const handlePurgeAllOrphans = async () => {
    if (
      !window.confirm(
        'Are you sure you want to permanently purge all orphaned images from the MinIO bucket?',
      )
    ) {
      return;
    }
    setLoading(true);
    setStatusMsg(null);
    setErrorMsg(null);
    try {
      const res = await apiPost<{ purged_count: number }>(
        '/apps/storage/registry/purge-orphans',
        {},
        token,
      );
      setStatusMsg(`Successfully purged ${res.purged_count} orphaned repositories from MinIO.`);
      fetchStorage();
      onStorageChanged?.();
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to purge orphans');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomPurge = async () => {
    if (!customPath.trim()) return;
    await handlePurgeRepo(customPath.trim());
    setCustomPath('');
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1040,
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div className="storage-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="storage-header">
          <div className="storage-header-title">
            <Database size={18} className="text-secondary-foreground" />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h3 className="storage-modal-title">MinIO S3 & Docker Registry Storage</h3>
                <span className="badge badge-secondary font-mono">pantheon-registry</span>
              </div>
              <div className="storage-subtext">
                S3 Endpoint: <code className="font-mono">localhost:9000</code> • Registry:{' '}
                <code className="font-mono">localhost:5000</code>
              </div>
            </div>
          </div>
          <button className="log-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={16} />
          </button>
        </div>

        {/* Stats bar */}
        <div className="storage-stats-bar">
          <div className="storage-stat-chip">
            <span className="storage-stat-label">Total Repositories</span>
            <span className="storage-stat-val">{data ? data.total_repositories : '—'}</span>
          </div>
          <div className={`storage-stat-chip ${data && data.orphaned_count > 0 ? 'warning' : ''}`}>
            <span className="storage-stat-label">Orphaned Images</span>
            <span
              className={`storage-stat-val ${data && data.orphaned_count > 0 ? 'storage-stat-val-warning' : ''}`}
            >
              {data ? data.orphaned_count : '—'}
            </span>
          </div>
          <div className="storage-stat-chip">
            <span className="storage-stat-label">Backing Engine</span>
            <span className="storage-stat-val font-mono" style={{ fontSize: 13 }}>
              MinIO S3 (Active)
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto' }}>
            {data && data.orphaned_count > 0 && (
              <button
                type="button"
                className="btn-purge-all-orphans"
                onClick={handlePurgeAllOrphans}
                disabled={loading}
              >
                <Trash2 size={12} />
                Purge All {data.orphaned_count} Orphaned
              </button>
            )}
            <button
              className="btn-secondary"
              onClick={fetchStorage}
              disabled={loading}
              style={{ padding: '6px 11px' }}
              title="Refresh MinIO Storage"
            >
              <RefreshCw size={12} className={loading ? 'spin' : ''} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="storage-body">
          {statusMsg && (
            <div className="storage-notice storage-notice-success">
              <CheckCircle2 size={14} />
              <span>{statusMsg}</span>
            </div>
          )}
          {errorMsg && (
            <div className="storage-notice storage-notice-danger">
              <AlertCircle size={14} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Table */}
          <div className="storage-table-container">
            <table className="storage-table">
              <thead>
                <tr>
                  <th>Repository Name</th>
                  <th>Tags</th>
                  <th>MinIO Size</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading && !data ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '30px' }}>
                      <Loader2
                        size={18}
                        className="spin"
                        style={{ margin: '0 auto 8px', color: 'var(--muted-foreground)' }}
                      />
                      <span style={{ color: 'var(--muted-foreground)' }}>
                        Reading MinIO bucket catalog...
                      </span>
                    </td>
                  </tr>
                ) : !data || data.repositories.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      style={{
                        textAlign: 'center',
                        padding: '30px',
                        color: 'var(--muted-foreground)',
                      }}
                    >
                      No image repositories currently in the MinIO bucket.
                    </td>
                  </tr>
                ) : (
                  data.repositories.map((repo) => (
                    <tr key={repo.repository}>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span
                            style={{
                              fontWeight: 600,
                              color: 'var(--foreground)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            {repo.name}
                          </span>
                          <span
                            style={{
                              fontSize: 10,
                              color: 'var(--muted-foreground)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            {repo.minio_path}
                          </span>
                        </div>
                      </td>
                      <td>
                        {repo.tags && repo.tags.length > 0 ? (
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                            {repo.tags.map((t: string) => (
                              <span
                                key={t}
                                className="badge badge-secondary font-mono"
                                style={{ fontSize: 10 }}
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span style={{ color: 'var(--muted-foreground)', fontSize: 11 }}>
                            none
                          </span>
                        )}
                      </td>
                      <td>
                        <span
                          className="font-mono"
                          style={{ fontSize: 11, color: 'var(--foreground)' }}
                        >
                          {repo.size_human} ({repo.object_count} obj)
                        </span>
                      </td>
                      <td>
                        {repo.is_orphaned ? (
                          <span
                            className="badge badge-warning font-mono"
                            style={{ fontSize: 10 }}
                            title="No active app found with this name in PostgreSQL"
                          >
                            Orphaned
                          </span>
                        ) : (
                          <span className="badge badge-success font-mono" style={{ fontSize: 10 }}>
                            Active App
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          type="button"
                          className="btn-purge-repo"
                          onClick={() => handlePurgeRepo(repo.repository)}
                          disabled={purging[repo.repository] || loading}
                          title="Purge repository from MinIO bucket & Docker image cache"
                        >
                          {purging[repo.repository] ? (
                            <Loader2 size={12} className="spin" />
                          ) : (
                            <Trash2 size={12} />
                          )}
                          Remove from MinIO
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Quick Purge by Name */}
          <div className="storage-footer-tools">
            <span
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--foreground)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              Purge Specific Image Repository
            </span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                type="text"
                className="input font-mono"
                value={customPath}
                onChange={(e) => setCustomPath(e.target.value)}
                placeholder="e.g. app-service-name or <org-id>/app-name"
                style={{
                  flex: 1,
                  fontSize: 12,
                  padding: '7px 12px',
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleCustomPurge();
                }}
              />
              <button
                type="button"
                className="btn-purge-repo"
                onClick={handleCustomPurge}
                disabled={!customPath.trim() || loading}
                style={{ padding: '7px 14px' }}
              >
                <Trash2 size={12} />
                Purge from MinIO
              </button>
            </div>
          </div>
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

  // Storage modal and Delete modal state
  const [showStorageModal, setShowStorageModal] = useState(false);
  const [deleteModalApp, setDeleteModalApp] = useState<{
    app: AppRecord;
    purgeMinio: boolean;
  } | null>(null);
  const [storageSummary, setStorageSummary] = useState<{
    total_repositories: number;
    orphaned_count: number;
  } | null>(null);

  // Auth — for now use a simple token from localStorage (set after login)
  const [token] = useState<string | null>(() =>
    typeof localStorage !== 'undefined' && typeof localStorage.getItem === 'function'
      ? localStorage.getItem('pantheon_token')
      : null,
  );

  // Fetch storage summary (total & orphaned images in MinIO)
  const fetchStorageSummary = useCallback(async () => {
    try {
      const res = await apiGet<RegistryStorageResponse>('/apps/storage/registry', token);
      setStorageSummary({
        total_repositories: res.total_repositories,
        orphaned_count: res.orphaned_count,
      });
    } catch {
      // background fetch error ignore
    }
  }, [token]);

  useEffect(() => {
    fetchStorageSummary();
  }, [fetchStorageSummary]);

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

  // Delete app handler (opens confirmation modal with MinIO purge option)
  const handleDeleteApp = (app: AppRecord) => {
    setDeleteModalApp({ app, purgeMinio: true });
  };

  const confirmDeleteApp = async () => {
    if (!deleteModalApp) return;
    const { app, purgeMinio } = deleteModalApp;

    setActionLoading((prev) => ({ ...prev, [app.id]: 'delete' }));
    setError(null);
    try {
      await apiDelete(`/apps/${app.id}?purge_minio=${purgeMinio}`, token);
      setApps((prev) => prev.filter((a) => a.id !== app.id));
      setSuccessMsg(
        `Application "${app.name}" removed${purgeMinio ? ' and MinIO image storage purged' : ''}.`,
      );
      if (selectedLogApp === app.id) setSelectedLogApp(null);
      if (selectedPreviewApp?.id === app.id) setSelectedPreviewApp(null);
      setDeleteModalApp(null);
      fetchStorageSummary();
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
                    placeholder="e.g. backend-api or auth-service"
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
                      placeholder="https://github.com/organization/repo.git"
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
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowStorageModal(true)}
                  style={{
                    padding: '4px 10px',
                    fontSize: 11,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                  title="View MinIO S3 & Docker Registry Image Storage"
                  data-testid="open-minio-storage-btn"
                >
                  <Database size={13} style={{ color: 'var(--primary)' }} />
                  MinIO Storage
                  {storageSummary && storageSummary.orphaned_count > 0 && (
                    <span
                      className="badge badge-warning font-mono"
                      style={{ fontSize: 9, padding: '1px 5px' }}
                      title={`${storageSummary.orphaned_count} orphaned image repositories found`}
                    >
                      {storageSummary.orphaned_count} orphan
                    </span>
                  )}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={fetchApps}
                  style={{ padding: '4px 10px' }}
                  title="Refresh application list"
                >
                  <RefreshCw size={12} />
                </button>
              </div>
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
                          {/* Show assigned host port when app has been deployed */}
                          {app.target_profile?.host_port && (
                            <span
                              className="badge badge-info font-mono"
                              style={{ fontSize: 10, marginLeft: 4 }}
                              title={`Container mapped to host port ${app.target_profile.host_port}`}
                            >
                              :{app.target_profile.host_port}
                            </span>
                          )}
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
                            <>
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
                              <button
                                type="button"
                                className="btn-secondary"
                                onClick={() => setSelectedPreviewApp(app)}
                                title="View Live App Preview"
                                style={{
                                  padding: '4px 10px',
                                  fontSize: 11,
                                  textTransform: 'none',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 4,
                                }}
                              >
                                <ExternalLink size={12} />
                                Preview
                              </button>
                            </>
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

      {/* MinIO & Registry Storage Management Modal */}
      <MinioStorageModal
        isOpen={showStorageModal}
        onClose={() => setShowStorageModal(false)}
        token={token}
        onStorageChanged={fetchStorageSummary}
      />

      {/* Delete App Confirmation Modal with MinIO Purge Option */}
      {deleteModalApp && (
        <DeleteAppModal
          app={deleteModalApp.app}
          purgeMinio={deleteModalApp.purgeMinio}
          onPurgeMinioChange={(val) =>
            setDeleteModalApp((prev) => (prev ? { ...prev, purgeMinio: val } : null))
          }
          onConfirm={confirmDeleteApp}
          onClose={() => setDeleteModalApp(null)}
          loading={actionLoading[deleteModalApp.app.id] === 'delete'}
        />
      )}
    </div>
  );
}
