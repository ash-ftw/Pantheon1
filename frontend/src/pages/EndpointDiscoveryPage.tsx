/**
 * EndpointDiscoveryPage — PRD Module 6 (Phase 5)
 *
 * OpenAPI/Swagger endpoint discovery and classification:
 *   - Probes common spec paths on the deployed app
 *   - Classifies endpoints: public, likely_admin, likely_auth, upload, search
 *   - Each endpoint has confidence scoring with basis
 *   - Filterable by classification category
 *   - Manual re-trigger for re-discovery
 */

import {
  AlertTriangle,
  CheckCircle2,
  FileSearch,
  Filter,
  Globe,
  KeyRound,
  RefreshCw,
  Search,
  Shield,
  Upload,
  Zap,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { useAuthStore } from '../stores/authStore';

import './DiscoveryPages.css';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AppRecord {
  id: string;
  name: string;
  status: string;
  discovery_status: string;
}

interface EndpointItem {
  path: string;
  method: string;
  summary: string;
  description: string;
  classification: string;
  confidence: string;
  confidence_basis: string;
  parameters: Record<string, unknown>[];
}

interface EndpointsResult {
  app_id: string;
  org_id: string;
  namespace: string;
  discovery_status: string;
  specs_found: string[];
  endpoints: EndpointItem[];
  classification: Record<string, EndpointItem[]>;
}

type ClassificationKey = 'all' | 'public' | 'likely_admin' | 'likely_auth' | 'upload' | 'search';

/* ------------------------------------------------------------------ */
/*  API Helpers                                                        */
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

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

const classificationMeta: Record<string, { label: string; icon: React.ReactNode; color: string }> =
  {
    all: { label: 'All', icon: <Filter size={12} />, color: 'var(--foreground)' },
    public: { label: 'Public', icon: <Globe size={12} />, color: 'var(--success)' },
    likely_admin: { label: 'Likely Admin', icon: <Shield size={12} />, color: 'var(--accent)' },
    likely_auth: { label: 'Likely Auth', icon: <KeyRound size={12} />, color: 'var(--warning)' },
    upload: { label: 'Upload', icon: <Upload size={12} />, color: 'var(--info)' },
    search: { label: 'Search', icon: <Search size={12} />, color: 'var(--primary)' },
  };

function ClassificationBadge({ classification }: { classification: string }) {
  const meta = classificationMeta[classification] || classificationMeta.public;
  return (
    <span
      className="badge"
      style={{
        color: meta.color,
        backgroundColor: `color-mix(in srgb, ${meta.color} 12%, transparent)`,
        border: `1px solid color-mix(in srgb, ${meta.color} 28%, transparent)`,
      }}
    >
      {meta.icon}
      {meta.label}
    </span>
  );
}

function ConfidenceDot({ level }: { level: string }) {
  const color =
    level === 'high' ? 'var(--success)' : level === 'medium' ? 'var(--warning)' : 'var(--danger)';
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          backgroundColor: color,
          display: 'inline-block',
          boxShadow: `0 0 4px ${color}`,
        }}
      />
      <span className="font-mono" style={{ fontSize: 10, color, textTransform: 'uppercase' }}>
        {level}
      </span>
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page Component                                                */
/* ------------------------------------------------------------------ */

export function EndpointDiscoveryPage() {
  const token = useAuthStore((s) => s.token);

  const [apps, setApps] = useState<AppRecord[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [result, setResult] = useState<EndpointsResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<ClassificationKey>('all');

  // Load app list
  useEffect(() => {
    apiGet<AppRecord[]>('/apps', token)
      .then((data) => {
        setApps(data);
        if (data.length > 0 && !selectedAppId) {
          const running = data.find((a) => a.status === 'running');
          setSelectedAppId(running?.id || data[0].id);
        } else if (data.length === 0) {
          setLoading(false);
        }
      })
      .catch(() => {
        setApps([]);
        setLoading(false);
      });
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load persisted endpoint data
  useEffect(() => {
    if (!selectedAppId) return;
    let isCurrent = true;
    apiGet<EndpointsResult>(`/discovery/${selectedAppId}/endpoints`, token)
      .then((data) => {
        if (isCurrent) {
          setResult(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (isCurrent) {
          setError(err instanceof Error ? err.message : 'Failed to load endpoints');
        }
      })
      .finally(() => {
        if (isCurrent) {
          setLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [selectedAppId, token]);

  // Re-run discovery
  const handleRerun = async () => {
    if (!selectedAppId) return;
    setRerunning(true);
    setError(null);
    try {
      const data = await apiPost<EndpointsResult>(
        '/discovery/endpoints',
        { app_id: selectedAppId },
        token,
      );
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Discovery failed');
    } finally {
      setRerunning(false);
    }
  };

  // Compute filtered endpoints
  const filteredEndpoints = useMemo(() => {
    if (!result) return [];
    if (activeFilter === 'all') return result.endpoints;
    return result.endpoints.filter((ep) => ep.classification === activeFilter);
  }, [result, activeFilter]);

  // Compute classification counts
  const classificationCounts = useMemo(() => {
    if (!result) return {};
    const counts: Record<string, number> = { all: result.endpoints.length };
    for (const ep of result.endpoints) {
      counts[ep.classification] = (counts[ep.classification] || 0) + 1;
    }
    return counts;
  }, [result]);

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="page-title">Endpoint Discovery</div>
        <div className="page-subtitle">
          Automatic OpenAPI/Swagger spec detection and endpoint classification. Discovers and
          categorizes your application's API surface for targeted security testing.
        </div>
      </div>

      {/* App Selector + Actions */}
      <div className="card">
        <div className="card-body">
          <div className="discovery-app-selector">
            <FileSearch size={16} style={{ color: 'var(--muted-foreground)' }} />
            <select
              value={selectedAppId}
              onChange={(e) => {
                setSelectedAppId(e.target.value);
                setActiveFilter('all');
                setLoading(true);
              }}
              disabled={apps.length === 0}
            >
              {apps.length === 0 ? (
                <option value="">No apps deployed</option>
              ) : (
                apps.map((app) => (
                  <option key={app.id} value={app.id}>
                    {app.name} ({app.status})
                  </option>
                ))
              )}
            </select>

            <button
              className="btn-secondary"
              onClick={handleRerun}
              disabled={!selectedAppId || rerunning}
            >
              <RefreshCw size={12} className={rerunning ? 'animate-pulse' : ''} />
              {rerunning ? 'Discovering...' : 'Re-run Discovery'}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="discovery-status-banner failed">
          <Zap size={14} />
          <span>{error}</span>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="card">
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="skeleton-line" style={{ width: '50%' }} />
            <div className="skeleton-line" style={{ width: '100%' }} />
            <div className="skeleton-line" style={{ width: '100%' }} />
            <div className="skeleton-line" style={{ width: '75%' }} />
          </div>
        </div>
      )}

      {/* Results */}
      {!loading && result && (
        <>
          {/* Spec Status */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">OpenAPI Spec Detection</span>
            </div>
            <div className="card-body">
              {result.specs_found.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {result.specs_found.map((spec) => (
                    <div key={spec} className="spec-status">
                      <span className="dot found" />
                      <CheckCircle2 size={12} style={{ color: 'var(--success)' }} />
                      <span style={{ color: 'var(--foreground)' }}>Spec found at</span>
                      <span className="font-mono" style={{ color: 'var(--primary)' }}>
                        {spec}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="spec-status">
                  <span className="dot not-found" />
                  <AlertTriangle size={12} style={{ color: 'var(--muted-foreground)' }} />
                  <span>
                    No OpenAPI/Swagger spec detected — endpoints may need manual configuration or
                    the app doesn't expose a spec
                  </span>
                </div>
              )}
              <div
                style={{
                  marginTop: 12,
                  fontSize: 11,
                  color: 'var(--muted-foreground)',
                }}
              >
                {result.endpoints.length} endpoint{result.endpoints.length !== 1 ? 's' : ''}{' '}
                discovered across{' '}
                {
                  Object.keys(result.classification).filter(
                    (k) => (result.classification[k] || []).length > 0,
                  ).length
                }{' '}
                classification
                {Object.keys(result.classification).filter(
                  (k) => (result.classification[k] || []).length > 0,
                ).length !== 1
                  ? 's'
                  : ''}
              </div>
            </div>
          </div>

          {/* Classification Filter Tabs */}
          {result.endpoints.length > 0 && (
            <div className="classification-tabs">
              {(Object.keys(classificationMeta) as ClassificationKey[]).map((key) => {
                const count = classificationCounts[key] || 0;
                if (key !== 'all' && count === 0) return null;
                const meta = classificationMeta[key];
                return (
                  <button
                    key={key}
                    className={`classification-tab ${activeFilter === key ? 'active' : ''}`}
                    onClick={() => setActiveFilter(key)}
                  >
                    {meta.icon}
                    {meta.label}
                    {count > 0 && <span className="count">{count}</span>}
                  </button>
                );
              })}
            </div>
          )}

          {/* Endpoint Table */}
          {filteredEndpoints.length > 0 ? (
            <div className="card">
              <div className="endpoint-table-wrap">
                <table className="endpoint-table">
                  <thead>
                    <tr>
                      <th>Method</th>
                      <th>Path</th>
                      <th>Summary</th>
                      <th>Classification</th>
                      <th>Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEndpoints.map((ep, idx) => (
                      <tr key={`${ep.method}-${ep.path}-${idx}`}>
                        <td>
                          <span className={`method-badge method-${ep.method}`}>{ep.method}</span>
                        </td>
                        <td>
                          <span className="endpoint-path">{ep.path}</span>
                        </td>
                        <td>
                          <span style={{ fontSize: 12, color: 'var(--secondary-foreground)' }}>
                            {ep.summary || '—'}
                          </span>
                        </td>
                        <td>
                          <ClassificationBadge classification={ep.classification} />
                        </td>
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <ConfidenceDot level={ep.confidence} />
                            {ep.confidence_basis && (
                              <span
                                style={{
                                  fontSize: 9,
                                  color: 'var(--muted-foreground)',
                                  maxWidth: 180,
                                  lineHeight: 1.3,
                                }}
                              >
                                {ep.confidence_basis}
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : result.endpoints.length > 0 ? (
            <div className="card">
              <div className="card-body">
                <div className="discovery-empty">
                  <Filter size={36} className="icon" />
                  <h3>No Matching Endpoints</h3>
                  <p>
                    No endpoints match the "{classificationMeta[activeFilter]?.label}" filter. Try
                    selecting "All" to see all discovered endpoints.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="card">
              <div className="card-body">
                <div className="discovery-empty">
                  <FileSearch size={48} className="icon" />
                  <h3>No Endpoints Discovered</h3>
                  <p>
                    No API endpoints were found. The application may not expose an OpenAPI/Swagger
                    spec, or the app may still be starting up. Try re-running discovery after the
                    app is fully initialized.
                  </p>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty state — no app selected */}
      {!loading && !result && !error && (
        <div className="card">
          <div className="card-body">
            <div className="discovery-empty">
              <FileSearch size={48} className="icon" />
              <h3>No Discovery Data</h3>
              <p>
                Deploy an application from the App Onboarding page. Endpoint discovery runs
                automatically after a successful deployment and target analysis.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
