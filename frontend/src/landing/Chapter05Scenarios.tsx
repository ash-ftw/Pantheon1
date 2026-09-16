import { useEffect, useRef, useState } from 'react';

interface EnvItem {
  id: string;
  title: string;
  arc: string;
  subtitle: string;
  description: string;
  scenarios: string[];
}

const ENVIRONMENTS: EnvItem[] = [
  {
    id: 'cloud-native',
    title: 'Cloud-Native',
    arc: 'Discipline',
    subtitle: 'Where it begins.',
    description:
      'Kubernetes clusters, container registries, and infrastructure-as-code blind spots. We simulate rogue container breakouts, privileged hostPath mounts, and metadata API SSRF attempts.',
    scenarios: [
      'K8s RBAC Privilege Escalation',
      'Container Escape via cgroups v2',
      'Cloud Metadata API SSRF (IMDSv2 Bypass)',
      'Ingress Route Poisoning & Controller Crash',
    ],
  },
  {
    id: 'application-layer',
    title: 'Application Layer',
    arc: 'Exposure',
    subtitle: 'The exposure.',
    description:
      'The business logic where static scanners stumble. Automated weaponization of Broken Object Level Authorization (BOLA), JWT replay, rate-limit bypassing, and multistep transaction race conditions.',
    scenarios: [
      'BOLA / IDOR Cross-Tenant Access',
      'JWT Alg: None & Key Confusion',
      'GraphQL Deep Recursion DoS',
      'Step-Up Auth Bypass on Payout Endpoints',
    ],
  },
  {
    id: 'supply-chain',
    title: 'Supply Chain',
    arc: 'The Wild One',
    subtitle: 'The wild one.',
    description:
      'Dependency confusion, malicious npm/pip post-install scripts, and contaminated CI/CD runner environments. Testing resilience when trust itself is compromised.',
    scenarios: [
      'Private Package Registry Confusion',
      'GitHub Actions Runner Token Exfiltration',
      'Dangling Subdomain CNAME Takeover',
      'Base Docker Image Backdoor Detonation',
    ],
  },
];

export function Chapter05Scenarios() {
  const [selectedEnvId, setSelectedEnvId] = useState('cloud-native');
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const currentEnv = ENVIRONMENTS.find((e) => e.id === selectedEnvId) || ENVIRONMENTS[0];

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let t = 0;
    const width = (canvas.width = canvas.offsetWidth || 500);
    const height = (canvas.height = canvas.offsetHeight || 440);

    const render = () => {
      t += 0.02;
      ctx.fillStyle = '#07090d';
      ctx.fillRect(0, 0, width, height);

      const cx = width / 2;
      const cy = height / 2;

      if (selectedEnvId === 'cloud-native') {
        // Glowing Wireframe Kubernetes Cluster Nodes
        ctx.strokeStyle = 'rgba(0, 212, 170, 0.2)';
        ctx.lineWidth = 1;

        // Grid plane
        for (let i = -4; i <= 4; i++) {
          ctx.beginPath();
          ctx.moveTo(cx + i * 40, cy + 40);
          ctx.lineTo(cx + i * 70, height - 20);
          ctx.stroke();
        }

        // Draw 3 K8s Nodes
        const nodes = [-120, 0, 120];
        nodes.forEach((offset, idx) => {
          const nx = cx + offset;
          const ny = cy - 30 + Math.sin(t + idx) * 8;

          // Cube wireframe
          ctx.strokeStyle = '#00d4aa';
          ctx.lineWidth = 1.2;
          ctx.strokeRect(nx - 36, ny - 36, 72, 72);

          // Pods inside
          for (let p = 0; p < 4; p++) {
            const px = nx - 18 + (p % 2) * 36;
            const py = ny - 18 + Math.floor(p / 2) * 36;
            ctx.beginPath();
            ctx.arc(px, py, 4, 0, Math.PI * 2);
            ctx.fillStyle = '#38bdf8';
            ctx.fill();
          }

          ctx.fillStyle = '#f1f5f9';
          ctx.font = '10px JetBrains Mono';
          ctx.fillText(`node-${idx + 1}`, nx - 22, ny + 54);
        });
      } else if (selectedEnvId === 'application-layer') {
        // API Mesh Highway with pulsating packets
        const layers = 5;
        for (let l = 0; l < layers; l++) {
          const y = 80 + l * 65;
          ctx.strokeStyle = 'rgba(255, 107, 53, 0.2)';
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(40, y);
          ctx.lineTo(width - 40, y);
          ctx.stroke();

          // Data packets
          for (let p = 0; p < 3; p++) {
            const x = 40 + (((t * 90 + p * 140 + l * 60) % (width - 80)));
            ctx.beginPath();
            ctx.arc(x, y, 4.5, 0, Math.PI * 2);
            ctx.fillStyle = '#ff6b35';
            ctx.shadowColor = '#ff6b35';
            ctx.shadowBlur = 8;
            ctx.fill();
            ctx.shadowBlur = 0;
          }
        }

        // Central Gateway
        ctx.fillStyle = 'rgba(255, 107, 53, 0.15)';
        ctx.strokeStyle = '#ff6b35';
        ctx.strokeRect(cx - 60, cy - 80, 120, 160);
        ctx.fillStyle = '#f1f5f9';
        ctx.font = '11px JetBrains Mono';
        ctx.fillText('API GATEWAY', cx - 40, cy - 20);
        ctx.fillStyle = '#ff6b35';
        ctx.font = '9px JetBrains Mono';
        ctx.fillText('AUTH: INSPECT', cx - 36, cy + 10);
      } else {
        // Supply Chain: Dependency Graph Tangle
        const count = 22;
        ctx.lineWidth = 0.8;
        for (let i = 0; i < count; i++) {
          const a = (i / count) * Math.PI * 2 + t * 0.2;
          const r = 80 + Math.sin(t * 2 + i) * 35;
          const x = cx + Math.cos(a) * r;
          const y = cy + Math.sin(a) * r;

          // Connect to neighbor
          const nextA = ((i + 3) / count) * Math.PI * 2 + t * 0.2;
          const nextR = 80 + Math.sin(t * 2 + i + 3) * 35;
          const nx = cx + Math.cos(nextA) * nextR;
          const ny = cy + Math.sin(nextA) * nextR;

          ctx.strokeStyle = i % 4 === 0 ? 'rgba(239, 68, 68, 0.4)' : 'rgba(168, 85, 247, 0.25)';
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(nx, ny);
          ctx.stroke();

          // Node
          ctx.beginPath();
          ctx.arc(x, y, i % 4 === 0 ? 4 : 2.5, 0, Math.PI * 2);
          ctx.fillStyle = i % 4 === 0 ? '#ef4444' : '#a855f7';
          ctx.fill();
        }

        // Center poisoned package
        ctx.beginPath();
        ctx.arc(cx, cy, 8, 0, Math.PI * 2);
        ctx.fillStyle = '#ef4444';
        ctx.shadowColor = '#ef4444';
        ctx.shadowBlur = 14;
        ctx.fill();
        ctx.shadowBlur = 0;

        ctx.fillStyle = '#ef4444';
        ctx.font = '10px JetBrains Mono';
        ctx.fillText('ROOT DEPENDENCY', cx - 46, cy + 24);
      }

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [selectedEnvId]);

  return (
    <section id="chapter-05" className="landing-chapter-section">
      <div className="landing-chapter-content">
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div className="chapter-eyebrow">05 // ENVIRONMENTS & COVERAGE</div>
          <h2 className="platform-headline" style={{ textAlign: 'center' }}>
            THE THREE ATTACK HORIZONS
          </h2>
          <p className="platform-subtext" style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto' }}>
            Modern threats don’t stop at the perimeter. We validate all three layers of your operational stack.
          </p>
        </div>

        <div className="environments-layout">
          {/* Left Column: 3 Category Mini-Chapters */}
          <div className="env-selector-list">
            {ENVIRONMENTS.map((env) => {
              const isActive = env.id === selectedEnvId;
              return (
                <div
                  key={env.id}
                  className={`env-card-tab ${isActive ? 'active' : ''}`}
                  onClick={() => setSelectedEnvId(env.id)}
                  data-testid={`env-tab-${env.id}`}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div className="env-tagline">{env.title}</div>
                    <span className="badge badge-accent font-mono text-xs">
                      {env.arc}
                    </span>
                  </div>

                  <div className="env-subtitle">“{env.subtitle}”</div>
                  <p className="env-desc">{env.description}</p>

                  {isActive && (
                    <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {env.scenarios.map((scen, idx) => (
                        <div
                          key={idx}
                          className="font-mono text-xs"
                          style={{ color: '#00d4aa', display: 'flex', alignItems: 'center', gap: 6 }}
                        >
                          <span style={{ color: '#ff6b35' }}>›</span> {scen}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Right Column: Full-Bleed Abstract 3D Render Canvas */}
          <div className="env-canvas-display">
            <div style={{ position: 'absolute', top: 16, left: 16, right: 16, display: 'flex', justifyContent: 'space-between', zIndex: 10 }}>
              <span className="font-mono text-xs" style={{ color: '#ff6b35' }}>
                VECTOR RENDER // {currentEnv.title.toUpperCase()}
              </span>
              <span className="badge badge-primary font-mono text-xs">
                SIMULATION LIVE
              </span>
            </div>

            <canvas
              ref={canvasRef}
              style={{ width: '100%', height: '100%', display: 'block' }}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
