import { ShieldAlert, Terminal } from 'lucide-react';
import { CHAPTERS } from './types';

function GithubIcon({ size = 15, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

function LinkedinIcon({ size = 15, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
      <rect x="2" y="9" width="4" height="12" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  );
}

interface LandingFooterProps {
  onSelectChapter: (id: string) => void;
}

export function LandingFooter({ onSelectChapter }: LandingFooterProps) {
  return (
    <footer className="landing-footer">
      <div className="footer-inner">
        {/* Top Row: System Tag & Build Info */}
        <div className="footer-top-row">
          <div className="footer-brand-tag">
            <ShieldAlert size={16} color="#00d4aa" />
            <span className="footer-copyright">PANTHEON © 2026 · ALL RIGHTS RESERVED</span>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span className="footer-build-tag font-mono">BUILD 2026.09-REV4</span>
            <span className="badge badge-primary font-mono text-xs">SOC2 TYPE II IN PROGRESS</span>
          </div>
        </div>

        {/* Middle Row: Secondary Condensed Chapter Index Nav */}
        <nav className="footer-chapter-list" aria-label="Footer Chapter Directory">
          {CHAPTERS.map((ch) => (
            <button
              key={ch.id}
              type="button"
              onClick={() => onSelectChapter(ch.id)}
              className="footer-chapter-item font-mono"
              style={{ background: 'none', border: 'none', cursor: 'pointer' }}
            >
              {ch.numeral} {ch.label}
            </button>
          ))}
        </nav>

        {/* Bottom Row: Dev & Cryptographic Verification */}
        <div className="footer-bottom-row">
          <div>SIGNING KEY: 4A8F-091B-7CE2 // ZERO EXPOSED STATIC SECRETS</div>

          <div style={{ display: 'flex', gap: 16 }}>
            <a
              href="https://github.com/pantheon-cyber"
              target="_blank"
              rel="noreferrer"
              aria-label="GitHub"
              style={{ color: '#4b5a6e' }}
            >
              <GithubIcon size={15} />
            </a>
            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noreferrer"
              aria-label="LinkedIn"
              style={{ color: '#4b5a6e' }}
            >
              <LinkedinIcon size={15} />
            </a>
            <a href="#terminal" aria-label="Terminal Shell" style={{ color: '#4b5a6e' }}>
              <Terminal size={15} />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
