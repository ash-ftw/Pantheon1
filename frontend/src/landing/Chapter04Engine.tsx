import { useEffect, useRef, useState } from 'react';
import { Check } from 'lucide-react';
import type { EnginePhase } from './types';

const PHASES: EnginePhase[] = [
  {
    id: 'recon',
    numeral: '①',
    title: 'Recon',
    tagline: 'Read the attack surface.',
    description:
      'Intent-first target mapping before a single scenario runs. Automatic OpenAPI discovery, DNS mapping, container ingress indexing, and zero-touch asset fingerprinting.',
    badge: 'PHASE 01 // DISCOVERY',
    telemetry: 'TARGETS IDENTIFIED: 142 ENDPOINTS · 12 CRDs',
  },
  {
    id: 'ignite',
    numeral: '②',
    title: 'Ignite',
    tagline: 'Light the corridor.',
    description:
      'Ephemeral attacker workloads spin up on TTL-managed routes. Zero exposed static credentials; short-lived tokens and isolated sandbox networking with automated circuit breakers.',
    badge: 'PHASE 02 // DETONATION',
    telemetry: 'SANDBOX ROUTE TTL: 14:59 · DEFAULT-DENY ACTIVE',
  },
  {
    id: 'observe',
    numeral: '③',
    title: 'Observe',
    tagline: 'Walk the stack.',
    description:
      'Real-time attack graph traversal. Watch attacker pods attempt lateral movement, inspect eBPF socket events live, and evaluate ingress WAF/firewall tripwires as they fire.',
    badge: 'PHASE 03 // TRAVERSAL',
    telemetry: 'GRAPH HOP DEPTH: 4 · MITRE T1190 / T1078 FLAGGED',
  },
  {
    id: 'report',
    numeral: '④',
    title: 'Report',
    tagline: 'Carry it across.',
    description:
      'Findings converted into prioritized, severity-scored remediation. Finding-to-fix automation: generate Helm patch diffs, network policy fixes, and CI/CD gates directly from verified exploits.',
    badge: 'PHASE 04 // REMEDIATION',
    telemetry: 'PR GENERATION READY · CVSS 9.8 MITIGATED',
  },
];

export function Chapter04Engine() {
  const [activePhaseIndex, setActivePhaseIndex] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const activePhase = PHASES[activePhaseIndex];

  // Canvas visualizer morphing based on active phase
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let t = 0;
    const width = (canvas.width = canvas.offsetWidth || 500);
    const height = (canvas.height = canvas.offsetHeight || 380);

    const render = () => {
      t += 0.02;
      ctx.fillStyle = '#07090d';
      ctx.fillRect(0, 0, width, height);

      const cx = width / 2;
      const cy = height / 2;

      if (activePhaseIndex === 0) {
        // RECON: Circular radar scan & target nodes
        ctx.strokeStyle = 'rgba(0, 212, 170, 0.2)';
        ctx.lineWidth = 1;
        for (let r = 50; r <= 150; r += 40) {
          ctx.beginPath();
          ctx.arc(cx, cy, r, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Radar line
        const scanAngle = t * 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(scanAngle) * 160, cy + Math.sin(scanAngle) * 160);
        ctx.strokeStyle = 'rgba(0, 212, 170, 0.8)';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Discovered targets blipping
        for (let i = 0; i < 8; i++) {
          const angle = i * (Math.PI / 4) + Math.sin(t + i) * 0.2;
          const dist = 60 + ((i * 25) % 90);
          const px = cx + Math.cos(angle) * dist;
          const py = cy + Math.sin(angle) * dist;

          ctx.beginPath();
          ctx.arc(px, py, 3.5, 0, Math.PI * 2);
          ctx.fillStyle = '#00d4aa';
          ctx.fill();

          ctx.fillStyle = 'rgba(0, 212, 170, 0.4)';
          ctx.font = '9px JetBrains Mono';
          ctx.fillText(`API:/${i}`, px + 6, py - 4);
        }
      } else if (activePhaseIndex === 1) {
        // IGNITE: Laser corridor & ephemeral attacker pods
        ctx.strokeStyle = 'rgba(255, 107, 53, 0.25)';
        ctx.lineWidth = 2;
        // Two corridor bounds
        ctx.beginPath();
        ctx.moveTo(40, cy - 60);
        ctx.lineTo(width - 40, cy - 60);
        ctx.moveTo(40, cy + 60);
        ctx.lineTo(width - 40, cy + 60);
        ctx.stroke();

        // Glowing packets traversing
        for (let i = 0; i < 5; i++) {
          const packetX = 40 + ((t * 120 + i * 80) % (width - 80));
          ctx.beginPath();
          ctx.arc(packetX, cy, 5, 0, Math.PI * 2);
          ctx.fillStyle = '#ff6b35';
          ctx.shadowColor = '#ff6b35';
          ctx.shadowBlur = 12;
          ctx.fill();
          ctx.shadowBlur = 0;
        }

        ctx.fillStyle = '#f8fafc';
        ctx.font = '11px JetBrains Mono';
        ctx.fillText('EPHEMERAL TUNNEL // ENCRYPTED MTLS 1.3', cx - 110, cy - 75);
      } else if (activePhaseIndex === 2) {
        // OBSERVE: Real-time attack graph traversal
        const nodes = [
          { x: cx - 140, y: cy, label: 'Attacker Pod', color: '#ff6b35' },
          { x: cx - 40, y: cy - 60, label: 'Ingress GW', color: '#00d4aa' },
          { x: cx - 40, y: cy + 60, label: 'Auth Svc', color: '#00d4aa' },
          { x: cx + 70, y: cy, label: 'API Mesh', color: '#38bdf8' },
          { x: cx + 160, y: cy, label: 'Secrets Store', color: '#ef4444' },
        ];

        // Draw connections
        ctx.strokeStyle = 'rgba(0, 212, 170, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(nodes[0].x, nodes[0].y);
        ctx.lineTo(nodes[1].x, nodes[1].y);
        ctx.moveTo(nodes[0].x, nodes[0].y);
        ctx.lineTo(nodes[2].x, nodes[2].y);
        ctx.moveTo(nodes[1].x, nodes[1].y);
        ctx.lineTo(nodes[3].x, nodes[3].y);
        ctx.moveTo(nodes[2].x, nodes[2].y);
        ctx.lineTo(nodes[3].x, nodes[3].y);
        ctx.moveTo(nodes[3].x, nodes[3].y);
        ctx.lineTo(nodes[4].x, nodes[4].y);
        ctx.stroke();

        // Pulsing hop packet
        const hopProgress = (Math.sin(t * 3) + 1) / 2;
        const hopX = nodes[3].x + (nodes[4].x - nodes[3].x) * hopProgress;
        const hopY = nodes[3].y;
        ctx.beginPath();
        ctx.arc(hopX, hopY, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#ef4444';
        ctx.shadowColor = '#ef4444';
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0;

        nodes.forEach((n) => {
          ctx.beginPath();
          ctx.arc(n.x, n.y, 7, 0, Math.PI * 2);
          ctx.fillStyle = n.color;
          ctx.fill();

          ctx.fillStyle = '#cbd5e1';
          ctx.font = '10px JetBrains Mono';
          ctx.fillText(n.label, n.x - 24, n.y + 18);
        });
      } else {
        // REPORT: Verified findings to PR
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.4)';
        ctx.lineWidth = 1;
        ctx.strokeRect(cx - 150, cy - 80, 300, 160);

        ctx.fillStyle = '#10b981';
        ctx.font = '12px JetBrains Mono';
        ctx.fillText('REMEDIATION PATCH GENERATED', cx - 110, cy - 50);

        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px JetBrains Mono';
        ctx.fillText('+ apiVersion: networking.k8s.io/v1', cx - 130, cy - 20);
        ctx.fillText('+ kind: NetworkPolicy', cx - 130, cy - 4);
        ctx.fillText('+   policyTypes: ["Ingress", "Egress"]', cx - 130, cy + 12);
        ctx.fillText('+   defaultDenyAll: true', cx - 130, cy + 28);
        ctx.fillText('STATUS: PR #104 CREATED & VERIFIED', cx - 130, cy + 60);
      }

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [activePhaseIndex]);

  return (
    <section id="chapter-04" className="landing-chapter-section">
      <div className="landing-chapter-content">
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div className="chapter-eyebrow">04 // THE ENGINE</div>
          <h2 className="platform-headline" style={{ textAlign: 'center' }}>
            FOUR MOVEMENTS OF ADVERSARIAL VALIDATION
          </h2>
          <p
            className="platform-subtext"
            style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto' }}
          >
            From zero-knowledge recon to automated code fixes, each simulation walks the full
            attacker lifecycle.
          </p>
        </div>

        <div className="engine-layout">
          {/* Phase Selectors / Tabs */}
          <div className="engine-nav-tabs">
            {PHASES.map((phase, idx) => {
              const isActive = idx === activePhaseIndex;
              return (
                <div
                  key={phase.id}
                  className={`engine-phase-tab ${isActive ? 'active' : ''}`}
                  onClick={() => setActivePhaseIndex(idx)}
                  data-testid={`phase-tab-${phase.id}`}
                >
                  <div className="phase-header-row">
                    <div className="phase-glyph-title">
                      <span className="phase-glyph-icon">{phase.numeral}</span>
                      <span>{phase.title}</span>
                    </div>
                    <span className="badge badge-primary font-mono text-xs">{phase.badge}</span>
                  </div>

                  <div className="phase-tagline">“{phase.tagline}”</div>
                  <p className="phase-desc">{phase.description}</p>
                  <div className="phase-telemetry">{phase.telemetry}</div>
                </div>
              );
            })}
          </div>

          {/* Canvas Morph Visualizer */}
          <div className="engine-canvas-container">
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 12,
              }}
            >
              <span className="font-mono text-xs" style={{ color: '#00d4aa' }}>
                VISUALIZER // {activePhase.title.toUpperCase()}
              </span>
              <span className="badge badge-info font-mono text-xs">SCRUBBER SYNCED</span>
            </div>

            <canvas
              ref={canvasRef}
              style={{ width: '100%', height: '320px', borderRadius: 4, display: 'block' }}
            />

            {/* Connecting Timeline Stepper */}
            <div className="phase-timeline-stepper">
              <div className="timeline-line" />
              {PHASES.map((phase, idx) => {
                const isActive = idx === activePhaseIndex;
                const isDone = idx < activePhaseIndex;
                return (
                  <button
                    key={phase.id}
                    type="button"
                    className={`timeline-step-dot ${isActive ? 'active' : ''}`}
                    onClick={() => setActivePhaseIndex(idx)}
                    title={phase.title}
                  >
                    {isDone ? <Check size={11} /> : phase.numeral}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
