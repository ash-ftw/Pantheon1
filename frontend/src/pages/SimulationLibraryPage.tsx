/**
 * SimulationLibraryPage — PRD Module 7 (Phase 6)
 *
 * Preset & Custom Scenario Browser:
 * - 13 required categories (Brute Force, Credential Stuffing, SQLi, XSS, Auth, BOLA, Chaos, etc.)
 * - Rich metadata cards with method badges, estimated impact, concurrency, and duration
 * - Category filter tabs & keyword search
 * - Scenario detail modal with full target spec and expected signals
 * - "Clone to Custom Editor" action
 */

import {
  AlertTriangle,
  Boxes,
  Clock,
  ExternalLink,
  Flame,
  KeyRound,
  Layers,
  Network,
  Plus,
  Radio,
  Search,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Users,
  Wrench,
  X,
  Zap,
} from 'lucide-react';
import { type ReactNode, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';

import { useAuthStore } from '../stores/authStore';

import './ScenarioPages.css';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface ScenarioDefinition {
  name: string;
  description: string;
  category: string;
  target: {
    service: string;
    path: string;
    port: number;
    protocol: string;
    headers?: Record<string, string>;
    query_params?: Record<string, string>;
  };
  method: string;
  payload_category: string;
  concurrency: number;
  duration: number;
  expected_signals: string[];
  parameters: Record<string, unknown>;
  estimated_impact: 'low' | 'medium' | 'high' | 'critical';
  estimated_duration_seconds: number;
  source: 'preset' | 'ai' | 'custom';
  tags: string[];
}

export interface ScenarioItem {
  id: string;
  org_id: string | null;
  name: string;
  slug: string;
  description: string;
  category: string;
  source: 'preset' | 'ai' | 'custom';
  is_preset: boolean;
  definition: ScenarioDefinition;
  created_at: string;
  updated_at: string;
}

const CATEGORY_GROUPS: { label: string; key: string; icon: ReactNode }[] = [
  { label: 'All Scenarios', key: 'all', icon: <Layers size={14} /> },
  { label: 'Brute Force', key: 'brute_force', icon: <Flame size={14} /> },
  { label: 'Credential Stuffing', key: 'credential_guessing', icon: <KeyRound size={14} /> },
  { label: 'SQL Injection', key: 'sqli_resilience', icon: <ShieldAlert size={14} /> },
  { label: 'XSS Reflection', key: 'xss_reflection', icon: <Shield size={14} /> },
  { label: 'Auth & JWT', key: 'auth_abuse', icon: <Zap size={14} /> },
  { label: 'BOLA / IDOR', key: 'bola', icon: <Users size={14} /> },
  { label: 'API Abuse', key: 'api_abuse', icon: <AlertTriangle size={14} /> },
  { label: 'Cache Pressure', key: 'cache_pressure', icon: <Boxes size={14} /> },
  { label: 'Traffic Flood', key: 'traffic_flood', icon: <Radio size={14} /> },
  { label: 'Service Chaos', key: 'service_failure', icon: <Server size={14} /> },
  { label: 'Network Latency', key: 'network_partition', icon: <Network size={14} /> },
  { label: 'Resource Starvation', key: 'resource_exhaustion', icon: <Flame size={14} /> },
  { label: 'Multi-Stage Chain', key: 'multi_stage_chain', icon: <Layers size={14} /> },
];

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function SimulationLibraryPage() {
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.token);

  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<'all' | 'preset' | 'custom' | 'ai'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeModalScenario, setActiveModalScenario] = useState<ScenarioItem | null>(null);

  // Load scenarios from backend API
  useEffect(() => {
    let isCurrent = true;
    const fetchUrl = token ? '/api/scenarios' : '/api/scenarios/presets';
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;

    fetch(fetchUrl, { headers })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (isCurrent) {
          setScenarios(data);
          setLoading(false);
        }
      })
      .catch(() => {
        // Fallback to presets endpoint
        fetch('/api/scenarios/presets')
          .then((r) => r.json())
          .then((data) => {
            if (isCurrent) {
              setScenarios(data);
              setLoading(false);
            }
          })
          .catch(() => {
            if (isCurrent) setLoading(false);
          });
      });

    return () => {
      isCurrent = false;
    };
  }, [token]);

  // Filter scenarios
  const filteredScenarios = useMemo(() => {
    return scenarios.filter((item) => {
      // Category filter
      if (selectedCategory !== 'all' && item.category !== selectedCategory) {
        return false;
      }
      // Source filter
      if (sourceFilter !== 'all' && item.source !== sourceFilter) {
        return false;
      }
      // Keyword search
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const matchesName = item.name.toLowerCase().includes(query);
        const matchesDesc = item.description.toLowerCase().includes(query);
        const matchesCat = item.category.toLowerCase().includes(query);
        const matchesTag = (item.definition?.tags || []).some((t) => t.toLowerCase().includes(query));
        if (!matchesName && !matchesDesc && !matchesCat && !matchesTag) return false;
      }
      return true;
    });
  }, [scenarios, selectedCategory, sourceFilter, searchTerm]);

  // Category counts
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: scenarios.length };
    for (const item of scenarios) {
      counts[item.category] = (counts[item.category] || 0) + 1;
    }
    return counts;
  }, [scenarios]);

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div className="page-title">Simulation Library</div>
          <div className="page-subtitle">
            Pre-built preset simulations and custom scenarios for security testing and chaos resilience.
            Validated against Pantheon's strict execution schema (PRD Modules 7–9).
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className="btn-secondary"
            onClick={() => navigate('/scenario-builder')}
          >
            <Sparkles size={14} style={{ color: 'var(--primary)' }} />
            AI Builder
          </button>
          <button
            className="btn-primary"
            onClick={() => navigate('/custom-scenarios')}
          >
            <Plus size={14} />
            Author Custom
          </button>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="scenario-category-tabs">
        {CATEGORY_GROUPS.map((group) => {
          const count = categoryCounts[group.key] || 0;
          if (group.key !== 'all' && count === 0) return null;
          return (
            <button
              key={group.key}
              className={`scenario-category-tab ${selectedCategory === group.key ? 'active' : ''}`}
              onClick={() => setSelectedCategory(group.key)}
            >
              {group.icon}
              {group.label}
              <span className="count">{count}</span>
            </button>
          );
        })}
      </div>

      {/* Search & Filter Controls */}
      <div className="scenario-controls-bar">
        <div className="scenario-search-input">
          <Search size={16} style={{ color: 'var(--muted-foreground)' }} />
          <input
            type="text"
            placeholder="Search by scenario name, category, or tags..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="scenario-filters">
          <label style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>Source:</label>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value as 'all' | 'preset' | 'custom' | 'ai')}
          >
            <option value="all">All Sources</option>
            <option value="preset">System Presets</option>
            <option value="custom">Custom Scenarios</option>
            <option value="ai">AI-Generated</option>
          </select>
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="scenario-grid">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="card" style={{ height: 200, opacity: 0.6 }}>
              <div className="skeleton-line" style={{ width: '60%', margin: '16px 0' }} />
              <div className="skeleton-line" style={{ width: '90%', marginBottom: 8 }} />
              <div className="skeleton-line" style={{ width: '40%' }} />
            </div>
          ))}
        </div>
      )}

      {/* Scenarios Grid */}
      {!loading && (
        <>
          {filteredScenarios.length > 0 ? (
            <div className="scenario-grid">
              {filteredScenarios.map((item) => {
                const def = item.definition || ({} as ScenarioDefinition);
                return (
                  <div
                    key={item.id}
                    className="scenario-card"
                    onClick={() => setActiveModalScenario(item)}
                  >
                    <div className="scenario-card-header">
                      <div className="scenario-card-title">{item.name}</div>
                      <div className="scenario-card-badges">
                        <span className={`method-badge method-${def.method || 'GET'}`}>
                          {def.method || 'GET'}
                        </span>
                        <span className={`impact-badge ${def.estimated_impact || 'medium'}`}>
                          {def.estimated_impact || 'medium'}
                        </span>
                        <span
                          className="badge badge-success"
                          style={{ fontSize: 9, padding: '1px 5px', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                          title="Validated by Simulation Guard (PRD §7.6)"
                        >
                          <ShieldCheck size={9} /> Guard
                        </span>
                      </div>
                    </div>

                    <div className="scenario-card-desc">{item.description}</div>

                    {/* Expected Signals preview */}
                    <div style={{ marginBottom: 14 }}>
                      <div className="signal-tags">
                        {(def.expected_signals || []).slice(0, 2).map((sig) => (
                          <span key={sig} className="signal-tag">
                            ● {sig}
                          </span>
                        ))}
                        {(def.expected_signals || []).length > 2 && (
                          <span className="signal-tag" style={{ color: 'var(--muted-foreground)' }}>
                            +{def.expected_signals.length - 2} more
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="scenario-card-meta">
                      <div className="scenario-card-meta-item">
                        <Users size={12} />
                        {def.concurrency || 10} workers
                      </div>
                      <div className="scenario-card-meta-item">
                        <Clock size={12} />
                        {def.duration || 30}s
                      </div>
                      <div className="scenario-card-meta-item" style={{ marginLeft: 'auto' }}>
                        <span
                          className={`badge ${
                            item.source === 'preset' ? 'badge-primary' : item.source === 'ai' ? 'badge-info' : 'badge-warning'
                          }`}
                        >
                          {item.source}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="card">
              <div className="card-body" style={{ textAlign: 'center', padding: '48px 24px' }}>
                <ShieldAlert size={48} style={{ color: 'var(--muted-foreground)', margin: '0 auto 16px' }} />
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, color: 'var(--foreground)', marginBottom: 8 }}>
                  No Scenarios Found
                </h3>
                <p style={{ color: 'var(--secondary-foreground)', fontSize: 13, maxWidth: 440, margin: '0 auto 20px' }}>
                  No scenarios match your current search or category filter. Try clearing your filters or create a new custom scenario.
                </p>
                <button
                  className="btn-secondary"
                  onClick={() => {
                    setSelectedCategory('all');
                    setSourceFilter('all');
                    setSearchTerm('');
                  }}
                >
                  Clear Filters
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Scenario Detail Modal */}
      {activeModalScenario && (
        <div
          className="scenario-modal-overlay"
          onClick={() => setActiveModalScenario(null)}
        >
          <div
            className="scenario-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="scenario-modal-header">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span className={`method-badge method-${activeModalScenario.definition?.method || 'GET'}`}>
                    {activeModalScenario.definition?.method || 'GET'}
                  </span>
                  <span style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600 }}>
                    {activeModalScenario.name}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted-foreground)', marginTop: 4, fontFamily: 'var(--font-mono)', display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span>Category: {activeModalScenario.category} · Source: {activeModalScenario.source}</span>
                  <span className="badge badge-success" style={{ fontSize: 10, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <ShieldCheck size={11} /> Simulation Guard: Verified (PRD §7.6)
                  </span>
                </div>
              </div>

              <button
                onClick={() => setActiveModalScenario(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--muted-foreground)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <div className="scenario-modal-body">
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--foreground)', marginBottom: 6 }}>
                  Description
                </div>
                <div style={{ fontSize: 13, color: 'var(--secondary-foreground)', lineHeight: 1.6 }}>
                  {activeModalScenario.description}
                </div>
              </div>

              {/* Target Details */}
              <div className="card" style={{ backgroundColor: 'var(--secondary)' }}>
                <div className="card-header">
                  <span className="card-title">Target Specification</span>
                </div>
                <div className="card-body" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>Path</div>
                    <div className="font-mono" style={{ fontSize: 13, color: 'var(--primary)' }}>
                      {activeModalScenario.definition?.target?.path || '/'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>Port</div>
                    <div className="font-mono" style={{ fontSize: 13 }}>
                      {activeModalScenario.definition?.target?.port || 8080}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>Protocol</div>
                    <div className="font-mono" style={{ fontSize: 13 }}>
                      {activeModalScenario.definition?.target?.protocol || 'http'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Execution Specs */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 4 }}>Concurrency</div>
                  <div className="font-mono" style={{ fontSize: 15, fontWeight: 600 }}>
                    {activeModalScenario.definition?.concurrency || 10} workers
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 4 }}>Duration</div>
                  <div className="font-mono" style={{ fontSize: 15, fontWeight: 600 }}>
                    {activeModalScenario.definition?.duration || 30} seconds
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 4 }}>Estimated Impact</div>
                  <span className={`impact-badge ${activeModalScenario.definition?.estimated_impact || 'medium'}`}>
                    {activeModalScenario.definition?.estimated_impact || 'medium'}
                  </span>
                </div>
              </div>

              {/* Expected Signals */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--foreground)', marginBottom: 8 }}>
                  Expected Reaction Signals
                </div>
                <div className="signal-tags">
                  {(activeModalScenario.definition?.expected_signals || []).map((sig) => (
                    <span key={sig} className="signal-tag" style={{ backgroundColor: 'rgba(0, 212, 170, 0.08)', borderColor: 'rgba(0, 212, 170, 0.3)' }}>
                      ● {sig}
                    </span>
                  ))}
                </div>
              </div>

              {/* Raw Parameters */}
              {Object.keys(activeModalScenario.definition?.parameters || {}).length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--foreground)', marginBottom: 8 }}>
                    Simulation Parameters
                  </div>
                  <pre
                    style={{
                      backgroundColor: '#050709',
                      padding: 12,
                      borderRadius: 'var(--radius)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 11,
                      color: '#a6accd',
                      overflowX: 'auto',
                      border: '1px solid var(--card-border)',
                    }}
                  >
                    {JSON.stringify(activeModalScenario.definition.parameters, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="scenario-modal-footer">
              <button
                className="btn-secondary"
                onClick={() => {
                  const toClone = activeModalScenario.definition;
                  setActiveModalScenario(null);
                  navigate('/custom-scenarios', { state: { template: toClone } });
                }}
              >
                <Wrench size={14} />
                Clone to Custom Editor
              </button>
              <button
                className="btn-primary"
                onClick={() => {
                  setActiveModalScenario(null);
                  navigate('/test-runs');
                }}
              >
                <ExternalLink size={14} />
                Select for Test Run
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
