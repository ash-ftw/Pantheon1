/**
 * TargetAnalysisPage — PRD Module 5 (Phase 5)
 *
 * Automated post-deploy profiling:
 *   - Language, framework, exposed ports, detected DB, auth mechanisms
 *   - Environment variable names (never values) for secret-like vars
 *   - Confidence scoring with basis explanation
 *   - Manual re-trigger for re-analysis
 *
 * Data is persisted server-side and loaded via GET endpoint.
 */

import {
  Activity,
  Code2,
  Database,
  Globe,
  KeyRound,
  Loader2,
  Network,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { useAuthStore } from '../stores/authStore';

import './DiscoveryPages.css';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AppRecord {
  id: string;
  name: string;
  status: string;
  source_type: string;
  discovery_status: string;
}

interface TargetProfile {
  app_id: string;
  org_id: string;
  namespace: string;
  discovery_status: string;
  language: string | null;
  framework: string | null;
  exposed_ports: number[];
  detected_db: string | null;
  db_environment_variables: string[];
  auth_mechanisms: string[];
  auth_env_variables: string[];
  confidence: string;
  confidence_basis: string;
}

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

function ConfidenceMeter({ level }: { level: string }) {
  const segments = level === 'high' ? 3 : level === 'medium' ? 2 : 1;
  return (
    <div className="confidence-meter">
      <div className="confidence-bar">
        {[1, 2, 3].map((i) => (
          <div key={i} className={`confidence-segment ${i <= segments ? `active ${level}` : ''}`} />
        ))}
      </div>
      <span
        className={`confidence-label`}
        style={{
          color:
            level === 'high'
              ? 'var(--success)'
              : level === 'medium'
                ? 'var(--warning)'
                : 'var(--danger)',
        }}
      >
        {level}
      </span>
    </div>
  );
}

function DiscoveryStatusBanner({ status }: { status: string }) {
  const icons: Record<string, React.ReactNode> = {
    pending: <Loader2 size={14} />,
    running: <Loader2 size={14} className="animate-pulse" />,
    completed: <ShieldCheck size={14} />,
    failed: <Zap size={14} />,
  };

  const messages: Record<string, string> = {
    pending: 'Discovery pending — deploy an app to trigger automatic analysis',
    running: 'Discovery running — analyzing your application...',
    completed: 'Discovery completed — profile data is current',
    failed: 'Discovery encountered an error — you can retry manually',
  };

  return (
    <div className={`discovery-status-banner ${status}`}>
      {icons[status] || icons.pending}
      <span>{messages[status] || messages.pending}</span>
    </div>
  );
}

function ProfileCard({
  label,
  value,
  icon,
  children,
}: {
  label: string;
  value?: string | null;
  icon: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <div className="profile-item">
      <div className="profile-item-label">{label}</div>
      {children ? (
        children
      ) : (
        <div className="profile-item-value">
          <span className="icon">{icon}</span>
          {value || 'Not detected'}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page Component                                                */
/* ------------------------------------------------------------------ */

export function TargetAnalysisPage() {
  const token = useAuthStore((s) => s.token);

  const [apps, setApps] = useState<AppRecord[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [profile, setProfile] = useState<TargetProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load app list
  useEffect(() => {
    apiGet<AppRecord[]>('/apps', token)
      .then((data) => {
        setApps(data);
        if (data.length > 0 && !selectedAppId) {
          // Pre-select the first running app, or just the first app
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

  // Load persisted profile when app is selected
  useEffect(() => {
    if (!selectedAppId) {
      return;
    }
    let isCurrent = true;
    apiGet<TargetProfile>(`/discovery/${selectedAppId}/profile`, token)
      .then((data) => {
        if (isCurrent) {
          setProfile(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (isCurrent) {
          setError(err instanceof Error ? err.message : 'Failed to load profile');
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

  // Re-run analysis
  const handleRerun = async () => {
    if (!selectedAppId) return;
    setRerunning(true);
    setError(null);
    try {
      const data = await apiPost<TargetProfile>(
        '/discovery/target-analysis',
        { app_id: selectedAppId },
        token,
      );
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setRerunning(false);
    }
  };

  const selectedApp = apps.find((a) => a.id === selectedAppId);

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="page-title">Target Analysis</div>
        <div className="page-subtitle">
          Automated profiling of deployed applications — language, framework, ports, database, and
          authentication mechanisms. Runs automatically after each deployment.
        </div>
      </div>

      {/* App Selector + Actions */}
      <div className="card">
        <div className="card-body">
          <div className="discovery-app-selector">
            <Search size={16} style={{ color: 'var(--muted-foreground)' }} />
            <select
              value={selectedAppId}
              onChange={(e) => {
                setSelectedAppId(e.target.value);
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
              {rerunning ? 'Analyzing...' : 'Re-run Analysis'}
            </button>

            {selectedApp && (
              <span
                className={`badge ${selectedApp.status === 'running' ? 'badge-success' : 'badge-info'}`}
              >
                {selectedApp.status}
              </span>
            )}
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
            <div className="skeleton-line" style={{ width: '60%' }} />
            <div className="skeleton-line" style={{ width: '80%' }} />
            <div className="skeleton-line" style={{ width: '45%' }} />
            <div className="skeleton-line" style={{ width: '70%' }} />
          </div>
        </div>
      )}

      {/* Profile Display */}
      {!loading && profile && (
        <>
          {/* Status Banner */}
          <DiscoveryStatusBanner status={profile.discovery_status} />

          {/* Confidence + Namespace */}
          <div className="card">
            <div
              className="card-header"
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
            >
              <span className="card-title">Analysis Overview</span>
              <ConfidenceMeter level={profile.confidence} />
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Server size={14} style={{ color: 'var(--muted-foreground)' }} />
                  <span style={{ fontSize: 12, color: 'var(--secondary-foreground)' }}>
                    Namespace:
                  </span>
                  <span className="font-mono" style={{ fontSize: 11, color: 'var(--primary)' }}>
                    {profile.namespace}
                  </span>
                </div>
                {profile.confidence_basis && (
                  <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>
                    Signals: {profile.confidence_basis}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Profile Cards Grid */}
          <div className="profile-grid">
            <ProfileCard label="Language" value={profile.language} icon={<Code2 size={18} />} />
            <ProfileCard label="Framework" value={profile.framework} icon={<Globe size={18} />} />
            <ProfileCard
              label="Database"
              value={profile.detected_db}
              icon={<Database size={18} />}
            />

            {/* Exposed Ports */}
            <ProfileCard label="Exposed Ports" icon={<Network size={18} />}>
              {profile.exposed_ports.length > 0 ? (
                <div className="port-tags">
                  {profile.exposed_ports.map((port) => (
                    <span key={port} className="port-tag">
                      :{port}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="profile-item-value">
                  <span className="icon">
                    <Network size={18} />
                  </span>
                  No ports detected
                </div>
              )}
            </ProfileCard>

            {/* Auth Mechanisms */}
            <ProfileCard label="Authentication" icon={<KeyRound size={18} />}>
              {profile.auth_mechanisms.length > 0 &&
              profile.auth_mechanisms[0] !== 'none detected' ? (
                <div className="auth-tags">
                  {profile.auth_mechanisms.map((mechanism) => (
                    <span key={mechanism} className="auth-tag">
                      {mechanism}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="profile-item-value">
                  <span className="icon">
                    <KeyRound size={18} />
                  </span>
                  None detected
                </div>
              )}
            </ProfileCard>

            {/* Activity indicator */}
            <ProfileCard label="Discovery Status" icon={<Activity size={18} />}>
              <div className="profile-item-value">
                <span className="icon">
                  <Activity size={18} />
                </span>
                <span
                  className={`badge badge-${
                    profile.discovery_status === 'completed'
                      ? 'success'
                      : profile.discovery_status === 'running'
                        ? 'warning'
                        : profile.discovery_status === 'failed'
                          ? 'danger'
                          : 'info'
                  }`}
                >
                  {profile.discovery_status}
                </span>
              </div>
            </ProfileCard>
          </div>

          {/* Environment Variables */}
          {(profile.db_environment_variables.length > 0 ||
            profile.auth_env_variables.length > 0) && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Detected Environment Variables</span>
              </div>
              <div className="card-body">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                  {/* DB Env Vars */}
                  <div>
                    <div className="profile-item-label" style={{ marginBottom: 10 }}>
                      Database Variables
                    </div>
                    {profile.db_environment_variables.length > 0 ? (
                      <div className="env-var-list">
                        {profile.db_environment_variables.map((v) => (
                          <div key={v} className="env-var-item">
                            {v}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>
                        No database variables found
                      </div>
                    )}
                  </div>

                  {/* Auth Env Vars */}
                  <div>
                    <div className="profile-item-label" style={{ marginBottom: 10 }}>
                      Auth / Secret Variables
                    </div>
                    {profile.auth_env_variables.length > 0 ? (
                      <div className="env-var-list">
                        {profile.auth_env_variables.map((v) => (
                          <div key={v} className="env-var-item">
                            {v}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>
                        No auth/secret variables found
                      </div>
                    )}
                  </div>
                </div>
                <div
                  style={{
                    marginTop: 16,
                    fontSize: 10,
                    color: 'var(--muted-foreground)',
                    fontFamily: 'var(--font-mono)',
                    letterSpacing: '0.04em',
                  }}
                >
                  Note: Only variable names are shown — values are never exposed (PRD §7.2 FR-2.7)
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!loading && !profile && !error && (
        <div className="card">
          <div className="card-body">
            <div className="discovery-empty">
              <Search size={48} className="icon" />
              <h3>No Target Profile</h3>
              <p>
                Deploy an application from the App Onboarding page. Target analysis runs
                automatically after a successful deployment.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
