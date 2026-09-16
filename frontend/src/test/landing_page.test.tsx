import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { LandingPage } from '../landing';
import { PreLoader } from '../landing/PreLoader';
import { ChapterNav } from '../landing/ChapterNav';
import { Chapter00Hero } from '../landing/Chapter00Hero';
import { Chapter01Manifesto } from '../landing/Chapter01Manifesto';
import { Chapter02Platform } from '../landing/Chapter02Platform';
import { Chapter03Stack } from '../landing/Chapter03Stack';
import { Chapter04Engine } from '../landing/Chapter04Engine';
import { Chapter05Scenarios } from '../landing/Chapter05Scenarios';
import { Chapter06Trust } from '../landing/Chapter06Trust';
import { Chapter07Cta } from '../landing/Chapter07Cta';
import { LandingFooter } from '../landing/LandingFooter';

describe('Pantheon Scroll-Driven Narrative Landing Page', () => {
  it('00 Pre-Loader: renders status text and triggers onEnter on button click', async () => {
    const onEnter = vi.fn();
    render(<PreLoader onEnter={onEnter} />);

    expect(screen.getByTestId('preloader-counter')).toBeInTheDocument();
    expect(screen.getByTestId('preloader-status')).toBeInTheDocument();

    // Fast-forward or wait for button if needed
    const enterBtn = await screen.findByTestId('preloader-enter-btn', {}, { timeout: 3000 });
    expect(enterBtn).toHaveTextContent('TAP TO ENTER');

    fireEvent.click(enterBtn);
    // After fade delay
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect(onEnter).toHaveBeenCalled();
  });

  it('01 Chapter Side Nav: renders all 9 numbered chapters', () => {
    const onSelect = vi.fn();
    render(<ChapterNav activeChapterId="chapter-00" onSelectChapter={onSelect} />);

    expect(screen.getByText('00')).toBeInTheDocument();
    expect(screen.getByText('HERO')).toBeInTheDocument();
    expect(screen.getByText('01')).toBeInTheDocument();
    expect(screen.getByText('MANIFESTO')).toBeInTheDocument();
    expect(screen.getByText('04')).toBeInTheDocument();
    expect(screen.getByText('ENGINE')).toBeInTheDocument();
    expect(screen.getByText('07')).toBeInTheDocument();
    expect(screen.getByText('CTA')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('chapter-nav-chapter-04'));
    expect(onSelect).toHaveBeenCalledWith('chapter-04');
  });

  it('02 Chapter 00 Hero: renders 3D hero headline, CTAs, and ticker', () => {
    const onScrollNext = vi.fn();
    render(
      <MemoryRouter>
        <Chapter00Hero onScrollNext={onScrollNext} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/BUILT TO PROVE RESILIENCE/i)).toBeInTheDocument();
    expect(screen.getByText(/LAUNCH TEST RUN/i)).toBeInTheDocument();
    expect(screen.getByText(/EXPLORE THE ENGINE/i)).toBeInTheDocument();
    expect(screen.getAllByText(/ZERO TRUST/i).length).toBeGreaterThan(0);
  });

  it('03 Chapter 01 Manifesto: renders pull quote, CISO card, and split render badges', () => {
    render(<Chapter01Manifesto />);

    expect(screen.getByText(/204 days/i)).toBeInTheDocument();
    expect(screen.getByText(/BEFORE \/\/ CHAOTIC SURFACE/i)).toBeInTheDocument();
    expect(screen.getByText(/AFTER \/\/ ENFORCED ISOLATION/i)).toBeInTheDocument();
  });

  it('04 Chapter 02 Platform: renders BUILT TO BE ATTACKED and 4-cell metadata grid', () => {
    render(<Chapter02Platform />);

    expect(screen.getByText('BUILT TO BE ATTACKED.')).toBeInTheDocument();
    expect(screen.getByText('DEPLOYMENT')).toBeInTheDocument();
    expect(screen.getByText('Kubernetes-Native')).toBeInTheDocument();
    expect(screen.getByText('ISOLATION')).toBeInTheDocument();
    expect(screen.getByText('ENGINE')).toBeInTheDocument();
    expect(screen.getByText('STATUS')).toBeInTheDocument();
    expect(screen.getByText('GA · 2026')).toBeInTheDocument();
  });

  it('05 Chapter 03 By the Numbers: renders 4 stat blocks with wry subtitles', () => {
    render(<Chapter03Stack />);

    expect(screen.getByText('Attack Scenarios Simulated')).toBeInTheDocument();
    expect(screen.getByText(/Still not enough to make you paranoid/i)).toBeInTheDocument();
    expect(screen.getByText('Tenant Isolation Uptime')).toBeInTheDocument();
    expect(screen.getByText('Avg. Time-To-First-Finding')).toBeInTheDocument();
    expect(screen.getByText('Shared Credentials, Ever')).toBeInTheDocument();
  });

  it('06 Chapter 04 Engine: renders four movements and switches active phase', () => {
    render(<Chapter04Engine />);

    expect(screen.getByText('FOUR MOVEMENTS OF ADVERSARIAL VALIDATION')).toBeInTheDocument();
    expect(screen.getByText('Recon')).toBeInTheDocument();
    expect(screen.getByText('Ignite')).toBeInTheDocument();
    expect(screen.getByText('Observe')).toBeInTheDocument();
    expect(screen.getByText('Report')).toBeInTheDocument();

    // Click Ignite tab
    fireEvent.click(screen.getByTestId('phase-tab-ignite'));
    expect(screen.getByText(/Light the corridor/i)).toBeInTheDocument();
  });

  it('07 Chapter 05 Scenarios: renders coverage categories and switches tabs', () => {
    render(<Chapter05Scenarios />);

    expect(screen.getByText('THE THREE ATTACK HORIZONS')).toBeInTheDocument();
    expect(screen.getByText('Cloud-Native')).toBeInTheDocument();
    expect(screen.getByText('Application Layer')).toBeInTheDocument();
    expect(screen.getByText('Supply Chain')).toBeInTheDocument();

    // Switch to Application Layer
    fireEvent.click(screen.getByTestId('env-tab-application-layer'));
    expect(screen.getByText(/The exposure/i)).toBeInTheDocument();
  });

  it('08 Chapter 06 Trust: renders replay controls and filterable findings table', () => {
    render(<Chapter06Trust />);

    expect(screen.getByText('TESTED UNDER REAL ADVERSARIAL SIGNAL')).toBeInTheDocument();
    expect(screen.getByTestId('replay-play-btn')).toBeInTheDocument();

    // Verify findings table
    expect(screen.getByText('CVE-2026-2184')).toBeInTheDocument();
    expect(screen.getAllByText('CRITICAL').length).toBeGreaterThan(0);

    // Search filter
    const searchInput = screen.getByPlaceholderText('Search findings...');
    fireEvent.change(searchInput, { target: { value: 'BOLA' } });
    expect(screen.getByText('CVE-2025-4819')).toBeInTheDocument();
    expect(screen.queryByText('CVE-2026-2184')).not.toBeInTheDocument();
  });

  it('09 Chapter 07 Marquee CTA: renders callout and launch button', () => {
    render(
      <MemoryRouter>
        <Chapter07Cta />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Ready to see what actually breaks/i)).toBeInTheDocument();
    expect(screen.getByTestId('cta-launch-btn')).toHaveAttribute('href', '/dashboard');
  });

  it('10 Footer & Full Landing Page: renders header, status pill, and chapters', () => {
    const onSelect = vi.fn();
    render(<LandingFooter onSelectChapter={onSelect} />);
    expect(screen.getByText(/PANTHEON © 2026/i)).toBeInTheDocument();

    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('pantheon-landing-page')).toBeInTheDocument();
    expect(screen.getByText('PLATFORM STATUS: OPERATIONAL')).toBeInTheDocument();
  });
});
