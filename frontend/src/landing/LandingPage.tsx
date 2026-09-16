import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { Shield } from 'lucide-react';

import { CHAPTERS } from './types';
import { PreLoader } from './PreLoader';
import { ChapterNav } from './ChapterNav';
import { Chapter00Hero } from './Chapter00Hero';
import { Chapter01Manifesto } from './Chapter01Manifesto';
import { Chapter02Platform } from './Chapter02Platform';
import { Chapter03Stack } from './Chapter03Stack';
import { Chapter04Engine } from './Chapter04Engine';
import { Chapter05Scenarios } from './Chapter05Scenarios';
import { Chapter06Trust } from './Chapter06Trust';
import { Chapter07Cta } from './Chapter07Cta';
import { LandingFooter } from './LandingFooter';
import { ThemeSwitcher } from '../components/ui';

import './LandingPage.css';

export function LandingPage() {
  const [showPreloader, setShowPreloader] = useState(true);
  const [activeChapterId, setActiveChapterId] = useState('chapter-00');

  // Scroll to specific chapter element
  const scrollToChapter = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Scroll-spy: observe intersecting chapter sections
  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + window.innerHeight * 0.35;

      for (let i = CHAPTERS.length - 1; i >= 0; i--) {
        const el = document.getElementById(CHAPTERS[i].id);
        if (el && el.offsetTop <= scrollPosition) {
          setActiveChapterId(CHAPTERS[i].id);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="landing-root" data-testid="pantheon-landing-page">
      {/* Pre-Loader Screen */}
      {showPreloader && (
        <PreLoader onEnter={() => setShowPreloader(false)} />
      )}

      {/* Subtle Background Grid & Glow Overlay */}
      <div className="landing-grid-bg" />
      <div className="landing-radial-glow" />

      {/* Fixed Top Header */}
      <header className="landing-header">
        <Link to="/" className="landing-brand">
          <Shield size={22} color="var(--primary, #00d4aa)" />
          <span className="landing-brand-title">PANTHEON</span>
          <span className="landing-brand-badge font-mono">v1.0</span>
        </Link>

        <div className="landing-header-right">
          <ThemeSwitcher />
          <div className="status-badge-pill">
            <span className="status-dot-pulse" />
            <span>PLATFORM STATUS: OPERATIONAL</span>
          </div>

          <Link to="/dashboard" className="btn-console-enter" data-testid="enter-console-btn">
            ENTER CONSOLE →
          </Link>
        </div>
      </header>

      {/* Persistent Chapter Index (Side Nav) */}
      <ChapterNav
        activeChapterId={activeChapterId}
        onSelectChapter={scrollToChapter}
      />

      {/* Main Narrative Chapters */}
      <main>
        {/* Chapter 00 — Hero */}
        <Chapter00Hero onScrollNext={() => scrollToChapter('chapter-01')} />

        {/* Chapter 01 — Manifesto / Why */}
        <Chapter01Manifesto />

        {/* Chapter 02 — Platform Identity */}
        <Chapter02Platform />

        {/* Chapter 03 — By the Numbers / Stack */}
        <Chapter03Stack />

        {/* Chapter 04 — The Engine (Four Movements) */}
        <Chapter04Engine />

        {/* Chapter 05 — Environments / Coverage */}
        <Chapter05Scenarios />

        {/* Chapter 06 — Trust & Proof */}
        <Chapter06Trust />

        {/* Chapter 07 — Marquee CTA Interlude */}
        <Chapter07Cta />
      </main>

      {/* Footer */}
      <LandingFooter onSelectChapter={scrollToChapter} />
    </div>
  );
}
