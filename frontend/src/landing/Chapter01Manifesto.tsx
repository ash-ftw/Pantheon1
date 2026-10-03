import { useEffect, useRef } from 'react';

export function Chapter01Manifesto() {
  const redCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const greenCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Chaotic Red Attack Graph Animation
  useEffect(() => {
    const canvas = redCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const width = (canvas.width = canvas.offsetWidth || 300);
    const height = (canvas.height = canvas.offsetHeight || 240);

    const nodes = Array.from({ length: 18 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 1.6,
      vy: (Math.random() - 0.5) * 1.6,
      radius: Math.random() * 3 + 2,
    }));

    const render = () => {
      ctx.fillStyle = 'rgba(7, 9, 13, 0.25)';
      ctx.fillRect(0, 0, width, height);

      // Update positions
      nodes.forEach((node) => {
        node.x += node.vx;
        node.y += node.vy;
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;
      });

      // Chaotic edges
      ctx.lineWidth = 0.8;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 80) {
            ctx.strokeStyle = `rgba(239, 68, 68, ${0.6 - dist / 80})`;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }

      // Draw nodes
      nodes.forEach((n, idx) => {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fillStyle = idx % 2 === 0 ? '#ef4444' : '#ff6b35';
        ctx.shadowColor = '#ef4444';
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, []);

  // Resolved Green/Cyan Secured Graph Animation
  useEffect(() => {
    const canvas = greenCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const width = (canvas.width = canvas.offsetWidth || 300);
    const height = (canvas.height = canvas.offsetHeight || 240);

    // Symmetric circular/hierarchical cluster
    const cx = width / 2;
    const cy = height / 2;
    const layers = [
      { r: 24, count: 3, speed: 0.006 },
      { r: 60, count: 6, speed: -0.004 },
      { r: 96, count: 9, speed: 0.003 },
    ];

    let t = 0;

    const render = () => {
      t += 1;
      ctx.fillStyle = 'rgba(7, 9, 13, 0.25)';
      ctx.fillRect(0, 0, width, height);

      // Central master node
      ctx.beginPath();
      ctx.arc(cx, cy, 6, 0, Math.PI * 2);
      ctx.fillStyle = '#00d4aa';
      ctx.shadowColor = '#00d4aa';
      ctx.shadowBlur = 12;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Draw structured rings and satellites
      layers.forEach((layer) => {
        ctx.beginPath();
        ctx.arc(cx, cy, layer.r, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(0, 212, 170, 0.12)';
        ctx.lineWidth = 1;
        ctx.stroke();

        for (let i = 0; i < layer.count; i++) {
          const angle = (i / layer.count) * Math.PI * 2 + t * layer.speed;
          const px = cx + Math.cos(angle) * layer.r;
          const py = cy + Math.sin(angle) * layer.r;

          // Connect to center
          ctx.beginPath();
          ctx.moveTo(cx, cy);
          ctx.lineTo(px, py);
          ctx.strokeStyle = 'rgba(0, 212, 170, 0.2)';
          ctx.lineWidth = 0.6;
          ctx.stroke();

          // Satellite node
          ctx.beginPath();
          ctx.arc(px, py, 3, 0, Math.PI * 2);
          ctx.fillStyle = '#10b981';
          ctx.fill();
        }
      });

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, []);

  return (
    <section id="chapter-01" className="landing-chapter-section">
      {/* Background: Two Looping Crossing Text Bands */}
      <div className="crossing-bands-bg" aria-hidden="true">
        <div className="crossing-band-row ticker-band-track">
          {[...Array(3)].map((_, i) => (
            <span key={i} style={{ marginRight: 40 }}>
              ASSUME BREACH × VALIDATE CONTROLS × MEASURE BLAST RADIUS ×{' '}
            </span>
          ))}
        </div>
        <div className="crossing-band-row ticker-band-track reverse">
          {[...Array(3)].map((_, i) => (
            <span key={i} style={{ marginRight: 40 }}>
              ZERO CREDENTIAL EXPOSURE × EPHEMERAL ATTACK WORKLOADS × PROVABLE RESILIENCE ×{' '}
            </span>
          ))}
        </div>
      </div>

      <div className="landing-chapter-content manifesto-grid">
        {/* Left: Pull Quote & Narrative */}
        <div className="manifesto-text-block">
          <div className="chapter-eyebrow">01 // MANIFESTO</div>

          <blockquote className="manifesto-pull-quote">
            “The average enterprise detects an unauthorized intrusion{' '}
            <span className="highlight">204 days</span> after the perimeter has broken. Security is
            not proven by what you configure. It is proven only by what an adversary fails to
            execute.”
          </blockquote>

          <div className="manifesto-mono-subline">
            [KERNEL_LOG: ASSUMED_BREACH_PHILOSOPHY // ZERO_IMPLICIT_TRUST // TTL: ACTIVE]
          </div>

          <div className="manifesto-ciso-card">
            <p className="ciso-quote">
              “Traditional compliance tools audit your static configs. Pantheon tests what actually
              breaks when a real adversary lands in your staging cluster. It changed how our
              engineering teams prioritize remediation.”
            </p>
            <div className="ciso-author">
              — VP OF INFRASTRUCTURE & CLOUD SECURITY, GLOBAL FINTECH
            </div>
          </div>
        </div>

        {/* Right: Split Visual Renders (Chaotic vs Resolved) */}
        <div className="split-renders-pair">
          <div className="render-card red">
            <div className="render-header">
              <span className="render-badge red">BEFORE // CHAOTIC SURFACE</span>
              <span className="font-mono text-xs" style={{ color: '#ef4444' }}>
                CVSS: 9.8
              </span>
            </div>
            <div className="render-canvas-box">
              <canvas
                ref={redCanvasRef}
                style={{ width: '100%', height: '100%', display: 'block' }}
              />
            </div>
            <p className="font-mono text-xs mt-2" style={{ color: '#94a3b8', fontSize: 11 }}>
              Unbounded lateral traversal, exposed service tokens, unsegmented ingress.
            </p>
          </div>

          <div className="render-card green">
            <div className="render-header">
              <span className="render-badge green">AFTER // ENFORCED ISOLATION</span>
              <span className="font-mono text-xs" style={{ color: '#00d4aa' }}>
                HARDENED
              </span>
            </div>
            <div className="render-canvas-box">
              <canvas
                ref={greenCanvasRef}
                style={{ width: '100%', height: '100%', display: 'block' }}
              />
            </div>
            <p className="font-mono text-xs mt-2" style={{ color: '#94a3b8', fontSize: 11 }}>
              Namespace default-deny policies, automated route revocation, zero credentials.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
