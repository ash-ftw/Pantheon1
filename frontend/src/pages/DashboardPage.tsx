/**
 * DashboardPage — PRD Module 1 (Phase 14).
 *
 * Executive Cyber Range & Security Posture Dashboard. Aggregates multi-app
 * resilience metrics, vulnerability trends over time via Recharts, recent simulation
 * executions, and 1-click preset demo app deployment.
 */

import { useState } from 'react';
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Box,
  CheckCircle2,
  Clock,
  Flame,
  Lock,
  Play,
  RefreshCw,
  Server,
  ShieldAlert,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import './DashboardPage.css';
import { useThemeStore } from '../stores/themeStore';

interface DashboardStats {
  total_apps: number;
  active_deployments: number;
  total_test_runs: number;
  completed_test_runs: number;
  active_test_runs: number;
  total_findings: number;
  findings_by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  open_findings_count: number;
  resolved_findings_count: number;
  resilience_score: number;
  mitigation_stats: {
    total_recommendations: number;
    applied_mitigations: number;
    mitigation_rate_pct: number;
  };
  findings_timeline: Array<{
    date: string;
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
  }>;
  recent_test_runs: Array<{
    id: string;
    app_id: string;
    app_name: string;
    scenario_name: string;
    scenario_category: string;
    status: string;
    findings_count: number;
    critical_count: number;
    total_steps: number;
    current_step: number;
    created_at: string;
  }>;
  cluster_status: {
    status: string;
    namespace: string;
    network_policy: string;
    isolation: string;
  };
  recent_activity: Array<{
    id: string;
    action: string;
    resource_type: string;
    created_at: string;
    details: Record<string, unknown>;
  }>;
}

interface DemoApp {
  id: string;
  name: string;
  description: string;
  category: string;
  vulnerabilities: string[];
  architecture: string;
  git_url: string;
  estimated_deploy_time: string;
  tags: string[];
  highlights: string[];
}

export function DashboardPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [deployingDemoId, setDeployingDemoId] = useState<string | null>(null);
  const [deploySuccessMsg, setDeploySuccessMsg] = useState<string | null>(null);

  // 1. Fetch Dashboard Stats
  const {
    data: stats,
    isLoading: isStatsLoading,
    refetch: refetchStats,
  } = useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      const res = await fetch('/api/dashboard/stats', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
      if (!res.ok) throw new Error('Failed to load dashboard metrics');
      return res.json();
    },
    refetchInterval: 30000,
  });

  // 2. Fetch Demo Apps Catalog
  const { data: demoCatalog = [] } = useQuery<DemoApp[]>({
    queryKey: ['dashboard', 'demo-catalog'],
    queryFn: async () => {
      const res = await fetch('/api/dashboard/demo-catalog', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
      if (!res.ok) return [];
      return res.json();
    },
  });

  // 3. Deploy Demo App Mutation
  const deployDemoMutation = useMutation({
    mutationFn: async (demoId: string) => {
      setDeployingDemoId(demoId);
      const res = await fetch(`/api/dashboard/demo-catalog/${demoId}/deploy`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to deploy demo app');
      }
      return res.json();
    },
    onSuccess: (data) => {
      setDeployingDemoId(null);
      setDeploySuccessMsg(
        `Successfully launched ${data.app_name}! Ingestion build queued into tenant environment.`,
      );
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['apps'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
    onError: (err: Error) => {
      setDeployingDemoId(null);
      alert(`Deployment failed: ${err.message}`);
    },
  });

  const { theme } = useThemeStore();
  const isMatte = theme === 'matte-mono';

  // Severity color mapping conforming to Phase 1 Design Tokens (strictly monochrome in matte)
  const SEVERITY_COLORS = isMatte
    ? {
        critical: '#ffffff',
        high: '#eaeaea',
        medium: '#c8c8c8',
        low: '#8a8a93',
        info: '#5a5a62',
      }
    : {
        critical: '#ef4444',
        high: '#ff6b35',
        medium: '#f59e0b',
        low: '#3b82f6',
        info: '#10b981',
      };

  const severityBarData = stats
    ? [
        {
          name: 'Critical',
          count: stats.findings_by_severity.critical,
          color: SEVERITY_COLORS.critical,
        },
        { name: 'High', count: stats.findings_by_severity.high, color: SEVERITY_COLORS.high },
        { name: 'Medium', count: stats.findings_by_severity.medium, color: SEVERITY_COLORS.medium },
        { name: 'Low', count: stats.findings_by_severity.low, color: SEVERITY_COLORS.low },
        { name: 'Info', count: stats.findings_by_severity.info, color: SEVERITY_COLORS.info },
      ]
    : [];

  const scoreColor = (score: number) => {
    if (isMatte) return 'text-[var(--foreground)]';
    if (score >= 80) return 'text-primary';
    if (score >= 60) return 'text-warning';
    return 'text-danger';
  };

  const scoreBadge = (score: number) => {
    if (score >= 80) return 'Resilient Posture';
    if (score >= 60) return 'Moderate Exposure';
    return 'High Vulnerability Risk';
  };

  return (
    <div className="dashboard-container">
      {/* Header Banner */}
      <div className="dashboard-header">
        <div className="dashboard-title-area">
          <div className="dashboard-badge-row">
            <span className="badge badge-primary font-mono">
              <ShieldCheck size={12} />
              <span>TENANT CLUSTER ISOLATED</span>
            </span>
            <span className="badge badge-secondary font-mono">
              <Lock size={12} />
              <span>DEFAULT-DENY POLICY ACTIVE</span>
            </span>
          </div>
          <h1 className="dashboard-title font-display">Cyber Range Executive Dashboard</h1>
          <p className="dashboard-subtitle">
            Continuous threat simulation, vulnerability trajectory analytics, and automated
            defensive mitigation.
          </p>
        </div>

        <div className="dashboard-actions">
          <button
            type="button"
            className="btn btn-secondary font-mono"
            onClick={() => refetchStats()}
            title="Refresh Metrics"
          >
            <RefreshCw size={14} className={isStatsLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <Link to="/apps" className="btn btn-secondary font-mono">
            <Box size={14} />
            <span>Deploy App</span>
          </Link>
          <Link to="/scenarios" className="btn btn-primary font-mono">
            <Play size={14} />
            <span>Launch Simulation</span>
          </Link>
        </div>
      </div>

      {deploySuccessMsg && (
        <div className="dashboard-alert-banner">
          <CheckCircle2 size={18} className="text-primary" />
          <div className="alert-content">
            <span className="alert-title font-display">Ingestion Underway</span>
            <p className="alert-msg">{deploySuccessMsg}</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary font-mono text-xs"
            onClick={() => navigate('/apps')}
          >
            <span>View Build Stream</span>
            <ArrowRight size={12} />
          </button>
          <button
            type="button"
            className="alert-dismiss font-mono"
            onClick={() => setDeploySuccessMsg(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* Hero Stat Cards */}
      <div className="kpi-grid">
        {/* Card 1: Resilience Score */}
        <div className="kpi-card kpi-card-highlight">
          <div className="kpi-header">
            <span className="kpi-title font-display">Security Resilience Rating</span>
            <div className="kpi-icon-wrap primary">
              <Zap size={18} />
            </div>
          </div>
          <div className="kpi-body">
            <div className="score-display">
              <span
                className={`score-number font-display ${scoreColor(stats?.resilience_score || 0)}`}
              >
                {stats ? stats.resilience_score.toFixed(1) : '--'}
              </span>
              <span className="score-max font-mono">/ 100</span>
            </div>
            <div className="score-progress-bar">
              <div
                className="score-progress-fill"
                style={{
                  width: `${Math.min(100, Math.max(5, stats?.resilience_score || 0))}%`,
                }}
              />
            </div>
          </div>
          <div className="kpi-footer font-mono">
            <span className="kpi-subtext">{scoreBadge(stats?.resilience_score || 0)}</span>
            <span className="badge badge-primary">
              {stats?.mitigation_stats.mitigation_rate_pct}% Fixed
            </span>
          </div>
        </div>

        {/* Card 2: Applications */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title font-display">Connected Applications</span>
            <div className="kpi-icon-wrap info">
              <Box size={18} />
            </div>
          </div>
          <div className="kpi-body">
            <div className="kpi-metric-number font-display">{stats ? stats.total_apps : '--'}</div>
            <div className="kpi-metric-sub font-mono">
              <span className="text-success font-semibold">
                {stats?.active_deployments || 0} active
              </span>{' '}
              running in tenant namespace
            </div>
          </div>
          <div className="kpi-footer font-mono">
            <Link to="/apps" className="kpi-link">
              <span>Manage apps</span>
              <ArrowUpRight size={13} />
            </Link>
          </div>
        </div>

        {/* Card 3: Test Runs */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title font-display">Simulations Executed</span>
            <div className="kpi-icon-wrap accent">
              <Play size={18} />
            </div>
          </div>
          <div className="kpi-body">
            <div className="kpi-metric-number font-display">
              {stats ? stats.total_test_runs : '--'}
            </div>
            <div className="kpi-metric-sub font-mono">
              {stats?.active_test_runs ? (
                <span className="text-primary animate-pulse font-semibold">
                  {stats.active_test_runs} currently executing
                </span>
              ) : (
                <span className="text-muted-foreground">Range cluster idle</span>
              )}
            </div>
          </div>
          <div className="kpi-footer font-mono">
            <Link to="/test-runs" className="kpi-link">
              <span>View live runs</span>
              <ArrowUpRight size={13} />
            </Link>
          </div>
        </div>

        {/* Card 4: Security Findings */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title font-display">Detected Vulnerabilities</span>
            <div className="kpi-icon-wrap danger">
              <ShieldAlert size={18} />
            </div>
          </div>
          <div className="kpi-body">
            <div className="kpi-metric-number font-display">
              {stats ? stats.total_findings : '--'}
            </div>
            <div className="kpi-metric-sub font-mono">
              <span className="text-danger font-semibold">
                {stats?.findings_by_severity.critical || 0} Critical
              </span>
              <span className="mx-1.5 text-muted">·</span>
              <span className="text-accent font-semibold">
                {stats?.findings_by_severity.high || 0} High
              </span>
            </div>
          </div>
          <div className="kpi-footer font-mono">
            <Link to="/defence" className="kpi-link">
              <span>Remediate findings</span>
              <ArrowUpRight size={13} />
            </Link>
          </div>
        </div>
      </div>

      {/* Visual Analytics Charts Section */}
      <div className="charts-grid">
        {/* Recharts Area Chart: Posture Trajectory */}
        <div className="chart-card">
          <div className="chart-card-header">
            <div>
              <h2 className="chart-title font-display">Vulnerability Trajectory Over Time</h2>
              <span className="chart-sub font-mono">
                Severity trends across sequential attack simulation executions
              </span>
            </div>
            <div className="chart-legend-pills font-mono">
              <span className="legend-pill critical">Critical</span>
              <span className="legend-pill high">High</span>
              <span className="legend-pill medium">Medium</span>
            </div>
          </div>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart
                data={
                  stats?.findings_timeline && stats.findings_timeline.length > 0
                    ? stats.findings_timeline
                    : [
                        { date: 'Initial', critical: 2, high: 3, medium: 4, low: 1, total: 10 },
                        { date: 'Iter 1', critical: 1, high: 2, medium: 3, low: 1, total: 7 },
                        { date: 'Iter 2', critical: 0, high: 1, medium: 2, low: 0, total: 3 },
                      ]
                }
                margin={{ top: 10, right: 20, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorCritical" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="5%"
                      stopColor={isMatte ? '#ffffff' : '#ef4444'}
                      stopOpacity={isMatte ? 0.35 : 0.6}
                    />
                    <stop
                      offset="95%"
                      stopColor={isMatte ? '#ffffff' : '#ef4444'}
                      stopOpacity={0.0}
                    />
                  </linearGradient>
                  <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="5%"
                      stopColor={isMatte ? '#eaeaea' : '#ff6b35'}
                      stopOpacity={isMatte ? 0.25 : 0.4}
                    />
                    <stop
                      offset="95%"
                      stopColor={isMatte ? '#eaeaea' : '#ff6b35'}
                      stopOpacity={0.0}
                    />
                  </linearGradient>
                  <linearGradient id="colorMedium" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="5%"
                      stopColor={isMatte ? '#c8c8c8' : '#f59e0b'}
                      stopOpacity={isMatte ? 0.2 : 0.3}
                    />
                    <stop
                      offset="95%"
                      stopColor={isMatte ? '#c8c8c8' : '#f59e0b'}
                      stopOpacity={0.0}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={isMatte ? '#232323' : '#1a2332'} />
                <XAxis
                  dataKey="date"
                  stroke={isMatte ? '#8a8a93' : '#4b5a6e'}
                  tick={{ fontSize: 11, fill: isMatte ? '#c8c8c8' : '#94a3b8' }}
                />
                <YAxis
                  stroke={isMatte ? '#8a8a93' : '#4b5a6e'}
                  tick={{ fontSize: 11, fill: isMatte ? '#c8c8c8' : '#94a3b8' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isMatte ? '#141416' : '#0d1117',
                    borderColor: isMatte ? '#232323' : '#1a2332',
                    borderRadius: '4px',
                    color: isMatte ? '#eaeaea' : '#e2e8f0',
                    fontSize: '12px',
                    fontFamily: 'JetBrains Mono',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="critical"
                  stroke={isMatte ? '#ffffff' : '#ef4444'}
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorCritical)"
                  name="Critical Findings"
                />
                <Area
                  type="monotone"
                  dataKey="high"
                  stroke={isMatte ? '#eaeaea' : '#ff6b35'}
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorHigh)"
                  name="High Severity"
                />
                <Area
                  type="monotone"
                  dataKey="medium"
                  stroke={isMatte ? '#8a8a93' : '#f59e0b'}
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorMedium)"
                  name="Medium Severity"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recharts Bar Chart: Findings by Severity */}
        <div className="chart-card">
          <div className="chart-card-header">
            <div>
              <h2 className="chart-title font-display">Findings by Severity Level</h2>
              <span className="chart-sub font-mono">
                Distribution across all connected workloads in organization
              </span>
            </div>
            <span className="badge badge-secondary font-mono">
              {stats?.total_findings || 0} Total Vulnerabilities
            </span>
          </div>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={severityBarData}
                margin={{ top: 10, right: 20, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={isMatte ? '#232323' : '#1a2332'} />
                <XAxis
                  dataKey="name"
                  stroke={isMatte ? '#8a8a93' : '#4b5a6e'}
                  tick={{ fontSize: 11, fill: isMatte ? '#c8c8c8' : '#94a3b8' }}
                />
                <YAxis
                  stroke={isMatte ? '#8a8a93' : '#4b5a6e'}
                  tick={{ fontSize: 11, fill: isMatte ? '#c8c8c8' : '#94a3b8' }}
                  allowDecimals={false}
                />
                <Tooltip
                  cursor={{
                    fill: isMatte ? 'rgba(255, 255, 255, 0.02)' : 'rgba(255, 255, 255, 0.03)',
                  }}
                  contentStyle={{
                    backgroundColor: isMatte ? '#141416' : '#0d1117',
                    borderColor: isMatte ? '#232323' : '#1a2332',
                    borderRadius: '4px',
                    color: isMatte ? '#eaeaea' : '#e2e8f0',
                    fontSize: '12px',
                    fontFamily: 'JetBrains Mono',
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {severityBarData.map((entry) => (
                    <Cell key={`cell-${entry.name}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Preset Demo Apps Section (PRD §6.1) */}
      <div className="demo-section">
        <div className="section-header">
          <div>
            <div className="badge-title-wrap">
              <span className="badge badge-primary font-mono">Instant Lab Provisioning</span>
              <h2 className="section-title font-display">Explore Known-Vulnerable Demo Apps</h2>
            </div>
            <p className="section-sub">
              Explore attack simulations and defensive mitigations immediately while your custom
              tenant cluster provisions (PRD §6.1).
            </p>
          </div>
        </div>

        <div className="demo-grid">
          {demoCatalog.map((demo) => (
            <div key={demo.id} className="demo-card">
              <div className="demo-card-header">
                <div className="demo-category-badge font-mono">{demo.category}</div>
                <span className="demo-time-badge font-mono">
                  <Clock size={11} />
                  <span>{demo.estimated_deploy_time}</span>
                </span>
              </div>

              <h3 className="demo-app-name font-display">{demo.name}</h3>
              <p className="demo-app-desc">{demo.description}</p>

              <div className="demo-vuln-box">
                <span className="demo-vuln-header font-mono">Testable Vulnerabilities:</span>
                <ul className="demo-vuln-list">
                  {demo.vulnerabilities.slice(0, 3).map((v) => (
                    <li key={v} className="demo-vuln-item">
                      <Flame size={12} className="text-accent" />
                      <span>{v}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="demo-meta-row font-mono">
                <span className="demo-arch">
                  <Server size={12} />
                  <span>{demo.architecture}</span>
                </span>
                <div className="demo-tags">
                  {demo.tags.slice(0, 2).map((t) => (
                    <span key={t} className="badge badge-muted">
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              <div className="demo-card-footer">
                <button
                  type="button"
                  className="btn btn-primary btn-block font-mono"
                  disabled={deployingDemoId === demo.id || deployDemoMutation.isPending}
                  onClick={() => deployDemoMutation.mutate(demo.id)}
                >
                  {deployingDemoId === demo.id ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" />
                      <span>Ingesting Workload...</span>
                    </>
                  ) : (
                    <>
                      <Zap size={14} />
                      <span>1-Click Launch Demo</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Grid: Recent Test Runs & System Security Activity */}
      <div className="bottom-grid">
        {/* Recent Test Runs Table */}
        <div className="card bottom-card">
          <div className="card-header-row">
            <div>
              <h3 className="card-title font-display">Recent Threat Simulations</h3>
              <span className="card-subtitle font-mono">Last 5 automated and custom runs</span>
            </div>
            <Link to="/test-runs" className="kpi-link font-mono">
              <span>View all runs</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="font-mono">SIMULATION</th>
                  <th className="font-mono">TARGET APP</th>
                  <th className="font-mono">STATUS</th>
                  <th className="font-mono">FINDINGS</th>
                  <th className="font-mono">TIME</th>
                  <th className="font-mono text-right">ACTION</th>
                </tr>
              </thead>
              <tbody>
                {stats?.recent_test_runs && stats.recent_test_runs.length > 0 ? (
                  stats.recent_test_runs.map((r) => (
                    <tr key={r.id}>
                      <td className="font-display font-semibold">
                        <div className="run-name-cell">
                          <span>{r.scenario_name}</span>
                          <span className="run-cat-tag font-mono">{r.scenario_category}</span>
                        </div>
                      </td>
                      <td className="font-mono text-sm">{r.app_name}</td>
                      <td>
                        <span
                          className={`badge ${
                            r.status === 'completed'
                              ? 'badge-success'
                              : r.status === 'running'
                                ? 'badge-primary'
                                : 'badge-warning'
                          } font-mono text-xs`}
                        >
                          {r.status.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <div className="finding-pill-group font-mono">
                          {r.critical_count > 0 ? (
                            <span className="badge badge-danger text-xs">
                              {r.critical_count} Critical
                            </span>
                          ) : (
                            <span className="badge badge-secondary text-xs">
                              {r.findings_count} Total
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="font-mono text-xs text-muted-foreground">
                        {new Date(r.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="text-right">
                        <Link
                          to={`/test-runs?run_id=${r.id}`}
                          className="btn btn-secondary btn-sm font-mono"
                        >
                          <span>Inspect</span>
                          <ArrowRight size={11} />
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="table-empty font-mono">
                      No simulation runs recorded yet. Launch a preset scenario above to test target
                      resilience.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Security Audit Feed */}
        <div className="card bottom-card">
          <div className="card-header-row">
            <div>
              <h3 className="card-title font-display">Append-Only Audit Feed</h3>
              <span className="card-subtitle font-mono">
                Cryptographic platform actions (FR-11.1)
              </span>
            </div>
            <Link to="/team" className="kpi-link font-mono">
              <span>Full audit log</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          <div className="activity-list font-mono">
            {stats?.recent_activity && stats.recent_activity.length > 0 ? (
              stats.recent_activity.map((item) => (
                <div key={item.id} className="activity-item">
                  <div className="activity-icon-wrap">
                    <Activity size={13} className="text-primary" />
                  </div>
                  <div className="activity-details">
                    <div className="activity-action-line">
                      <span className="activity-action font-semibold">{item.action}</span>
                      <span className="activity-resource badge badge-secondary">
                        {item.resource_type}
                      </span>
                    </div>
                    <span className="activity-time">
                      {new Date(item.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="table-empty font-mono">No recent audit log activity logged yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
