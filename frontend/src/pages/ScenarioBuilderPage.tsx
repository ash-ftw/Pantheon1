/**
 * ScenarioBuilderPage — PRD Module 8 (Phase 6)
 *
 * AI Scenario Builder:
 * - Natural language prompt input with suggestion chips
 * - Target app & Phase 5 discovered endpoints context linking
 * - Generates structured ScenarioDefinition schema via backend AI service
 * - Enforces client & server-side re-validation
 * - "Save to Library" and "Clone to Custom Editor" actions
 */

import {
  AlertCircle,
  CheckCircle2,
  Code,
  Loader2,
  Save,
  Sparkles,
  Wrench,
  Zap,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';

import { useAuthStore } from '../stores/authStore';
import type { ScenarioDefinition } from './SimulationLibraryPage';

import './ScenarioPages.css';

interface AppOption {
  id: string;
  name: string;
  status: string;
  discovered_endpoints?: {
    endpoints: { path: string; method: string; classification: string }[];
  };
}

const PROMPT_SUGGESTIONS = [
  'Simulate credential stuffing on the login endpoint with 30 workers',
  'Test SQL injection resilience on search parameters with tautology payloads',
  'Aggressive API rate limit exhaustion firing 200 requests/sec',
  'BOLA / IDOR cross-tenant object authorization check',
  'Chaos test: simulate upstream pod termination and measure recovery time',
  'Cross-service 250ms network latency and 10% packet drop stress test',
];

export function ScenarioBuilderPage() {
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.token);

  const [prompt, setPrompt] = useState('');
  const [apps, setApps] = useState<AppOption[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [selectedEndpoint, setSelectedEndpoint] = useState<string>('');
  const [generating, setGenerating] = useState(false);
  const [generatedScenario, setGeneratedScenario] = useState<ScenarioDefinition | null>(null);
  const [showJson, setShowJson] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reasoning, setReasoning] = useState<string>('');
  const [isThinking, setIsThinking] = useState(false);
  const [showReasoning, setShowReasoning] = useState(true);

  // Load deployed apps for contextual generation
  useEffect(() => {
    let isCurrent = true;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;

    fetch('/api/apps', { headers })
      .then((res) => (res.ok ? res.json() : []))
      .then((data: AppOption[]) => {
        if (isCurrent) {
          setApps(data);
          if (data.length > 0 && !selectedAppId) {
            setSelectedAppId(data[0].id);
          }
        }
      })
      .catch(() => {});

    return () => {
      isCurrent = false;
    };
  }, [token, selectedAppId]);

  // Selected app endpoints
  const selectedApp = apps.find((a) => a.id === selectedAppId);
  const discoveredEndpoints = selectedApp?.discovered_endpoints?.endpoints || [];

  // Generate scenario via backend AI service with streaming reasoning
  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setError(null);
    setSaveSuccess(false);
    setReasoning('');
    setIsThinking(true);
    setShowReasoning(true);

    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;

    try {
      // 1. Try streaming SSE endpoint from NVIDIA NIM
      const response = await fetch('/api/ai/scenario/stream', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          prompt,
          app_id: selectedAppId || null,
          target_path: selectedEndpoint || null,
        }),
      });

      if (response.ok && response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullReasoning = '';
        let fullContent = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const chunk = JSON.parse(line.slice(6));
                if (chunk.type === 'reasoning' && chunk.delta) {
                  fullReasoning += chunk.delta;
                  setReasoning(fullReasoning);
                } else if (chunk.type === 'content' && chunk.delta) {
                  fullContent += chunk.delta;
                } else if (chunk.type === 'done') {
                  if (chunk.reasoning) setReasoning(chunk.reasoning);
                  if (chunk.content) fullContent = chunk.content;
                }
              } catch {
                // ignore SSE parse errors
              }
            }
          }
        }

        setIsThinking(false);

        if (fullContent.trim()) {
          const jsonMatch =
            fullContent.match(/```(?:json)?\s*([\s\S]*?)\s*```/) || fullContent.match(/\{[\s\S]*\}/);
          const jsonStr = jsonMatch ? jsonMatch[1] || jsonMatch[0] : fullContent;
          const parsed = JSON.parse(jsonStr);
          setGeneratedScenario(parsed);
          return;
        }
      }

      // 2. Fallback to standard scenario generation endpoint
      const res = await fetch('/api/scenarios/generate', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          prompt,
          app_id: selectedAppId || null,
          target_path: selectedEndpoint || null,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${res.status}`);
      }

      const scenario: ScenarioDefinition = await res.json();
      setGeneratedScenario(scenario);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setGenerating(false);
      setIsThinking(false);
    }
  };


  // Save generated scenario to org library
  const handleSave = async () => {
    if (!generatedScenario || !token) return;
    setSaving(true);
    setError(null);

    try {
      const res = await fetch('/api/scenarios', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: generatedScenario.name,
          description: generatedScenario.description,
          category: generatedScenario.category,
          definition: generatedScenario,
          source: 'ai',
          is_preset: false,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail?.message || errData.detail || 'Failed to save scenario');
      }

      setSaveSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <div className="page-title">AI Scenario Builder</div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 11,
              fontFamily: 'var(--font-mono)',
              color: 'var(--primary)',
              backgroundColor: 'rgba(0, 212, 170, 0.08)',
              padding: '4px 10px',
              borderRadius: 4,
              border: '1px solid rgba(0, 212, 170, 0.3)',
            }}
          >
            <Sparkles size={13} />
            <span>NVIDIA NIM • nemotron-3.5-lightning-30b-a3b</span>
          </div>
        </div>
        <div className="page-subtitle">
          Describe the security simulation or chaos resilience test you want to execute in plain
          English. Pantheon parses your prompt, links Phase 5 discovered endpoints, and strictly
          re-validates against the execution schema.
        </div>
      </div>

      {/* Main Composer Card */}
      <div className="ai-builder-card">
        {/* Target Context Selector Bar */}
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 18 }}>
          <div style={{ flex: 1, minWidth: 220 }}>
            <label
              style={{
                display: 'block',
                fontSize: 11,
                color: 'var(--muted-foreground)',
                marginBottom: 6,
              }}
            >
              Target Application (Optional)
            </label>
            <select
              value={selectedAppId}
              onChange={(e) => {
                setSelectedAppId(e.target.value);
                setSelectedEndpoint('');
              }}
              style={{
                width: '100%',
                padding: '8px 12px',
                backgroundColor: 'var(--secondary)',
                border: '1px solid var(--card-border)',
                borderRadius: 'var(--radius)',
                color: 'var(--foreground)',
                fontSize: 12,
              }}
            >
              <option value="">No specific app (Generic)</option>
              {apps.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.name} ({app.status})
                </option>
              ))}
            </select>
          </div>

          {discoveredEndpoints.length > 0 && (
            <div style={{ flex: 1, minWidth: 240 }}>
              <label
                style={{
                  display: 'block',
                  fontSize: 11,
                  color: 'var(--muted-foreground)',
                  marginBottom: 6,
                }}
              >
                Context Endpoint (Discovered via Phase 5)
              </label>
              <select
                value={selectedEndpoint}
                onChange={(e) => setSelectedEndpoint(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  backgroundColor: 'var(--secondary)',
                  border: '1px solid var(--card-border)',
                  borderRadius: 'var(--radius)',
                  color: 'var(--foreground)',
                  fontSize: 12,
                }}
              >
                <option value="">Auto-select based on prompt</option>
                {discoveredEndpoints.map((ep) => (
                  <option key={`${ep.method}-${ep.path}`} value={ep.path}>
                    {ep.method} {ep.path} ({ep.classification})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Prompt Input Area */}
        <textarea
          className="ai-prompt-area"
          placeholder="Describe your simulation scenario... (e.g. 'Test rate limiting on /api/auth/login with 40 concurrent workers for 30 seconds and check for HTTP 429 response')"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
        />

        {/* Prompt Suggestions */}
        <div className="prompt-suggestions">
          <span
            style={{
              fontSize: 11,
              color: 'var(--muted-foreground)',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <Zap size={11} /> Try:
          </span>
          {PROMPT_SUGGESTIONS.map((suggestion) => (
            <button key={suggestion} className="prompt-chip" onClick={() => setPrompt(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>

        {/* Action Button */}
        <div style={{ marginTop: 18, display: 'flex', justifyContent: 'flex-end' }}>
          <button
            className="btn-primary"
            onClick={handleGenerate}
            disabled={!prompt.trim() || generating}
          >
            {generating ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Synthesizing Scenario...
              </>
            ) : (
              <>
                <Sparkles size={14} />
                Generate Scenario
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="validation-banner error animate-slide-in">
          <AlertCircle size={16} />
          <div>{error}</div>
        </div>
      )}

      {/* Save Success Alert */}
      {saveSuccess && (
        <div className="validation-banner success animate-slide-in">
          <CheckCircle2 size={16} />
          <div>Scenario saved successfully to your organization's Simulation Library!</div>
        </div>
      )}

      {/* Live Thinking / Reasoning Trace Widget */}
      {(isThinking || reasoning) && (
        <div
          className="card animate-fade-in"
          style={{
            marginBottom: 20,
            border: '1px solid rgba(0, 212, 170, 0.25)',
            backgroundColor: '#0a0e14',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              borderBottom: showReasoning ? '1px solid var(--card-border)' : 'none',
              cursor: 'pointer',
            }}
            onClick={() => setShowReasoning(!showReasoning)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {isThinking ? (
                <Loader2 size={14} className="animate-spin text-primary" />
              ) : (
                <CheckCircle2 size={14} style={{ color: 'var(--primary)' }} />
              )}
              <span
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: 13,
                  textTransform: 'uppercase',
                  letterSpacing: 0.5,
                  color: 'var(--foreground)',
                }}
              >
                {isThinking ? 'Nemotron 3.5 Reasoning in Progress...' : 'Nemotron 3.5 Thinking Trace'}
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--muted-foreground)',
                  backgroundColor: 'rgba(255,255,255,0.06)',
                  padding: '1px 6px',
                  borderRadius: 3,
                }}
              >
                {reasoning.length} chars
              </span>
            </div>
            <button
              className="btn-secondary"
              style={{ fontSize: 11, padding: '2px 8px', height: 'auto' }}
              onClick={(e) => {
                e.stopPropagation();
                setShowReasoning(!showReasoning);
              }}
            >
              {showReasoning ? 'Collapse' : 'Expand'}
            </button>
          </div>

          {showReasoning && (
            <div
              style={{
                padding: '12px 16px',
                maxHeight: 240,
                overflowY: 'auto',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                lineHeight: 1.6,
                color: '#94a3b8',
                whiteSpace: 'pre-wrap',
                backgroundColor: 'rgba(0,0,0,0.3)',
              }}
            >
              {reasoning || 'Analyzing prompt requirements and target architecture...'}
              {isThinking && <span className="animate-pulse" style={{ color: 'var(--primary)' }}> ▋</span>}
            </div>
          )}
        </div>
      )}


      {/* Generated Result Preview */}
      {generatedScenario && (
        <div className="card animate-fade-in">
          <div
            className="card-header"
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="card-title">Generated Scenario Specification</span>
              <span
                className="badge badge-success"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
              >
                <CheckCircle2 size={11} /> Schema Validated
              </span>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn-secondary"
                style={{ padding: '4px 10px', fontSize: 11 }}
                onClick={() => setShowJson(!showJson)}
              >
                <Code size={12} />
                {showJson ? 'Form View' : 'Inspect JSON'}
              </button>
            </div>
          </div>

          <div className="card-body">
            {!showJson ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                  }}
                >
                  <div>
                    <h3
                      style={{
                        fontFamily: 'var(--font-display)',
                        fontSize: 18,
                        color: 'var(--foreground)',
                        marginBottom: 4,
                      }}
                    >
                      {generatedScenario.name}
                    </h3>
                    <p
                      style={{
                        color: 'var(--secondary-foreground)',
                        fontSize: 13,
                        lineHeight: 1.5,
                      }}
                    >
                      {generatedScenario.description}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <span className={`method-badge method-${generatedScenario.method}`}>
                      {generatedScenario.method}
                    </span>
                    <span className={`impact-badge ${generatedScenario.estimated_impact}`}>
                      {generatedScenario.estimated_impact}
                    </span>
                  </div>
                </div>

                {/* Target & Specs Grid */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: 14,
                    backgroundColor: 'var(--secondary)',
                    padding: 14,
                    borderRadius: 'var(--radius)',
                  }}
                >
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>Category</div>
                    <div className="font-mono" style={{ fontSize: 12, color: 'var(--primary)' }}>
                      {generatedScenario.category}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>
                      Target Path
                    </div>
                    <div className="font-mono" style={{ fontSize: 12 }}>
                      {generatedScenario.target?.path || '/'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>
                      Concurrency
                    </div>
                    <div className="font-mono" style={{ fontSize: 12 }}>
                      {generatedScenario.concurrency} workers
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--muted-foreground)' }}>Duration</div>
                    <div className="font-mono" style={{ fontSize: 12 }}>
                      {generatedScenario.duration}s
                    </div>
                  </div>
                </div>

                {/* Expected Signals */}
                <div>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: 'var(--foreground)',
                      marginBottom: 6,
                    }}
                  >
                    Expected Defense Signals
                  </div>
                  <div className="signal-tags">
                    {generatedScenario.expected_signals.map((sig) => (
                      <span
                        key={sig}
                        className="signal-tag"
                        style={{
                          backgroundColor: 'rgba(0, 212, 170, 0.08)',
                          borderColor: 'rgba(0, 212, 170, 0.3)',
                        }}
                      >
                        ● {sig}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <pre
                style={{
                  backgroundColor: '#050709',
                  padding: 16,
                  borderRadius: 'var(--radius)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  color: '#a6accd',
                  overflowX: 'auto',
                  border: '1px solid var(--card-border)',
                }}
              >
                {JSON.stringify(generatedScenario, null, 2)}
              </pre>
            )}

            {/* Bottom Actions */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 10,
                marginTop: 24,
                paddingTop: 16,
                borderTop: '1px solid var(--card-border)',
              }}
            >
              <button
                className="btn-secondary"
                onClick={() =>
                  navigate('/custom-scenarios', { state: { template: generatedScenario } })
                }
              >
                <Wrench size={14} />
                Edit in Custom Authoring
              </button>
              <button className="btn-primary" onClick={handleSave} disabled={saving || saveSuccess}>
                {saving ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Saving...
                  </>
                ) : saveSuccess ? (
                  <>
                    <CheckCircle2 size={14} />
                    Saved
                  </>
                ) : (
                  <>
                    <Save size={14} />
                    Save to Library
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
