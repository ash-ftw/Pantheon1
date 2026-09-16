import { CheckCircle2, Cpu, Network, Server, ShieldCheck } from 'lucide-react';

export function Chapter02Platform() {
  return (
    <section id="chapter-02" className="landing-chapter-section">
      <div className="landing-chapter-content platform-grid">
        {/* Left Column: Mission & Body */}
        <div>
          <div className="chapter-eyebrow">02 // PLATFORM IDENTITY</div>

          <h2 className="platform-headline">
            BUILT TO BE ATTACKED.
          </h2>

          <p className="platform-subtext">
            Pantheon is not a scanner that runs checks against offline definitions.
            It is a living adversarial engine that spins up disposable, hardened
            attacker pods inside dedicated micro-sandboxes. We probe, exploit, and
            map your staging architecture in real time—with automated circuit breakers
            to protect downstream clusters.
          </p>

          {/* 4-Cell Mono Metadata Grid (Reskinned from Mina) */}
          <div className="meta-grid-4">
            <div className="meta-card-cell">
              <div className="meta-label">DEPLOYMENT</div>
              <div className="meta-value">Kubernetes-Native</div>
              <div className="meta-tag">CRD-driven operator · Helm v3</div>
            </div>

            <div className="meta-card-cell">
              <div className="meta-label">ISOLATION</div>
              <div className="meta-value">Namespace-Per-Tenant</div>
              <div className="meta-tag">Calico default-deny CNI</div>
            </div>

            <div className="meta-card-cell">
              <div className="meta-label">ENGINE</div>
              <div className="meta-value">Route Broker</div>
              <div className="meta-tag">TTL 15m · Auto-Kill Switch</div>
            </div>

            <div className="meta-card-cell">
              <div className="meta-label">STATUS</div>
              <div className="meta-value">GA · 2026</div>
              <div className="meta-tag">SOC 2 Type II In Progress</div>
            </div>
          </div>
        </div>

        {/* Right Column: Platform Telemetry Card */}
        <div className="platform-visual-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <span className="font-mono text-xs" style={{ color: '#00d4aa', letterSpacing: '0.15em' }}>
              RUNTIME ENVIRONMENT STATUS
            </span>
            <span className="badge badge-success font-mono">ENFORCED</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', background: '#07090d', border: '1px solid #1a2332', borderRadius: 2 }}>
              <Server size={18} color="#00d4aa" />
              <div style={{ flex: 1 }}>
                <div className="font-mono text-xs" style={{ color: '#f1f5f9' }}>
                  Target Cluster: sandbox-us-east-1.k8s
                </div>
                <div className="font-mono text-xs" style={{ color: '#4b5a6e', fontSize: 10 }}>
                  Active Pods: 48 | Cilium eBPF Network Policies: Synced
                </div>
              </div>
              <ShieldCheck size={16} color="#10b981" />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', background: '#07090d', border: '1px solid #1a2332', borderRadius: 2 }}>
              <Cpu size={18} color="#ff6b35" />
              <div style={{ flex: 1 }}>
                <div className="font-mono text-xs" style={{ color: '#f1f5f9' }}>
                  Adversary Runner: runner-ephem-992a.pantheon
                </div>
                <div className="font-mono text-xs" style={{ color: '#4b5a6e', fontSize: 10 }}>
                  Memory Limit: 512Mi | Cap-Drop: ALL | Seccomp: RuntimeDefault
                </div>
              </div>
              <span className="font-mono text-xs" style={{ color: '#ff6b35' }}>
                TTL: 08:42
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', background: '#07090d', border: '1px solid #1a2332', borderRadius: 2 }}>
              <Network size={18} color="#3b82f6" />
              <div style={{ flex: 1 }}>
                <div className="font-mono text-xs" style={{ color: '#f1f5f9' }}>
                  Route Broker Ingress: proxy-gw.isolated.net
                </div>
                <div className="font-mono text-xs" style={{ color: '#4b5a6e', fontSize: 10 }}>
                  TLS 1.3 Strict · Synthetic Bearer Tokens Revoked On Detach
                </div>
              </div>
              <CheckCircle2 size={16} color="#10b981" />
            </div>
          </div>

          <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #1a2332', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="font-mono text-xs" style={{ color: '#4b5a6e' }}>
              TELEMETRY HASH: 0x9f4a...e12d
            </span>
            <span className="font-mono text-xs" style={{ color: '#00d4aa' }}>
              LATENCY: 1.4ms
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
