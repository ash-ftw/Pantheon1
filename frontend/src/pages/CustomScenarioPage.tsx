/**
 * CustomScenarioPage — PRD Module 9 (Phase 6)
 *
 * Custom Scenario Authoring:
 * - Structured Visual Form + JSON Editor dual mode
 * - Real-time validation against the shared backend ScenarioDefinition schema
 * - Preset loader: prefill from any of the 13 built-in presets or cloned template
 * - Concurrency, duration boundaries, target specification, expected signals
 * - Save to tenant scenario library
 */

import {
  AlertCircle,
  CheckCircle2,
  Code,
  FileText,
  Loader2,
  Plus,
  RotateCcw,
  Save,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';

import { useAuthStore } from '../stores/authStore';
import type { ScenarioDefinition } from './SimulationLibraryPage';

import './ScenarioPages.css';

const DEFAULT_SCENARIO: ScenarioDefinition = {
  name: 'Custom Resilience Simulation',
  description: 'Custom security simulation evaluating service resilience under load.',
  category: 'api_abuse',
  target: {
    service: 'app-workload',
    path: '/api',
    port: 8080,
    protocol: 'http',
  },
  method: 'GET',
  payload_category: 'custom_probes',
  concurrency: 15,
  duration: 30,
  expected_signals: ['http_429_too_many_requests'],
  parameters: {},
  estimated_impact: 'medium',
  estimated_duration_seconds: 30,
  source: 'custom',
  tags: ['custom'],
};

const CATEGORIES = [
  { value: 'brute_force', label: 'Brute Force' },
  { value: 'credential_guessing', label: 'Credential Guessing' },
  { value: 'sqli_resilience', label: 'SQL Injection' },
  { value: 'xss_reflection', label: 'XSS Reflection' },
  { value: 'auth_abuse', label: 'Auth & JWT Abuse' },
  { value: 'bola', label: 'BOLA / IDOR' },
  { value: 'api_abuse', label: 'API Abuse & Rate Limits' },
  { value: 'cache_pressure', label: 'Cache Pressure' },
  { value: 'traffic_flood', label: 'Traffic Flood' },
  { value: 'service_failure', label: 'Service Failure (Chaos)' },
  { value: 'network_partition', label: 'Network Partition (Chaos)' },
  { value: 'resource_exhaustion', label: 'Resource Starvation (Chaos)' },
  { value: 'multi_stage_chain', label: 'Multi-Stage Chain' },
];

const METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'POD_KILL', 'NETWORK_DELAY', 'CPU_STRESS', 'CHAINED_HTTP'];

export function CustomScenarioPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const token = useAuthStore((s) => s.token);

  // Template from navigation state (if cloned from library or AI builder)
  const templateScenario = location.state?.template as ScenarioDefinition | undefined;

  const [mode, setMode] = useState<'form' | 'json'>('form');
  const [scenario, setScenario] = useState<ScenarioDefinition>(templateScenario || DEFAULT_SCENARIO);
  const [jsonText, setJsonText] = useState<string>(
    JSON.stringify(templateScenario || DEFAULT_SCENARIO, null, 2),
  );

  const [newSignal, setNewSignal] = useState('');
  const [presets, setPresets] = useState<{ name: string; definition: ScenarioDefinition }[]>([]);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; errors: string[] } | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSafetyModal, setShowSafetyModal] = useState(false);
  const [safetyPolicies, setSafetyPolicies] = useState<{
    permitted_categories: string[];
    permanently_disallowed_classes: string[];
    scope_constraints: string[];
    enforcement_level: string;
  } | null>(null);

  // Load presets for "Load Template" dropdown
  useEffect(() => {
    fetch('/api/scenarios/presets')
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setPresets(data))
      .catch(() => {});

    fetch('/api/safety/policies')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setSafetyPolicies(data))
      .catch(() => {});
  }, []);

  // Sync Form -> JSON
  const updateScenarioField = <K extends keyof ScenarioDefinition>(key: K, value: ScenarioDefinition[K]) => {
    const updated = { ...scenario, [key]: value };
    setScenario(updated);
    setJsonText(JSON.stringify(updated, null, 2));
    setValidationResult(null);
  };

  // Sync JSON -> Form
  const handleJsonChange = (text: string) => {
    setJsonText(text);
    setValidationResult(null);
    try {
      const parsed = JSON.parse(text);
      setScenario(parsed);
    } catch {
      // JSON is mid-edit, do not break form state
    }
  };

  // Preload preset template
  const handleLoadPreset = (name: string) => {
    const found = presets.find((p) => p.name === name);
    if (found?.definition) {
      setScenario(found.definition);
      setJsonText(JSON.stringify(found.definition, null, 2));
      setValidationResult(null);
    }
  };

  // Validate scenario against backend Pydantic schema
  const handleValidate = async () => {
    setValidating(true);
    setError(null);
    setValidationResult(null);

    let defToValidate = scenario;
    if (mode === 'json') {
      try {
        defToValidate = JSON.parse(jsonText);
      } catch (err) {
        setValidating(false);
        setValidationResult({
          valid: false,
          errors: [`JSON Syntax Error: ${err instanceof Error ? err.message : 'Invalid JSON'}`],
        });
        return;
      }
    }

    try {
      const res = await fetch('/api/scenarios/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ definition: defToValidate }),
      });

      const data = await res.json();
      setValidationResult({
        valid: data.valid,
        errors: data.errors || [],
      });
      if (data.valid && data.normalized_definition) {
        setScenario(data.normalized_definition);
        setJsonText(JSON.stringify(data.normalized_definition, null, 2));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation request failed');
    } finally {
      setValidating(false);
    }
  };

  // Save custom scenario
  const handleSave = async () => {
    if (!token) {
      setError('You must be logged in to save scenarios');
      return;
    }

    setSaving(true);
    setError(null);
    setSaveSuccess(false);

    let defToSave = scenario;
    if (mode === 'json') {
      try {
        defToSave = JSON.parse(jsonText);
      } catch (err) {
        setSaving(false);
        setError(`JSON syntax error: ${err instanceof Error ? err.message : 'Invalid JSON'}`);
        return;
      }
    }

    try {
      const res = await fetch('/api/scenarios', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: defToSave.name,
          description: defToSave.description,
          category: defToSave.category,
          definition: defToSave,
          source: 'custom',
          is_preset: false,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail?.message || errData.detail || `Server returned ${res.status}`);
      }

      setSaveSuccess(true);
      setTimeout(() => navigate('/scenarios'), 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save scenario');
    } finally {
      setSaving(false);
    }
  };

  // Add expected signal
  const handleAddSignal = () => {
    if (!newSignal.trim()) return;
    const current = scenario.expected_signals || [];
    if (!current.includes(newSignal.trim())) {
      updateScenarioField('expected_signals', [...current, newSignal.trim()]);
    }
    setNewSignal('');
  };

  // Remove expected signal
  const handleRemoveSignal = (sig: string) => {
    const current = scenario.expected_signals || [];
    updateScenarioField('expected_signals', current.filter((s) => s !== sig));
  };

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div className="page-title">Custom Scenario Authoring</div>
          <div className="page-subtitle">
            Author custom security simulations or chaos engineering tests against Pantheon's strict Pydantic schema.
            Use the visual form or edit raw JSON with live validation.
          </div>
        </div>

        {/* Mode Switcher + Safety Policies + Preset Preloader */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <button
            className="btn-secondary"
            style={{ padding: '6px 11px', fontSize: 11 }}
            onClick={() => setShowSafetyModal(true)}
          >
            <Shield size={12} style={{ color: 'var(--primary)' }} />
            Safety Guard Policies
          </button>

          {presets.length > 0 && (
            <select
              onChange={(e) => handleLoadPreset(e.target.value)}
              style={{
                padding: '6px 10px',
                backgroundColor: 'var(--secondary)',
                border: '1px solid var(--card-border)',
                borderRadius: 'var(--radius)',
                color: 'var(--secondary-foreground)',
                fontSize: 12,
              }}
              defaultValue=""
            >
              <option value="" disabled>Preload Preset Template...</option>
              {presets.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                </option>
              ))}
            </select>
          )}

          <div className="editor-toggle">
            <button
              className={mode === 'form' ? 'active' : ''}
              onClick={() => setMode('form')}
            >
              <FileText size={12} style={{ display: 'inline', marginRight: 4 }} />
              Form Mode
            </button>
            <button
              className={mode === 'json' ? 'active' : ''}
              onClick={() => setMode('json')}
            >
              <Code size={12} style={{ display: 'inline', marginRight: 4 }} />
              JSON Mode
            </button>
          </div>
        </div>
      </div>

      {/* Validation Result Banner */}
      {validationResult && (
        <div className={`validation-banner ${validationResult.valid ? 'success' : 'error'} animate-slide-in`}>
          {validationResult.valid ? (
            <>
              <CheckCircle2 size={16} />
              <div>
                <strong>Simulation Guard & Schema Validated</strong> — Scenario complies strictly with Pantheon's execution specification and PRD §7.6 Safety Model boundaries.
              </div>
            </>
          ) : (
            <>
              <AlertCircle size={16} />
              <div>
                <div style={{ fontWeight: 600, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <ShieldAlert size={14} /> Validation & Safety Guard Violations:
                </div>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {validationResult.errors.map((err, idx) => (
                    <li key={idx} style={{ color: err.includes('Simulation Guard') ? '#f87171' : 'inherit' }}>
                      {err}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="validation-banner error animate-slide-in">
          <AlertCircle size={16} />
          <div>{error}</div>
        </div>
      )}

      {/* Save Success Banner */}
      {saveSuccess && (
        <div className="validation-banner success animate-slide-in">
          <CheckCircle2 size={16} />
          <div>Scenario saved! Redirecting to Simulation Library...</div>
        </div>
      )}

      {/* Form Mode View */}
      {mode === 'form' ? (
        <div className="card">
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Row 1: Title & Category */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 6 }}>
                  Scenario Title *
                </label>
                <input
                  type="text"
                  value={scenario.name}
                  onChange={(e) => updateScenarioField('name', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--secondary)',
                    border: '1px solid var(--card-border)',
                    borderRadius: 'var(--radius)',
                    color: 'var(--foreground)',
                    fontSize: 13,
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 6 }}>
                  Category *
                </label>
                <select
                  value={scenario.category}
                  onChange={(e) => updateScenarioField('category', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--secondary)',
                    border: '1px solid var(--card-border)',
                    borderRadius: 'var(--radius)',
                    color: 'var(--foreground)',
                    fontSize: 13,
                  }}
                >
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Description */}
            <div>
              <label style={{ display: 'block', fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 6 }}>
                Description *
              </label>
              <textarea
                value={scenario.description}
                onChange={(e) => updateScenarioField('description', e.target.value)}
                rows={2}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  backgroundColor: 'var(--secondary)',
                  border: '1px solid var(--card-border)',
                  borderRadius: 'var(--radius)',
                  color: 'var(--foreground)',
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              />
            </div>

            {/* Target Specification Box */}
            <div className="card" style={{ backgroundColor: 'var(--secondary)', padding: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--foreground)', marginBottom: 12 }}>
                Target Destination Specification
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 10, color: 'var(--muted-foreground)', marginBottom: 4 }}>
                    Method
                  </label>
                  <select
                    value={scenario.method}
                    onChange={(e) => updateScenarioField('method', e.target.value)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      backgroundColor: 'var(--card)',
                      border: '1px solid var(--card-border)',
                      borderRadius: 'var(--radius)',
                      color: 'var(--foreground)',
                      fontSize: 12,
                    }}
                  >
                    {METHODS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 10, color: 'var(--muted-foreground)', marginBottom: 4 }}>
                    Path
                  </label>
                  <input
                    type="text"
                    value={scenario.target?.path || '/'}
                    onChange={(e) =>
                      updateScenarioField('target', {
                        ...(scenario.target || { service: 'default', port: 8080, protocol: 'http' }),
                        path: e.target.value,
                      })
                    }
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      backgroundColor: 'var(--card)',
                      border: '1px solid var(--card-border)',
                      borderRadius: 'var(--radius)',
                      color: 'var(--foreground)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 12,
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 10, color: 'var(--muted-foreground)', marginBottom: 4 }}>
                    Port
                  </label>
                  <input
                    type="number"
                    value={scenario.target?.port || 8080}
                    onChange={(e) =>
                      updateScenarioField('target', {
                        ...(scenario.target || { service: 'default', path: '/', protocol: 'http' }),
                        port: parseInt(e.target.value) || 8080,
                      })
                    }
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      backgroundColor: 'var(--card)',
                      border: '1px solid var(--card-border)',
                      borderRadius: 'var(--radius)',
                      color: 'var(--foreground)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 12,
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 10, color: 'var(--muted-foreground)', marginBottom: 4 }}>
                    Protocol
                  </label>
                  <select
                    value={scenario.target?.protocol || 'http'}
                    onChange={(e) =>
                      updateScenarioField('target', {
                        ...(scenario.target || { service: 'default', path: '/', port: 8080 }),
                        protocol: e.target.value,
                      })
                    }
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      backgroundColor: 'var(--card)',
                      border: '1px solid var(--card-border)',
                      borderRadius: 'var(--radius)',
                      color: 'var(--foreground)',
                      fontSize: 12,
                    }}
                  >
                    <option value="http">http</option>
                    <option value="https">https</option>
                    <option value="grpc">grpc</option>
                    <option value="internal">internal</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Execution Parameters: Concurrency, Duration, Impact */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
              <div>
                <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 6 }}>
                  <span>Concurrency</span>
                  <span className="font-mono" style={{ color: 'var(--primary)' }}>{scenario.concurrency} workers</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={500}
                  value={scenario.concurrency}
                  onChange={(e) => updateScenarioField('concurrency', parseInt(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--primary)' }}
                />
              </div>

              <div>
                <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 6 }}>
                  <span>Duration</span>
                  <span className="font-mono" style={{ color: 'var(--primary)' }}>{scenario.duration} seconds</span>
                </label>
                <input
                  type="range"
                  min={5}
                  max={600}
                  value={scenario.duration}
                  onChange={(e) => {
                    const dur = parseInt(e.target.value);
                    updateScenarioField('duration', dur);
                    updateScenarioField('estimated_duration_seconds', dur);
                  }}
                  style={{ width: '100%', accentColor: 'var(--primary)' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 6 }}>
                  Estimated Impact
                </label>
                <select
                  value={scenario.estimated_impact}
                  onChange={(e) => updateScenarioField('estimated_impact', e.target.value as 'low' | 'medium' | 'high' | 'critical')}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--secondary)',
                    border: '1px solid var(--card-border)',
                    borderRadius: 'var(--radius)',
                    color: 'var(--foreground)',
                    fontSize: 13,
                  }}
                >
                  <option value="low">Low Impact</option>
                  <option value="medium">Medium Impact</option>
                  <option value="high">High Impact</option>
                  <option value="critical">Critical Impact</option>
                </select>
              </div>
            </div>

            {/* Expected Signals Tag Manager */}
            <div>
              <label style={{ display: 'block', fontSize: 11, color: 'var(--muted-foreground)', marginBottom: 6 }}>
                Expected Defense & Detection Signals (Min 1 required)
              </label>
              <div className="signal-tags" style={{ marginBottom: 10 }}>
                {(scenario.expected_signals || []).map((sig) => (
                  <span key={sig} className="signal-tag" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <span>● {sig}</span>
                    <button
                      onClick={() => handleRemoveSignal(sig)}
                      style={{ background: 'transparent', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: 0 }}
                    >
                      <Trash2 size={11} />
                    </button>
                  </span>
                ))}
              </div>

              <div style={{ display: 'flex', gap: 8, maxWidth: 400 }}>
                <input
                  type="text"
                  placeholder="e.g. http_429_rate_limited, waf_blocked..."
                  value={newSignal}
                  onChange={(e) => setNewSignal(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddSignal();
                    }
                  }}
                  style={{
                    flex: 1,
                    padding: '6px 10px',
                    backgroundColor: 'var(--secondary)',
                    border: '1px solid var(--card-border)',
                    borderRadius: 'var(--radius)',
                    color: 'var(--foreground)',
                    fontSize: 12,
                  }}
                />
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleAddSignal}
                  style={{ padding: '6px 12px' }}
                >
                  <Plus size={12} /> Add
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* JSON Mode View */
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="card-title">Raw Scenario Definition JSON</span>
            <button
              className="btn-secondary"
              style={{ padding: '4px 10px', fontSize: 11 }}
              onClick={() => {
                setJsonText(JSON.stringify(scenario, null, 2));
                setValidationResult(null);
              }}
            >
              <RotateCcw size={11} /> Re-format JSON
            </button>
          </div>
          <div className="card-body">
            <textarea
              className="scenario-code-editor"
              value={jsonText}
              onChange={(e) => handleJsonChange(e.target.value)}
              spellCheck={false}
            />
          </div>
        </div>
      )}

      {/* Action Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 24 }}>
        <button
          className="btn-secondary"
          onClick={handleValidate}
          disabled={validating}
        >
          {validating ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
          Validate Schema
        </button>

        <button
          className="btn-primary"
          onClick={handleSave}
          disabled={saving || saveSuccess}
        >
          {saving ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save size={14} />
              Save Scenario
            </>
          )}
        </button>
      </div>

      {/* Safety Guard Policies Modal */}
      {showSafetyModal && (
        <div
          className="scenario-modal-overlay"
          onClick={() => setShowSafetyModal(false)}
        >
          <div
            className="scenario-modal"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 640 }}
          >
            <div className="scenario-modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <ShieldCheck size={20} style={{ color: 'var(--primary)' }} />
                <span className="card-title">Pantheon Safety Model (PRD §7.6)</span>
              </div>
              <button
                onClick={() => setShowSafetyModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--muted-foreground)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="scenario-modal-body" style={{ fontSize: 13, lineHeight: 1.6 }}>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--foreground)', marginBottom: 6 }}>
                  Permanently Disallowed Attack Classes (FR-6.2)
                </div>
                <div style={{ fontSize: 12, color: 'var(--secondary-foreground)', marginBottom: 8 }}>
                  Hard-coded in code with zero configuration path to bypass:
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, color: '#f87171', fontSize: 12 }}>
                  {(safetyPolicies?.permanently_disallowed_classes || [
                    'Real malware, rootkits, and Trojan payloads',
                    'Persistence mechanisms (crontabs, autoruns, backdoor user creation)',
                    'Credential theft against real external accounts',
                    'Reverse shells and interactive TTY command injection',
                    'Ransomware and mass file destruction',
                    'Data exfiltration to external webhooks and public endpoints',
                  ]).map((item, idx) => (
                    <li key={idx} style={{ marginBottom: 4 }}>{item}</li>
                  ))}
                </ul>
              </div>

              <div>
                <div style={{ fontWeight: 600, color: 'var(--foreground)', marginBottom: 6 }}>
                  Tenant Scope Boundaries (FR-6.3)
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--secondary-foreground)', fontSize: 12 }}>
                  {(safetyPolicies?.scope_constraints || [
                    'Simulations must target strictly within the customer tenant namespace',
                    'Public internet IP addresses and external domain names are prohibited',
                    'Cloud provider metadata endpoints (169.254.169.254) are permanently blocked',
                  ]).map((item, idx) => (
                    <li key={idx} style={{ marginBottom: 4 }}>{item}</li>
                  ))}
                </ul>
              </div>

              <div style={{ padding: 10, backgroundColor: 'rgba(0, 212, 170, 0.08)', borderRadius: 'var(--radius)', border: '1px solid rgba(0, 212, 170, 0.2)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
                All safety rejections are automatically logged to the audit log (FR-6.4).
              </div>
            </div>

            <div className="scenario-modal-footer">
              <button
                className="btn-primary"
                onClick={() => setShowSafetyModal(false)}
              >
                Close Policies
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
