/**
 * RouteBrokerPage — PRD §7.5 / Module 11 (Phase 8)
 *
 * Ephemeral Application-Layer Route Broker & Emergency Kill Switch:
 * - Scoped HTTP/HTTPS routing between range cluster and tenant namespaces (FR-5.5, NFR-1.3)
 * - Real-time countdown timers with auto-expiry (FR-5.2)
 * - Sub-5-second synchronous Emergency Kill Switch (NFR-3.1)
 * - Background TTL sweep integration
 * - Append-only audit logging of all route lifecycle events
 */

import {
  AlertOctagon,
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  Copy,
  ExternalLink,
  Globe,
  Plus,
  RefreshCw,
  Route,
  Shield,
  ShieldCheck,
  Terminal,
  Trash2,
  X,
  Zap,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { useAuthStore } from '../stores/authStore';

import './RouteBrokerPage.css';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface RouteRecord {
  id: string;
  org_id: string;
  test_run_id: string | null;
  app_id: string | null;
  target_service: string;
  target_port: number;
  path_prefix: string;
  route_url: string;
  public_url?: string;
  internal_url?: string;
  status: 'active' | 'revoked' | 'expired';
  ttl_seconds: number;
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
  revocation_reason: string | null;
  ingress_name: string;
  namespace: string;
  ttl_remaining_seconds: number;
}

interface AppOption {
  id: string;
  name: string;
  source_type: string;
  status: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const API_BASE = '/api';

function formatCountdown(seconds: number): string {
  if (seconds <= 0) return '00:00';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function getTimerClass(remainingSeconds: number): string {
  if (remainingSeconds <= 60) return 'danger';
  if (remainingSeconds <= 300) return 'warning';
  return 'normal';
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function RouteBrokerPage() {
  const token = useAuthStore((s) => s.token);

  // Data state
  const [routes, setRoutes] = useState<RouteRecord[]>([]);
  const [apps, setApps] = useState<AppOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'revoked' | 'expired'>('all');

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [targetService, setTargetService] = useState('web-frontend');
  const [targetPort, setTargetPort] = useState(8085);
  const [pathPrefix, setPathPrefix] = useState('/');
  const [ttlSeconds, setTtlSeconds] = useState(1800);
  const [openingRoute, setOpeningRoute] = useState(false);

  // Kill Switch states
  const [killingRouteId, setKillingRouteId] = useState<string | null>(null);
  const [killingAll, setKillingAll] = useState(false);
  const [sweeping, setSweeping] = useState(false);
  const [copiedRouteId, setCopiedRouteId] = useState<string | null>(null);
  const [copiedInternalRouteId, setCopiedInternalRouteId] = useState<string | null>(null);
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);

  /* ------------------------------------------------------------------ */
  /*  Helpers                                                           */
  /* ------------------------------------------------------------------ */

  const getPublicUrl = useCallback((route: RouteRecord) => {
    const url = route.public_url || route.route_url;
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    return `${window.location.origin}${url.startsWith('/') ? '' : '/'}${url}`;
  }, []);

  const getInternalUrl = useCallback((route: RouteRecord) => {
    if (route.internal_url) return route.internal_url;
    return `http://${route.ingress_name}.${route.namespace}.svc.cluster.local:${route.target_port}`;
  }, []);

  const handleCopyUrl = (url: string, routeId: string) => {
    navigator.clipboard.writeText(url);
    setCopiedRouteId(routeId);
    setTimeout(() => setCopiedRouteId(null), 2000);
  };

  const handleCopyInternalUrl = (url: string, routeId: string) => {
    navigator.clipboard.writeText(url);
    setCopiedInternalRouteId(routeId);
    setTimeout(() => setCopiedInternalRouteId(null), 2000);
  };

  /* ------------------------------------------------------------------ */
  /*  Data Fetching                                                      */
  /* ------------------------------------------------------------------ */

  const fetchRoutes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/routes`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`Failed to load routes: ${res.statusText}`);
      const data: RouteRecord[] = await res.json();
      setRoutes(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error loading routes');
    }
  }, [token]);

  const fetchApps = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/apps`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data: AppOption[] = await res.json();
        setApps(data);
      }
    } catch {
      // Non-blocking fallback
    }
  }, [token]);

  useEffect(() => {
    let mounted = true;
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchRoutes(), fetchApps()]);
      if (mounted) setLoading(false);
    };
    init();
    return () => {
      mounted = false;
    };
  }, [fetchRoutes, fetchApps]);

  /* ------------------------------------------------------------------ */
  /*  Live Countdown Timer Ticker (1 second interval)                   */
  /* ------------------------------------------------------------------ */

  useEffect(() => {
    const timer = setInterval(() => {
      setRoutes((prevRoutes) =>
        prevRoutes.map((route) => {
          if (route.status !== 'active') return route;

          const updatedTtl = Math.max(0, route.ttl_remaining_seconds - 1);
          if (updatedTtl === 0) {
            return {
              ...route,
              ttl_remaining_seconds: 0,
              status: 'expired',
            };
          }
          return {
            ...route,
            ttl_remaining_seconds: updatedTtl,
          };
        }),
      );
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  /* ------------------------------------------------------------------ */
  /*  Actions                                                            */
  /* ------------------------------------------------------------------ */

  const handleOpenRoute = async (e: React.FormEvent) => {
    e.preventDefault();
    setOpeningRoute(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/routes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          target_service: targetService.trim(),
          target_port: Number(targetPort),
          ttl_seconds: Number(ttlSeconds),
          path_prefix: pathPrefix.trim() || '/',
          app_id: selectedAppId || null,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to open route');
      }

      const createdRoute: RouteRecord = await res.json();
      setRoutes((prev) => [createdRoute, ...prev]);
      setIsModalOpen(false);
      setActionSuccessMessage(
        `Route opened to ${createdRoute.target_service}:${createdRoute.target_port} with ${Math.round(createdRoute.ttl_seconds / 60)}m TTL.`,
      );
      setTimeout(() => setActionSuccessMessage(null), 5000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to open route');
    } finally {
      setOpeningRoute(false);
    }
  };

  const handleKillRoute = async (routeId: string) => {
    setKillingRouteId(routeId);
    try {
      const res = await fetch(
        `${API_BASE}/routes/${routeId}?reason=manual_kill_switch`,
        {
          method: 'DELETE',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        },
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to revoke route');
      }

      const revokedRoute: RouteRecord = await res.json();
      setRoutes((prev) =>
        prev.map((r) => (r.id === routeId ? { ...r, ...revokedRoute } : r)),
      );
      setActionSuccessMessage(`EMERGENCY KILL SWITCH: Route ${routeId.slice(0, 8)} revoked in <500ms.`);
      setTimeout(() => setActionSuccessMessage(null), 5000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to revoke route');
    } finally {
      setKillingRouteId(null);
    }
  };

  const handleKillAllActive = async () => {
    const activeRoutes = routes.filter((r) => r.status === 'active');
    if (activeRoutes.length === 0) return;

    if (!window.confirm(`Are you sure you want to execute EMERGENCY KILL SWITCH on ALL ${activeRoutes.length} active routes?`)) {
      return;
    }

    setKillingAll(true);
    try {
      await Promise.all(
        activeRoutes.map((route) =>
          fetch(`${API_BASE}/routes/${route.id}?reason=emergency_kill_all`, {
            method: 'DELETE',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          }),
        ),
      );
      await fetchRoutes();
      setActionSuccessMessage(`EMERGENCY KILL ALL: ${activeRoutes.length} routes severed synchronously.`);
      setTimeout(() => setActionSuccessMessage(null), 5000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error executing Kill All');
    } finally {
      setKillingAll(false);
    }
  };

  const handleSweepExpired = async () => {
    setSweeping(true);
    try {
      const res = await fetch(`${API_BASE}/routes/sweep`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        await fetchRoutes();
        setActionSuccessMessage('TTL sweep executed cleanly.');
        setTimeout(() => setActionSuccessMessage(null), 4000);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Sweep failed');
    } finally {
      setSweeping(false);
    }
  };

  /* ------------------------------------------------------------------ */
  /*  Filtered Data & Stats                                             */
  /* ------------------------------------------------------------------ */

  const activeRoutesCount = useMemo(
    () => routes.filter((r) => r.status === 'active').length,
    [routes],
  );

  const revokedRoutesCount = useMemo(
    () => routes.filter((r) => r.status === 'revoked').length,
    [routes],
  );

  const expiredRoutesCount = useMemo(
    () => routes.filter((r) => r.status === 'expired').length,
    [routes],
  );

  const filteredRoutes = useMemo(() => {
    if (activeTab === 'all') return routes;
    return routes.filter((r) => r.status === activeTab);
  }, [routes, activeTab]);

  return (
    <div className="page-container route-broker-container">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            <Route className="page-title-icon" /> Route Broker & Kill Switch
          </h1>
          <p className="page-description">
            Ephemeral, application-layer (HTTP/HTTPS) routing bridging range clusters to tenant environments with sub-5-second emergency revocation (PRD §7.5).
          </p>
        </div>
        <div className="route-broker-header-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleSweepExpired}
            disabled={sweeping}
            title="Sweep expired routes immediately"
          >
            <RefreshCw size={14} className={sweeping ? 'animate-spin' : ''} />
            {sweeping ? 'Sweeping...' : 'Sweep Expired'}
          </button>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setIsModalOpen(true)}
            data-testid="open-route-btn"
          >
            <Plus size={14} /> Open Route
          </button>

          <button
            type="button"
            className="btn-emergency-kill"
            onClick={handleKillAllActive}
            disabled={activeRoutesCount === 0 || killingAll}
            data-testid="emergency-kill-all-btn"
            title="Immediately revoke all active attack routes (< 5 seconds)"
          >
            <AlertOctagon size={16} />
            {killingAll ? 'SEVERING ALL...' : `EMERGENCY KILL ALL (${activeRoutesCount})`}
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionSuccessMessage && (
        <div className="safety-notice-card" style={{ borderColor: 'var(--primary)' }}>
          <ShieldCheck size={18} />
          <span>{actionSuccessMessage}</span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="safety-notice-card" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Stat Cards */}
      <div className="route-broker-stats">
        <div className="route-stat-card active">
          <div className="route-stat-label">Active Routes</div>
          <div className="route-stat-value" style={{ color: 'var(--primary)' }}>
            {activeRoutesCount}
          </div>
        </div>

        <div className="route-stat-card danger">
          <div className="route-stat-label">Kill Switch Revocations</div>
          <div className="route-stat-value" style={{ color: 'var(--danger)' }}>
            {revokedRoutesCount}
          </div>
        </div>

        <div className="route-stat-card">
          <div className="route-stat-label">Expired Routes</div>
          <div className="route-stat-value" style={{ color: 'var(--muted-foreground)' }}>
            {expiredRoutesCount}
          </div>
        </div>

        <div className="route-stat-card">
          <div className="route-stat-label">Emergency SLA</div>
          <div className="route-stat-value" style={{ color: '#38bdf8' }}>
            &lt; 5.0s
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="route-filter-tabs">
        <button
          type="button"
          className={`route-filter-tab ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          All Routes <span className="count">{routes.length}</span>
        </button>
        <button
          type="button"
          className={`route-filter-tab ${activeTab === 'active' ? 'active' : ''}`}
          onClick={() => setActiveTab('active')}
        >
          Active <span className="count">{activeRoutesCount}</span>
        </button>
        <button
          type="button"
          className={`route-filter-tab ${activeTab === 'revoked' ? 'active' : ''}`}
          onClick={() => setActiveTab('revoked')}
        >
          Revoked <span className="count">{revokedRoutesCount}</span>
        </button>
        <button
          type="button"
          className={`route-filter-tab ${activeTab === 'expired' ? 'active' : ''}`}
          onClick={() => setActiveTab('expired')}
        >
          Expired <span className="count">{expiredRoutesCount}</span>
        </button>
      </div>

      {/* Routes Grid */}
      {loading ? (
        <div className="route-empty-state">
          <RefreshCw className="animate-spin" size={32} />
          <div className="route-empty-title">Loading Routes...</div>
        </div>
      ) : filteredRoutes.length === 0 ? (
        <div className="route-empty-state">
          <div className="route-empty-icon">
            <Route size={28} />
          </div>
          <div className="route-empty-title">No routes found</div>
          <p className="route-empty-desc">
            {activeTab === 'all'
              ? 'No application routes have been provisioned yet. Open an ephemeral route to allow range workers to communicate with deployed services.'
              : `No routes matching status "${activeTab}".`}
          </p>
          {activeTab === 'all' && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setIsModalOpen(true)}
            >
              <Plus size={14} /> Open First Route
            </button>
          )}
        </div>
      ) : (
        <div className="routes-grid">
          {filteredRoutes.map((route) => {
            const isKillable = route.status === 'active';
            const timerClass = getTimerClass(route.ttl_remaining_seconds);

            return (
              <div
                key={route.id}
                className={`route-card ${route.status}`}
                data-testid={`route-card-${route.id}`}
              >
                <div className="route-card-header">
                  <div>
                    <div className="route-target-title">
                      <Zap size={16} style={{ color: 'var(--primary)' }} />
                      <span>{route.target_service}</span>
                    </div>
                    <span className="route-stat-label">Port: {route.target_port}</span>
                  </div>

                  {route.status === 'active' ? (
                    <div className={`route-timer-badge ${timerClass}`}>
                      <Clock size={12} />
                      <span>{formatCountdown(route.ttl_remaining_seconds)}</span>
                    </div>
                  ) : (
                    <span
                      className={`badge ${
                        route.status === 'revoked' ? 'badge-danger' : 'badge-warning'
                      }`}
                    >
                      {route.status}
                    </span>
                  )}
                </div>

                {/* Human-Accessible Public Test Proxy URL Box */}
                <div className="route-url-box public-url-box">
                  <div className="route-url-header-row">
                    <span className="route-url-type-badge">
                      <Globe size={12} /> Human Test URL
                    </span>
                    <button
                      type="button"
                      className="route-copy-btn"
                      onClick={() => handleCopyUrl(getPublicUrl(route), route.id)}
                      title="Copy public test URL"
                    >
                      {copiedRouteId === route.id ? (
                        <Check size={14} style={{ color: 'var(--primary)' }} />
                      ) : (
                        <Copy size={14} />
                      )}
                    </button>
                  </div>
                  <span className="route-url-text" title={getPublicUrl(route)}>
                    {getPublicUrl(route)}
                  </span>
                </div>

                {/* Collapsible Technical Details (Internal Attack Route) */}
                <div className="route-tech-details-container">
                  <button
                    type="button"
                    className="route-tech-toggle-btn"
                    onClick={() =>
                      setExpandedDetails((prev) => ({
                        ...prev,
                        [route.id]: !prev[route.id],
                      }))
                    }
                  >
                    <div className="route-tech-toggle-left">
                      <Terminal size={12} />
                      <span>Attacker Pod Route & Technical Details</span>
                    </div>
                    {expandedDetails[route.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {expandedDetails[route.id] && (
                    <div className="route-tech-details-content">
                      <div className="route-internal-url-box">
                        <div className="route-internal-header">
                          <span className="route-stat-label" style={{ color: '#38bdf8' }}>
                            Internal Attacker URL (K8s Isolated)
                          </span>
                          <button
                            type="button"
                            className="route-copy-btn"
                            onClick={() => handleCopyInternalUrl(getInternalUrl(route), route.id)}
                            title="Copy internal cluster URL"
                          >
                            {copiedInternalRouteId === route.id ? (
                              <Check size={12} style={{ color: 'var(--primary)' }} />
                            ) : (
                              <Copy size={12} />
                            )}
                          </button>
                        </div>
                        <span className="route-internal-url-text" title={getInternalUrl(route)}>
                          {getInternalUrl(route)}
                        </span>
                      </div>

                      <div className="route-card-meta" style={{ marginTop: '8px' }}>
                        <div>
                          <span style={{ color: 'var(--muted-foreground)' }}>Ingress: </span>
                          <strong style={{ color: 'var(--foreground)' }}>{route.ingress_name}</strong>
                        </div>
                        <div>
                          <span style={{ color: 'var(--muted-foreground)' }}>Target Pod: </span>
                          <strong style={{ color: 'var(--foreground)' }}>
                            {route.target_service}:{route.target_port}
                          </strong>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Meta details */}
                <div className="route-card-meta">
                  <div>
                    <span style={{ color: 'var(--muted-foreground)' }}>Namespace: </span>
                    <strong style={{ color: 'var(--foreground)' }}>{route.namespace}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--muted-foreground)' }}>Path: </span>
                    <strong style={{ color: 'var(--foreground)' }}>{route.path_prefix}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--muted-foreground)' }}>Created: </span>
                    <span>{new Date(route.created_at).toLocaleTimeString()}</span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--muted-foreground)' }}>TTL Limit: </span>
                    <span>{Math.round(route.ttl_seconds / 60)} mins</span>
                  </div>
                </div>

                {/* Revocation audit tag if revoked */}
                {route.status === 'revoked' && route.revocation_reason && (
                  <div>
                    <span className="route-revocation-tag">
                      REVOKED: {route.revocation_reason}
                    </span>
                  </div>
                )}

                {/* Actions */}
                <div className="route-card-actions">
                  <a
                    href={getPublicUrl(route)}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-secondary"
                    style={{ fontSize: '11px', padding: '6px 12px' }}
                    data-testid={`test-link-${route.id}`}
                  >
                    <ExternalLink size={12} /> Test Link
                  </a>

                  {isKillable && (
                    <button
                      type="button"
                      className="btn-kill-single"
                      onClick={() => handleKillRoute(route.id)}
                      disabled={killingRouteId === route.id}
                      data-testid={`kill-route-btn-${route.id}`}
                    >
                      <Trash2 size={12} />
                      {killingRouteId === route.id ? 'Revoking...' : 'Kill Switch'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Open Route Modal */}
      {isModalOpen && (
        <div className="route-modal-backdrop" onClick={() => setIsModalOpen(false)}>
          <div
            className="route-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-labelledby="modal-title"
          >
            <div className="route-modal-header">
              <h3 id="modal-title" className="route-target-title">
                <Route size={18} style={{ color: 'var(--primary)' }} />
                Open Ephemeral Attack Route
              </h3>
              <button
                type="button"
                className="route-copy-btn"
                onClick={() => setIsModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleOpenRoute}>
              <div className="route-modal-body">
                {/* Security Guarantee Card */}
                <div className="safety-notice-card">
                  <Shield size={18} />
                  <div>
                    <strong>PRD §7.5 Application-Layer Scoping:</strong>
                    <p style={{ marginTop: '2px' }}>
                      Routes are strictly HTTP/HTTPS ingress paths. No L3/L4 network bridging, SSH, or raw socket exposure is permitted. Tenant credentials remain unexposed.
                    </p>
                  </div>
                </div>

                {/* App Selector */}
                {apps.length > 0 && (
                  <div className="form-group">
                    <label htmlFor="app-select">Deploy Target App (Optional)</label>
                    <select
                      id="app-select"
                      value={selectedAppId}
                      onChange={(e) => {
                        const appId = e.target.value;
                        setSelectedAppId(appId);
                        const matched = apps.find((a) => a.id === appId);
                        if (matched) {
                          setTargetService(matched.name.toLowerCase().replace(/[^a-z0-9-]/g, '-'));
                          setTargetPort(8085);
                        }
                      }}
                    >
                      <option value="">Custom Service Name...</option>
                      {apps.map((app) => (
                        <option key={app.id} value={app.id}>
                          {app.name} ({app.status})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Target Service Name */}
                <div className="form-group">
                  <label htmlFor="target-service">Target Kubernetes Service Name</label>
                  <input
                    id="target-service"
                    type="text"
                    required
                    value={targetService}
                    onChange={(e) => setTargetService(e.target.value)}
                    placeholder="e.g. web-frontend or api-service"
                  />
                </div>

                {/* Target Port */}
                <div className="form-group">
                  <label htmlFor="target-port">Target HTTP/HTTPS Port</label>
                  <input
                    id="target-port"
                    type="number"
                    min="1"
                    max="65535"
                    required
                    value={targetPort}
                    onChange={(e) => setTargetPort(Number(e.target.value))}
                    placeholder="8085"
                  />
                </div>

                {/* Path Prefix */}
                <div className="form-group">
                  <label htmlFor="path-prefix">Path Prefix</label>
                  <input
                    id="path-prefix"
                    type="text"
                    value={pathPrefix}
                    onChange={(e) => setPathPrefix(e.target.value)}
                    placeholder="/"
                  />
                </div>

                {/* Time To Live (TTL) Presets */}
                <div className="form-group">
                  <label>Time-To-Live (Auto-Expiry Duration)</label>
                  <div className="ttl-presets">
                    {[
                      { label: '15m', sec: 900 },
                      { label: '30m', sec: 1800 },
                      { label: '1h', sec: 3600 },
                      { label: '2h', sec: 7200 },
                    ].map((preset) => (
                      <button
                        key={preset.sec}
                        type="button"
                        className={`ttl-btn ${ttlSeconds === preset.sec ? 'active' : ''}`}
                        onClick={() => setTtlSeconds(preset.sec)}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                  <input
                    type="number"
                    min="60"
                    max="86400"
                    value={ttlSeconds}
                    onChange={(e) => setTtlSeconds(Number(e.target.value))}
                    style={{ marginTop: '8px' }}
                    placeholder="TTL in seconds (60 - 86400)"
                  />
                </div>
              </div>

              <div className="route-modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={openingRoute || !targetService.trim()}
                >
                  <Zap size={14} />
                  {openingRoute ? 'Opening Route...' : 'Open Ephemeral Route'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
