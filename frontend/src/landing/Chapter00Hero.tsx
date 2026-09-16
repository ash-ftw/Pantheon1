import { useEffect, useRef } from 'react';
import { ArrowDown, ChevronRight, Play, Shield } from 'lucide-react';
import { Link } from 'react-router';

interface Chapter00HeroProps {
  onScrollNext: () => void;
}

export function Chapter00Hero({ onScrollNext }: Chapter00HeroProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let width = (canvas.width = canvas.offsetWidth);
    let height = (canvas.height = canvas.offsetHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    };

    window.addEventListener('resize', handleResize);

    // 3D wireframe polyhedron vertices (icosahedron-like)
    const vertices = [
      [-1, 1, 0],
      [1, 1, 0],
      [-1, -1, 0],
      [1, -1, 0],
      [0, -1, 1],
      [0, 1, 1],
      [0, -1, -1],
      [0, 1, -1],
      [1, 0, -1],
      [1, 0, 1],
      [-1, 0, -1],
      [-1, 0, 1],
    ];

    const edges: [number, number][] = [
      [0, 1],
      [0, 5],
      [0, 7],
      [0, 10],
      [0, 11],
      [1, 5],
      [1, 7],
      [1, 8],
      [1, 9],
      [2, 3],
      [2, 4],
      [2, 6],
      [2, 10],
      [2, 11],
      [3, 4],
      [3, 6],
      [3, 8],
      [3, 9],
      [4, 5],
      [4, 9],
      [4, 11],
      [5, 9],
      [5, 11],
      [6, 7],
      [6, 8],
      [6, 10],
      [7, 8],
      [7, 10],
      [8, 9],
      [10, 11],
    ];

    let angleX = 0;
    let angleY = 0;
    let angleZ = 0;
    let waveOffset = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // 1. Draw Wave Mesh Ground in the bottom half
      const rows = 18;
      const cols = 28;
      const spacingX = width / cols;
      const spacingY = (height * 0.45) / rows;
      const groundY = height * 0.65;

      ctx.lineWidth = 1;
      for (let r = 0; r < rows; r++) {
        ctx.beginPath();
        const yBase = groundY + r * spacingY * 0.7;
        for (let c = 0; c <= cols; c++) {
          const x = c * spacingX;
          const wave = Math.sin(c * 0.35 + waveOffset + r * 0.4) * (14 + r * 1.5);
          const y = yBase + wave;

          const alpha = 0.04 + (r / rows) * 0.18;
          ctx.strokeStyle = `rgba(0, 212, 170, ${alpha})`;

          if (c === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // 2. Draw 3D Rotating Polyhedron in the center
      const centerX = width * 0.5;
      const centerY = height * 0.42;
      const scale = Math.min(width, height) * 0.22;

      angleX += 0.004;
      angleY += 0.007;
      angleZ += 0.003;
      waveOffset += 0.03;

      const cosX = Math.cos(angleX),
        sinX = Math.sin(angleX);
      const cosY = Math.cos(angleY),
        sinY = Math.sin(angleY);
      const cosZ = Math.cos(angleZ),
        sinZ = Math.sin(angleZ);

      const projected = vertices.map(([x, y, z]) => {
        // Rotate Y
        const x1 = x * cosY + z * sinY;
        const y1 = y;
        const z1 = -x * sinY + z * cosY;

        // Rotate X
        const x2 = x1;
        const y2 = y1 * cosX - z1 * sinX;
        const z2 = y1 * sinX + z1 * cosX;

        // Rotate Z
        const x3 = x2 * cosZ - y2 * sinZ;
        const y3 = x2 * sinZ + y2 * cosZ;
        const z3 = z2;

        const fov = 3.5;
        const pz = z3 + fov;
        const px = (x3 / pz) * scale + centerX;
        const py = (y3 / pz) * scale + centerY;
        return { px, py, pz };
      });

      // Draw Edges
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.45)';
      ctx.lineWidth = 1.2;
      edges.forEach(([i, j]) => {
        const p1 = projected[i];
        const p2 = projected[j];
        ctx.beginPath();
        ctx.moveTo(p1.px, p1.py);
        ctx.lineTo(p2.px, p2.py);
        ctx.stroke();
      });

      // Draw glowing vertices
      projected.forEach((p, idx) => {
        ctx.beginPath();
        ctx.arc(p.px, p.py, idx % 3 === 0 ? 3.5 : 2.5, 0, Math.PI * 2);
        ctx.fillStyle = idx % 3 === 0 ? '#ff6b35' : '#00d4aa';
        ctx.shadowColor = idx % 3 === 0 ? '#ff6b35' : '#00d4aa';
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0; // reset
      });

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <section id="chapter-00" className="landing-chapter-section hero-wrapper">
      {/* Dynamic 3D Object & Mesh Canvas Background */}
      <canvas ref={canvasRef} className="hero-canvas-bg" />

      <div className="hero-content">
        <div className="hero-badge-tag">
          <Shield size={12} style={{ display: 'inline', marginRight: 6 }} />
          AUTONOMOUS ADVERSARIAL VALIDATION // KERNEL 4.19
        </div>

        <h1 className="hero-headline">
          BUILT TO PROVE RESILIENCE.
          <br />
          <span>BREACH THE SURFACE FIRST.</span>
        </h1>

        <p className="hero-subhead">
          Pantheon spins up ephemeral, tenant-isolated attacker workloads against your staging and
          preview infrastructure. Real exploit chains, zero synthetic mocks, zero credential leaks.
        </p>

        <div className="hero-cta-group">
          <Link to="/dashboard" className="hero-btn-primary">
            <Play size={13} style={{ display: 'inline', marginRight: 6 }} />
            LAUNCH TEST RUN
          </Link>

          <button type="button" className="hero-btn-secondary" onClick={onScrollNext}>
            EXPLORE THE ENGINE
            <ChevronRight size={13} style={{ display: 'inline', marginLeft: 4 }} />
          </button>
        </div>

        <button
          type="button"
          className="hero-scroll-indicator"
          onClick={onScrollNext}
          aria-label="Scroll to Chapter 01 Manifesto"
        >
          <span>SCROLL TO BEGIN</span>
          <ArrowDown size={14} />
        </button>
      </div>

      {/* Looping mono ticker band just below hero */}
      <div
        className="ticker-band-container"
        style={{ position: 'absolute', bottom: 0, left: 0, right: 0 }}
      >
        <div className="ticker-band-track">
          {[...Array(4)].map((_, i) => (
            <span key={i} className="ticker-item">
              ZERO TRUST <span className="dot">·</span>
              CONTINUOUS ATTACK SIMULATION <span className="dot">·</span>
              TENANT ISOLATED <span className="dot">·</span>
              EPHEMERAL BY DESIGN <span className="dot">·</span>
              PROVABLE RESILIENCE <span className="dot">·</span>
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
