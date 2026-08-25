/**
 * Placeholder page component factory.
 * Creates a styled placeholder for each PRD module route
 * before the actual feature is built.
 */

interface PlaceholderPageProps {
  title: string;
  phase: string;
  description: string;
  icon: React.ReactNode;
}

export function PlaceholderPage({ title, phase, description, icon }: PlaceholderPageProps) {
  return (
    <div className="page-container animate-fade-in">
      <div className="page-header">
        <div className="page-title">{title}</div>
        <div className="page-subtitle">{description}</div>
      </div>
      <div className="card" style={{ maxWidth: 600 }}>
        <div className="card-body" style={{ textAlign: 'center', padding: '48px 32px' }}>
          <div style={{ marginBottom: 16, opacity: 0.4 }}>{icon}</div>
          <div
            className="font-display"
            style={{
              fontSize: 16,
              fontWeight: 600,
              textTransform: 'uppercase' as const,
              letterSpacing: '0.06em',
              marginBottom: 8,
            }}
          >
            {title}
          </div>
          <div style={{ color: 'var(--secondary-foreground)', marginBottom: 16 }}>
            {description}
          </div>
          <span className="badge badge-info">{phase}</span>
        </div>
      </div>
    </div>
  );
}
