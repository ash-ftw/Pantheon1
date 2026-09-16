import { Link } from 'react-router';
import { ArrowRight, Play } from 'lucide-react';

export function Chapter07Cta() {
  return (
    <section id="chapter-07" className="cta-interlude-section">
      {/* Full-width looping marquee */}
      <div className="cta-marquee-large">
        <div className="cta-marquee-track">
          {[...Array(4)].map((_, i) => (
            <span key={i} className="cta-marquee-text">
              READY TO GET <span className="glow">BREACHED</span> THE SAFE WAY? ·{' '}
            </span>
          ))}
        </div>
      </div>

      <div className="cta-interlude-center">
        <div className="chapter-eyebrow" style={{ marginBottom: 8 }}>
          07 // THE SAFE BREACH
        </div>

        <h2 className="cta-center-line">
          Ready to see what actually breaks?
        </h2>

        <p className="platform-subtext" style={{ margin: 0, textAlign: 'center' }}>
          Deploy an ephemeral, tenant-isolated sandbox in 10 minutes. Run real attack graphs with zero synthetic mocks.
        </p>

        <Link
          to="/dashboard"
          className="cta-arrow-btn"
          data-testid="cta-launch-btn"
          style={{ textDecoration: 'none' }}
        >
          <Play size={14} style={{ marginRight: 6 }} />
          <span>LAUNCH CONSOLE</span>
          <ArrowRight size={14} style={{ marginLeft: 6 }} />
        </Link>
      </div>
    </section>
  );
}
