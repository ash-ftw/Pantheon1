import { useEffect, useRef, useState } from 'react';
import { Play, Pause, RotateCcw, Search, ShieldCheck } from 'lucide-react';
import type { FindingItem } from './types';

const MOCK_FINDINGS: FindingItem[] = [
  {
    id: 'f-101',
    cve: 'CVE-2026-2184',
    title: 'Kubelet Unauthenticated Read-Only Port Information Disclosure',
    severity: 'CRITICAL',
    category: 'Kubernetes',
    cvss: 9.8,
    timeDetected: '00:02:14',
    blastRadius: 'Cluster Admin Token Exfiltration',
  },
  {
    id: 'f-102',
    cve: 'CVE-2025-4819',
    title: 'BOLA Access in Billing Tenant Ingress Endpoint',
    severity: 'HIGH',
    category: 'API Surface',
    cvss: 8.6,
    timeDetected: '00:05:41',
    blastRadius: 'Cross-Tenant Customer PII Leak',
  },
  {
    id: 'f-103',
    cve: 'CVE-2025-3120',
    title: 'Cilium NetworkPolicy Ingress CIDR Over-Permissive Wildcard',
    severity: 'MEDIUM',
    category: 'Auth & RBAC',
    cvss: 6.4,
    timeDetected: '00:08:19',
    blastRadius: 'Pod-to-Pod Egress Tampering',
  },
  {
    id: 'f-104',
    cve: 'CVE-2024-9912',
    title: 'Stale CI/CD Service Account Token in ConfigMap',
    severity: 'LOW',
    category: 'Supply Chain',
    cvss: 3.9,
    timeDetected: '00:11:02',
    blastRadius: 'Read-Only Image Registry Metadata',
  },
];

export function Chapter06Trust() {
  const radarCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Replay scrubber state
  const [isPlaying, setIsPlaying] = useState(false);
  const [replayTime, setReplayTime] = useState(35); // seconds 0-100

  // Search & Filter for Findings demo
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  // Animated Radar-Sweep Canvas Visualizer
  useEffect(() => {
    const canvas = radarCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let angle = 0;
    const size = (canvas.width = canvas.height = canvas.offsetWidth || 280);
    const center = size / 2;
    const radius = center - 12;

    const blips = [
      { r: radius * 0.4, a: 1.2, size: 4, life: 1 },
      { r: radius * 0.7, a: 3.8, size: 5, life: 1 },
      { r: radius * 0.85, a: 5.1, size: 3.5, life: 1 },
    ];

    const render = () => {
      ctx.fillStyle = '#07090d';
      ctx.fillRect(0, 0, size, size);

      // Radar Concentric Circles
      ctx.strokeStyle = 'rgba(0, 212, 170, 0.2)';
      ctx.lineWidth = 1;
      for (let r = radius * 0.33; r <= radius; r += radius * 0.33) {
        ctx.beginPath();
        ctx.arc(center, center, r, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Crosshairs
      ctx.beginPath();
      ctx.moveTo(center, 10);
      ctx.lineTo(center, size - 10);
      ctx.moveTo(10, center);
      ctx.lineTo(size - 10, center);
      ctx.strokeStyle = 'rgba(0, 212, 170, 0.15)';
      ctx.stroke();

      // Radar sweep cone
      angle += 0.035;
      const gradient = ctx.createConicGradient(angle, center, center);
      gradient.addColorStop(0, 'rgba(0, 212, 170, 0.35)');
      gradient.addColorStop(0.1, 'rgba(0, 212, 170, 0.05)');
      gradient.addColorStop(0.25, 'rgba(0, 212, 170, 0)');
      gradient.addColorStop(1, 'rgba(0, 212, 170, 0)');

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(center, center, radius, 0, Math.PI * 2);
      ctx.fill();

      // Sweep edge line
      ctx.beginPath();
      ctx.moveTo(center, center);
      ctx.lineTo(center + Math.cos(angle) * radius, center + Math.sin(angle) * radius);
      ctx.strokeStyle = '#00d4aa';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Target Blips
      blips.forEach((blip) => {
        const bx = center + Math.cos(blip.a) * blip.r;
        const by = center + Math.sin(blip.a) * blip.r;

        ctx.beginPath();
        ctx.arc(bx, by, blip.size, 0, Math.PI * 2);
        ctx.fillStyle = '#ff6b35';
        ctx.shadowColor = '#ff6b35';
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, []);

  // Replay timer
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setReplayTime((prev) => (prev >= 100 ? 0 : prev + 1));
    }, 150);
    return () => clearInterval(interval);
  }, [isPlaying]);

  const filteredFindings = MOCK_FINDINGS.filter((f) => {
    const matchesSev = severityFilter === 'ALL' || f.severity === severityFilter;
    const matchesQuery =
      f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.cve.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.category.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSev && matchesQuery;
  });

  return (
    <section id="chapter-06" className="landing-chapter-section">
      <div className="landing-chapter-content">
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div className="chapter-eyebrow">06 // TRUST & PROOF</div>
          <h2 className="platform-headline" style={{ textAlign: 'center' }}>
            TESTED UNDER REAL ADVERSARIAL SIGNAL
          </h2>
          <p
            className="platform-subtext"
            style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto' }}
          >
            Over 1.8M attack payloads detonated across 420+ enterprise staging clusters. Proof in
            execution, not paper promises.
          </p>
        </div>

        <div className="trust-grid">
          {/* Left Column: Radar Scanner & Live Replay Scrubber */}
          <div>
            <div className="radar-sweep-card">
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  width: '100%',
                  alignItems: 'center',
                }}
              >
                <span className="font-mono text-xs" style={{ color: '#00d4aa' }}>
                  ACTIVE SCANNER // 360° BEAM
                </span>
                <span className="badge badge-success font-mono text-xs">SWEEPING</span>
              </div>

              <div className="radar-canvas-box">
                <canvas
                  ref={radarCanvasRef}
                  style={{ width: '100%', height: '100%', display: 'block' }}
                />
              </div>

              {/* Interactive Attack-Graph Replay Widget */}
              <div className="replay-scrubber-widget">
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 8,
                  }}
                >
                  <span className="font-mono text-xs" style={{ color: '#f1f5f9' }}>
                    ATTACK REPLAY // RUN #812-PROD-MOCK
                  </span>
                  <span className="font-mono text-xs" style={{ color: '#00d4aa' }}>
                    T+00:{String(replayTime).padStart(2, '0')}s
                  </span>
                </div>

                <div className="replay-controls-row">
                  <button
                    type="button"
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="btn-primary"
                    style={{ padding: '4px 10px', fontSize: 10 }}
                    data-testid="replay-play-btn"
                  >
                    {isPlaying ? <Pause size={12} /> : <Play size={12} />}
                  </button>

                  <button
                    type="button"
                    onClick={() => setReplayTime(0)}
                    className="btn-secondary"
                    style={{ padding: '4px 10px', fontSize: 10 }}
                  >
                    <RotateCcw size={12} />
                  </button>

                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={replayTime}
                    onChange={(e) => setReplayTime(Number(e.target.value))}
                    className="replay-slider"
                  />
                </div>
              </div>
            </div>

            {/* Posture Comparison Bars (Forge Movement) */}
            <div className="posture-comparison-bars">
              <div className="posture-bar-box">
                <div className="posture-bar-title">
                  <span>EXPLOIT SURFACE</span>
                  <span style={{ color: '#10b981' }}>-84% REDUCED</span>
                </div>
                <div className="posture-bar-track">
                  <div
                    className="posture-bar-fill"
                    style={{ width: '16%', background: '#10b981' }}
                  />
                </div>
              </div>

              <div className="posture-bar-box">
                <div className="posture-bar-title">
                  <span>MTTR (FINDING TO PR)</span>
                  <span style={{ color: '#00d4aa' }}>12 MINUTES</span>
                </div>
                <div className="posture-bar-track">
                  <div
                    className="posture-bar-fill"
                    style={{ width: '92%', background: '#00d4aa' }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Searchable & Filterable Findings Matrix Demo */}
          <div className="findings-widget-card">
            <div className="findings-widget-header">
              <div>
                <div
                  className="font-display text-sm font-bold uppercase"
                  style={{ color: '#f8fafc', letterSpacing: '0.06em' }}
                >
                  ARCHIVE // REAL FINDINGS MATRIX
                </div>
                <div className="font-mono text-xs" style={{ color: '#4b5a6e', fontSize: 10 }}>
                  Interactive sample findings generated during automated runs
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <div style={{ position: 'relative' }}>
                  <Search
                    size={12}
                    style={{ position: 'absolute', left: 8, top: 9, color: '#4b5a6e' }}
                  />
                  <input
                    type="text"
                    placeholder="Search findings..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="findings-search-input"
                    style={{ paddingLeft: 24 }}
                  />
                </div>
              </div>
            </div>

            {/* Severity Filter Chips */}
            <div className="severity-filter-chips" style={{ marginBottom: 14 }}>
              {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
                <button
                  key={sev}
                  type="button"
                  className={`severity-chip ${severityFilter === sev ? 'active' : ''}`}
                  onClick={() => setSeverityFilter(sev)}
                >
                  {sev}
                </button>
              ))}
            </div>

            {/* Findings Table */}
            <div style={{ overflowX: 'auto' }}>
              <table className="findings-mini-table">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>CVE & Finding</th>
                    <th>Category</th>
                    <th>Blast Radius</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFindings.map((finding) => {
                    const badgeClass =
                      finding.severity === 'CRITICAL'
                        ? 'badge-danger'
                        : finding.severity === 'HIGH'
                          ? 'badge-accent'
                          : finding.severity === 'MEDIUM'
                            ? 'badge-warning'
                            : 'badge-info';

                    return (
                      <tr key={finding.id}>
                        <td>
                          <span className={`badge ${badgeClass}`}>{finding.severity}</span>
                        </td>
                        <td>
                          <div style={{ fontWeight: 600, color: '#f1f5f9' }}>{finding.cve}</div>
                          <div style={{ fontSize: 11, color: '#94a3b8' }}>{finding.title}</div>
                        </td>
                        <td>
                          <span className="font-mono text-xs" style={{ color: '#38bdf8' }}>
                            {finding.category}
                          </span>
                        </td>
                        <td>
                          <span
                            className="font-mono text-xs"
                            style={{ color: '#cbd5e1', fontSize: 11 }}
                          >
                            {finding.blastRadius}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                  {filteredFindings.length === 0 && (
                    <tr>
                      <td
                        colSpan={4}
                        style={{ textAlign: 'center', padding: '24px 0', color: '#4b5a6e' }}
                      >
                        No matching findings in this view.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div
              style={{
                marginTop: 16,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span className="font-mono text-xs" style={{ color: '#4b5a6e', fontSize: 10 }}>
                EXPORT FORMATS: SARIF · DEFECTDOJO · GITHUB SECURITY ADVISORY
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <ShieldCheck size={14} color="#10b981" />
                <span className="font-mono text-xs" style={{ color: '#10b981' }}>
                  100% EXPLOIT VERIFIED
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
