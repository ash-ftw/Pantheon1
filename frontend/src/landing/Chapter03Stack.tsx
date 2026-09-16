import { useEffect, useRef, useState } from 'react';

interface StatItem {
  id: string;
  target: number;
  suffix: string;
  decimals: number;
  title: string;
  wrySubtitle: string;
}

const STATS_DATA: StatItem[] = [
  {
    id: 'scenarios',
    target: 500,
    suffix: '+',
    decimals: 0,
    title: 'Attack Scenarios Simulated',
    wrySubtitle: 'Still not enough to make you paranoid.',
  },
  {
    id: 'uptime',
    target: 99.98,
    suffix: '%',
    decimals: 2,
    title: 'Tenant Isolation Uptime',
    wrySubtitle: 'Zero noisy neighbors. Zero blast spillover.',
  },
  {
    id: 'ttff',
    target: 12,
    suffix: 'min',
    decimals: 0,
    title: 'Avg. Time-To-First-Finding',
    wrySubtitle: 'From git commit to verified exploit path.',
  },
  {
    id: 'creds',
    target: 0,
    suffix: '',
    decimals: 0,
    title: 'Shared Credentials, Ever',
    wrySubtitle: 'Ephemeral tokens killed at route expiry.',
  },
];

export function Chapter03Stack() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [hasAnimated, setHasAnimated] = useState(false);
  const [counts, setCounts] = useState<{ [key: string]: number }>({
    scenarios: 0,
    uptime: 0,
    ttff: 0,
    creds: 0,
  });
  const [isCompleted, setIsCompleted] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    if (typeof IntersectionObserver === 'undefined') {
      setCounts({
        scenarios: 500,
        uptime: 99.98,
        ttff: 12,
        creds: 0,
      });
      setIsCompleted(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && !hasAnimated) {
          setHasAnimated(true);

          const duration = 1800; // ms
          const startTime = performance.now();

          const animate = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const easeProgress = 1 - Math.pow(1 - progress, 3);

            setCounts({
              scenarios: Math.floor(easeProgress * 500),
              uptime: Number((easeProgress * 99.98).toFixed(2)),
              ttff: Math.floor(easeProgress * 12),
              creds: 0,
            });

            if (progress < 1) {
              requestAnimationFrame(animate);
            } else {
              setCounts({
                scenarios: 500,
                uptime: 99.98,
                ttff: 12,
                creds: 0,
              });
              setIsCompleted(true);
            }
          };

          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.25 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [hasAnimated]);

  return (
    <section id="chapter-03" className="landing-chapter-section" ref={containerRef}>
      <div className="landing-chapter-content">
        <div className="numbers-container">
          <div className="chapter-eyebrow">03 // BY THE NUMBERS</div>
          <h2 className="platform-headline" style={{ textAlign: 'center', marginBottom: 12 }}>
            THE METRICS OF ADVERSARIAL CERTAINTY
          </h2>
          <p
            className="platform-subtext"
            style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto 40px auto' }}
          >
            We quantify what traditional static scanners gloss over: the velocity, isolation, and
            blast radius of real attacks.
          </p>
        </div>

        <div className="stats-grid-4">
          {STATS_DATA.map((item) => {
            const rawVal = counts[item.id] ?? 0;
            const displayVal =
              item.decimals > 0 ? rawVal.toFixed(item.decimals) : rawVal.toString();

            return (
              <div key={item.id} className="stat-box-card">
                <div
                  className={`stat-number-val ${isCompleted ? 'pulse' : ''}`}
                  data-testid={`stat-${item.id}`}
                >
                  {displayVal}
                  <span style={{ fontSize: '0.65em', marginLeft: 2 }}>{item.suffix}</span>
                </div>
                <div className="stat-title">{item.title}</div>
                <div className="stat-subtitle-wry">“{item.wrySubtitle}”</div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
