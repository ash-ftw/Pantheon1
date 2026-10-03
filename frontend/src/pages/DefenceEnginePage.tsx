/**
 * DefenceEnginePage — PRD Module 14 / Module 10 (Phase 11).
 *
 * Actionable mitigation center mapping discovered findings to deterministic
 * code guidance and 1-click infrastructure remediations (Kubernetes NetworkPolicy,
 * RateLimit middleware, security headers) with instant apply/revert lifecycle.
 */

import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Code2,
  Copy,
  Layers,
  RefreshCw,
  RotateCcw,
  Server,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  X,
  Zap,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useThemeStore } from '../stores/themeStore';
import './DefenceEnginePage.css';

export interface DefenceRecommendation {
  id: string;
  org_id: string;
  test_run_id: string;
  finding_id: string;
  app_id: string;
  title: string;
  category: string;
  mitigation_type: 'infrastructure' | 'code_guidance';
  mechanically_applicable: boolean;
  status: 'suggested' | 'applied' | 'reverted' | 'dismissed';
  code_guidance: string;
  infra_manifest: Record<string, unknown>;
  target_resource?: string | null;
  applied_at?: string | null;
  reverted_at?: string | null;
  created_at: string;
}

interface TestRunSummary {
  id: string;
  scenario_name: string;
  status: string;
  current_step: number;
  total_steps: number;
}

export function DefenceEnginePage() {
  const [recommendations, setRecommendations] = useState<DefenceRecommendation[]>([]);
  const [testRuns, setTestRuns] = useState<TestRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [loading, setLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [actionInProgressId, setActionInProgressId] = useState<string | null>(null);
  const [selectedRecId, setSelectedRecId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{
    text: string;
    type: 'success' | 'error';
  } | null>(null);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const theme = useThemeStore((s) => s.theme);
  const isMatte = theme === 'matte-mono';

  // Derived selected recommendation - stable and never triggers re-fetching
  const selectedRec = useMemo(() => {
    if (!selectedRecId) return null;
    return recommendations.find((r) => r.id === selectedRecId) || null;
  }, [recommendations, selectedRecId]);

  // Fetch Test Runs
  const fetchRuns = useCallback(async () => {
    try {
      const res = await fetch('/api/attack-graph/runs');
      if (res.ok) {
        const data = await res.json();
        setTestRuns(data);
      }
    } catch {
      // Fallback runs
    }
  }, []);

  // Fetch Recommendations - only triggers loading state on initial mount or run change
  const fetchRecommendations = useCallback(
    async (isInitialOrRunChange = false) => {
      try {
        if (isInitialOrRunChange) {
          setLoading(true);
        } else {
          setIsSyncing(true);
        }
        const url =
          selectedRunId && selectedRunId !== 'all'
            ? `/api/defence/recommendations?test_run_id=${selectedRunId}`
            : '/api/defence/recommendations';
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setRecommendations(data);
        }
      } catch {
        // Offline fallback
      } finally {
        if (isInitialOrRunChange) {
          setLoading(false);
        } else {
          setIsSyncing(false);
        }
      }
    },
    [selectedRunId],
  );

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    fetchRecommendations(true);
  }, [fetchRecommendations]);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4500);
  };

  // 1-Click Apply Mitigation
  const handleApply = async (rec: DefenceRecommendation) => {
    setActionInProgressId(rec.id);
    try {
      const res = await fetch(`/api/defence/recommendations/${rec.id}/apply`, {
        method: 'POST',
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(`Mitigation deployed to ${data.target_resource || 'cluster'}!`, 'success');
        await fetchRecommendations(false);
      } else {
        showToast(data.detail || data.message || 'Failed to apply mitigation', 'error');
      }
    } catch {
      showToast('Network error while applying mitigation', 'error');
    } finally {
      setActionInProgressId(null);
    }
  };

  // Rollback Mitigation
  const handleRevert = async (rec: DefenceRecommendation) => {
    setActionInProgressId(rec.id);
    try {
      const res = await fetch(`/api/defence/recommendations/${rec.id}/revert`, {
        method: 'POST',
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(`Mitigation reverted from ${rec.target_resource}`, 'success');
        await fetchRecommendations(false);
      } else {
        showToast(data.detail || data.message || 'Failed to revert mitigation', 'error');
      }
    } catch {
      showToast('Network error while reverting mitigation', 'error');
    } finally {
      setActionInProgressId(null);
    }
  };

  const copyToClipboard = (text: string, section: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(section);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  // Filtered recommendations
  const filteredRecs = useMemo(() => {
    return recommendations.filter((r) => {
      const matchStatus = statusFilter === 'all' || r.status === statusFilter;
      const matchType = typeFilter === 'all' || r.mitigation_type === typeFilter;
      return matchStatus && matchType;
    });
  }, [recommendations, statusFilter, typeFilter]);

  // Summary Metrics
  const metrics = useMemo(() => {
    const total = recommendations.length;
    const applicable = recommendations.filter((r) => r.mechanically_applicable).length;
    const applied = recommendations.filter((r) => r.status === 'applied').length;
    const coveragePct = total > 0 ? Math.round((applied / total) * 100) : 0;
    return { total, applicable, applied, coveragePct };
  }, [recommendations]);

  return (
    <div className="defence-page">
      {/* Toast Notification */}
      {toastMessage && (
        <div className={`defence-toast ${toastMessage.type}`}>
          {toastMessage.type === 'success' ? (
            <CheckCircle2 size={16} />
          ) : (
            <AlertTriangle size={16} />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="defence-header">
        <div className="defence-header-title">
          <div className="defence-badge">PRD MODULE 14 · PHASE 11</div>
          <h1>DEFENCE ENGINE & REMEDIATION</h1>
          <p>
            Deterministic finding mitigations, code-level remediation diffs, and 1-click
            infrastructure guardrails.
          </p>
        </div>

        <div className="defence-header-controls">
          <div className="run-selector-group">
            <span className="control-label">SCOPED TEST RUN</span>
            <select
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="run-select"
            >
              <option value="all">All Platform Runs</option>
              {testRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.scenario_name} ({r.status.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => fetchRecommendations(false)}
            className="refresh-button"
            disabled={isSyncing}
            title="Refresh Recommendations"
          >
            <RefreshCw size={15} className={isSyncing ? 'animate-spin' : ''} />
            <span>{isSyncing ? 'SYNCING...' : 'SYNC'}</span>
          </button>
        </div>
      </div>

      {/* Stat Bar */}
      <div className="defence-stats-grid">
        <div className="stat-card">
          <div className="stat-icon-wrapper cyan">
            <ShieldAlert size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-number">{metrics.total}</span>
            <span className="stat-label">DISCOVERED FINDINGS</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper blue">
            <Zap size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-number">{metrics.applicable}</span>
            <span className="stat-label">1-CLICK APPLICABLE</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper green">
            <ShieldCheck size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-number">{metrics.applied}</span>
            <span className="stat-label">ACTIVE MITIGATIONS</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrapper orange">
            <Layers size={20} />
          </div>
          <div className="stat-info">
            <span className="stat-number">{metrics.coveragePct}%</span>
            <span className="stat-label">REMEDIATION COVERAGE</span>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="defence-filter-bar">
        <div className="filter-group">
          <span className="filter-label">STATUS:</span>
          {['all', 'suggested', 'applied', 'reverted'].map((s) => (
            <button
              key={s}
              className={`filter-pill ${statusFilter === s ? 'active' : ''}`}
              onClick={() => setStatusFilter(s)}
            >
              {s.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="filter-group">
          <span className="filter-label">TYPE:</span>
          {[
            { key: 'all', label: 'ALL' },
            { key: 'infrastructure', label: '1-CLICK INFRA' },
            { key: 'code_guidance', label: 'CODE GUIDE' },
          ].map((t) => (
            <button
              key={t.key}
              className={`filter-pill ${typeFilter === t.key ? 'active' : ''}`}
              onClick={() => setTypeFilter(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="defence-content-area">
        {loading ? (
          <div className="defence-loading-state">
            <div className="loading-spinner" />
            <p>Loading deterministic defence recommendations...</p>
          </div>
        ) : filteredRecs.length === 0 ? (
          <div className="defence-empty-state">
            <ShieldCheck size={48} className="empty-icon" />
            <h3>NO MITIGATIONS MATCH FILTER</h3>
            <p>
              Run an attack simulation in Test Runs to detect security findings and generate
              actionable recommendations.
            </p>
          </div>
        ) : (
          <div className="recommendations-table-container">
            <table className="recommendations-table">
              <thead>
                <tr>
                  <th>MITIGATION & TITLE</th>
                  <th>CATEGORY</th>
                  <th>TARGET RESOURCE</th>
                  <th>TYPE</th>
                  <th>STATUS</th>
                  <th className="actions-header">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecs.map((rec) => {
                  const isActioning = actionInProgressId === rec.id;
                  const isApplied = rec.status === 'applied';

                  return (
                    <tr
                      key={rec.id}
                      className={`rec-row ${selectedRecId === rec.id ? 'active-row' : ''}`}
                      onClick={() => setSelectedRecId(rec.id)}
                    >
                      <td className="rec-title-cell">
                        <div className="rec-title-wrap">
                          <div className="rec-icon">
                            {rec.mechanically_applicable ? (
                              <Zap size={16} className={isMatte ? 'text-white' : 'text-cyan'} />
                            ) : (
                              <Code2 size={16} />
                            )}
                          </div>
                          <div>
                            <span className="rec-main-title">{rec.title}</span>
                            <span className="rec-subtitle">
                              Linked to Finding ID: {rec.finding_id.slice(0, 8)}...
                            </span>
                          </div>
                        </div>
                      </td>

                      <td>
                        <span className="category-pill">{rec.category}</span>
                      </td>

                      <td>
                        <span className="resource-code">
                          {rec.target_resource || (
                            <span className="text-muted">Application Source Code</span>
                          )}
                        </span>
                      </td>

                      <td>
                        <span className={`type-tag ${rec.mitigation_type}`}>
                          {rec.mitigation_type === 'infrastructure' ? '1-Click Infra' : 'Code Diff'}
                        </span>
                      </td>

                      <td>
                        <span className={`status-pill ${rec.status}`}>
                          {isApplied && <CheckCircle2 size={12} />}
                          {rec.status.toUpperCase()}
                        </span>
                      </td>

                      <td className="actions-cell" onClick={(e) => e.stopPropagation()}>
                        <div className="action-buttons-wrap">
                          {rec.mechanically_applicable && !isApplied && (
                            <button
                              className="apply-button"
                              onClick={() => handleApply(rec)}
                              disabled={isActioning}
                            >
                              {isActioning ? (
                                <span className="button-spinner" />
                              ) : (
                                <>
                                  <Zap size={13} />
                                  <span>APPLY</span>
                                </>
                              )}
                            </button>
                          )}

                          {rec.mechanically_applicable && isApplied && (
                            <button
                              className="revert-button"
                              onClick={() => handleRevert(rec)}
                              disabled={isActioning}
                            >
                              {isActioning ? (
                                <span className="button-spinner" />
                              ) : (
                                <>
                                  <RotateCcw size={13} />
                                  <span>REVERT</span>
                                </>
                              )}
                            </button>
                          )}

                          <button
                            className="inspect-button"
                            onClick={() => setSelectedRecId(rec.id)}
                            title="Inspect Remediation Guidance"
                          >
                            <ArrowRight size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Inspector Slide-Over Drawer */}
      {selectedRec && (
        <div className="inspector-drawer-backdrop" onClick={() => setSelectedRecId(null)}>
          <div className="inspector-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div className="drawer-title-group">
                <span className="drawer-badge">{selectedRec.category.toUpperCase()}</span>
                <h2>{selectedRec.title}</h2>
                <div className="drawer-meta-line">
                  <span className={`status-pill ${selectedRec.status}`}>
                    {selectedRec.status.toUpperCase()}
                  </span>
                  <span className="drawer-target-code">
                    {selectedRec.target_resource || 'Source Code Guidance'}
                  </span>
                </div>
              </div>
              <button className="drawer-close" onClick={() => setSelectedRecId(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="drawer-body">
              {/* 1-Click Action Bar if applicable */}
              {selectedRec.mechanically_applicable && (
                <div className="drawer-action-banner">
                  <div className="action-banner-info">
                    <Zap size={18} className={isMatte ? 'text-white' : 'text-cyan'} />
                    <div>
                      <strong>Automated Infrastructure Remediation</strong>
                      <p>
                        Deploys a hardened Kubernetes NetworkPolicy / Traefik Middleware to isolate
                        target pods.
                      </p>
                    </div>
                  </div>
                  {selectedRec.status !== 'applied' ? (
                    <button
                      className="drawer-apply-btn"
                      onClick={() => handleApply(selectedRec)}
                      disabled={actionInProgressId === selectedRec.id}
                    >
                      <Zap size={14} />
                      <span>1-CLICK APPLY MITIGATION</span>
                    </button>
                  ) : (
                    <button
                      className="drawer-revert-btn"
                      onClick={() => handleRevert(selectedRec)}
                      disabled={actionInProgressId === selectedRec.id}
                    >
                      <RotateCcw size={14} />
                      <span>ROLLBACK MITIGATION</span>
                    </button>
                  )}
                </div>
              )}

              {/* Code Guidance Section */}
              <div className="drawer-section">
                <div className="section-header">
                  <div className="section-title">
                    <Code2 size={16} />
                    <span>CODE-LEVEL REMEDIATION GUIDANCE</span>
                  </div>
                  <button
                    className="copy-btn"
                    onClick={() => copyToClipboard(selectedRec.code_guidance, 'code')}
                  >
                    <Copy size={13} />
                    <span>{copiedSection === 'code' ? 'COPIED!' : 'COPY'}</span>
                  </button>
                </div>
                <div className="code-box">
                  <pre>{selectedRec.code_guidance}</pre>
                </div>
              </div>

              {/* Kubernetes Manifest Section */}
              {selectedRec.infra_manifest && Object.keys(selectedRec.infra_manifest).length > 0 && (
                <div className="drawer-section">
                  <div className="section-header">
                    <div className="section-title">
                      <Server size={16} />
                      <span>KUBERNETES INFRASTRUCTURE MANIFEST</span>
                    </div>
                    <button
                      className="copy-btn"
                      onClick={() =>
                        copyToClipboard(
                          JSON.stringify(selectedRec.infra_manifest, null, 2),
                          'manifest',
                        )
                      }
                    >
                      <Copy size={13} />
                      <span>{copiedSection === 'manifest' ? 'COPIED!' : 'COPY'}</span>
                    </button>
                  </div>
                  <div className="manifest-box">
                    <pre>{JSON.stringify(selectedRec.infra_manifest, null, 2)}</pre>
                  </div>
                </div>
              )}

              {/* Audit & Execution Metadata */}
              <div className="drawer-section">
                <div className="section-header">
                  <div className="section-title">
                    <Terminal size={16} />
                    <span>AUDIT & REVISION METADATA</span>
                  </div>
                </div>
                <div className="meta-grid">
                  <div className="meta-item">
                    <span className="meta-label">RECOMMENDATION ID</span>
                    <span className="meta-value">{selectedRec.id}</span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-label">ASSOCIATED FINDING</span>
                    <span className="meta-value">{selectedRec.finding_id}</span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-label">GENERATED AT</span>
                    <span className="meta-value">
                      {new Date(selectedRec.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-label">APPLIED TIMESTAMP</span>
                    <span className="meta-value">
                      {selectedRec.applied_at
                        ? new Date(selectedRec.applied_at).toLocaleString()
                        : 'Not Applied'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
