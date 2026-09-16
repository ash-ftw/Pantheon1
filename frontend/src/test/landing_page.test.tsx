import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { LandingPage } from '../landing';

describe('Pantheon Enterprise Cyber Range Landing Page', () => {
  it('01 Header: renders Pantheon brand, navigation links, operational status, and Enter Console CTA', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    // Brand and logo
    expect(screen.getAllByAltText('Pantheon Logo').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/PANTHEON/i).length).toBeGreaterThan(0);
    expect(screen.getByText('Cyber Range v1.0')).toBeInTheDocument();

    // Navigation links
    expect(screen.getByText('Platform')).toHaveAttribute('href', '#platform');
    expect(screen.getByText('Execution')).toHaveAttribute('href', '#pipeline');
    expect(screen.getByText('Architecture')).toHaveAttribute('href', '#architecture');
    expect(screen.getByText('Security')).toHaveAttribute('href', '#security');

    // Status pill
    expect(screen.getAllByText('PLATFORM STATUS: OPERATIONAL').length).toBeGreaterThan(0);

    // Enter console CTA button in header
    const headerEnterBtn = screen.getByTestId('enter-console-btn');
    expect(headerEnterBtn).toHaveAttribute('href', '/dashboard');
    expect(headerEnterBtn).toHaveTextContent(/ENTER CONSOLE/i);
  });

  it('02 Hero: renders hero headline, copy, and action CTAs linking to console & scenarios', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    // Hero title parts
    const h1 = screen.getByRole('heading', { level: 1 });
    expect(h1).toHaveTextContent(/Attack/i);
    expect(h1).toHaveTextContent(/before someone else does/i);

    // Hero CTAs
    const heroConsoleBtn = screen.getByTestId('enter-console-hero-btn');
    expect(heroConsoleBtn).toHaveAttribute('href', '/dashboard');

    const heroScenariosBtn = screen.getByTestId('explore-scenarios-hero-btn');
    expect(heroScenariosBtn).toHaveAttribute('href', '/scenarios');
  });

  it('03 Marquee & Stats: renders architecture ticker and 4 metric blocks', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    // Marquee words
    expect(screen.getAllByText(/Isolated/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Ephemeral/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Observable/i).length).toBeGreaterThan(0);

    // Stats
    expect(screen.getByText('RS256')).toBeInTheDocument();
    expect(screen.getByText('Signed tenant tokens')).toBeInTheDocument();
    expect(screen.getByText('TTL')).toBeInTheDocument();
    expect(screen.getByText('Scoped attack routes')).toBeInTheDocument();
    expect(screen.getByText('Deny')).toBeInTheDocument();
    expect(screen.getByText('Default network policy')).toBeInTheDocument();
    expect(screen.getByText('k8s')).toBeInTheDocument();
    expect(screen.getByText('Namespace per tenant')).toBeInTheDocument();
  });

  it('04 Pipeline Scroller: renders the 5 execution steps', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Adversary Execution Pipeline')).toBeInTheDocument();
    expect(screen.getByText('Deploy')).toBeInTheDocument();
    expect(screen.getByText('Isolate')).toBeInTheDocument();
    expect(screen.getByText('Broker')).toBeInTheDocument();
    expect(screen.getByText('Execute')).toBeInTheDocument();
    expect(screen.getByText('Report')).toBeInTheDocument();
  });

  it('05 Platform Primitives: renders 6 capability cards with console deep-links', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Platform Primitives')).toBeInTheDocument();
    expect(screen.getByText('Tenant Isolation')).toBeInTheDocument();
    expect(screen.getByText('Ephemeral Route Broker')).toBeInTheDocument();
    expect(screen.getByText('Live Attack Graphs')).toBeInTheDocument();
    expect(screen.getByText('Fault Injection')).toBeInTheDocument();
    expect(screen.getAllByText('Observability Plane').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Defense Reports').length).toBeGreaterThan(0);

    // Verify deep links to console modules
    expect(screen.getByText('Onboard Apps & Namespaces').closest('a')).toHaveAttribute('href', '/apps');
    expect(screen.getByText('Configure Route Broker').closest('a')).toHaveAttribute('href', '/route-broker');
    expect(screen.getByText('Inspect Attack Graph').closest('a')).toHaveAttribute('href', '/attack-graph');
    expect(screen.getByText('Browse Simulation Library').closest('a')).toHaveAttribute('href', '/scenarios');
    expect(screen.getByText('View Observability Metrics').closest('a')).toHaveAttribute('href', '/observability');
    expect(screen.getByText('Access Defense Reports').closest('a')).toHaveAttribute('href', '/reports');
  });

  it('06 Architecture & Safety: renders plane topologies and CLI execution terminal', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    // Architecture planes
    expect(screen.getByText('Control Plane')).toBeInTheDocument();
    expect(screen.getByText('Tenant Environment')).toBeInTheDocument();
    expect(screen.getAllByText('Attack Engine').length).toBeGreaterThan(0);

    // Tech stack items
    expect(screen.getByText('FastAPI 0.115')).toBeInTheDocument();
    expect(screen.getByText('React 19')).toBeInTheDocument();
    expect(screen.getByText('Chaos Mesh')).toBeInTheDocument();

    // Safety model & Terminal trace
    expect(screen.getByText('Safety Invariants')).toBeInTheDocument();
    expect(screen.getByText(/Controlled blast radius, by construction/i)).toBeInTheDocument();
    expect(screen.getByText('POST /v1/scenarios/:id/execute')).toBeInTheDocument();
    expect(screen.getByText('STATUS: COMPLETED WITH 0 SAFETY VIOLATIONS')).toBeInTheDocument();
  });

  it('07 Access Request & Footer: handles access form submission and renders platform footer links', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    // Access form submission
    const emailInput = screen.getByPlaceholderText('security-team@company.com');
    const submitBtn = screen.getByRole('button', { name: /request access/i });

    fireEvent.change(emailInput, { target: { value: 'ciso@enterprise.com' } });
    fireEvent.click(submitBtn);

    expect(screen.getByText('Access request received')).toBeInTheDocument();

    // Footer links
    expect(screen.getByText('PANTHEON © 2026 · SECURITY TESTING PLATFORM')).toBeInTheDocument();
    expect(screen.getByText('Applications').closest('a')).toHaveAttribute('href', '/apps');
    expect(screen.getByText('Simulation Library').closest('a')).toHaveAttribute('href', '/scenarios');
    expect(screen.getByText('Attack Graph & Replay').closest('a')).toHaveAttribute('href', '/attack-graph');
  });
});
