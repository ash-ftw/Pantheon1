import { motion, useScroll, useSpring } from 'motion/react';
import { useState } from 'react';
import { Link } from 'react-router';
import { ArrowRight, CheckCircle2, ExternalLink, Shield } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { SceneMount } from './three/SceneMount';
import { Reveal } from './Reveal';
import './LandingPage.css';

const capabilities = [
  {
    index: '01',
    title: 'Tenant Isolation',
    body: 'Every customer application lands in its own Kubernetes namespace with default-deny network policies and hard resource quotas.',
    link: '/apps',
    linkText: 'Onboard Apps & Namespaces',
  },
  {
    index: '02',
    title: 'Ephemeral Route Broker',
    body: 'Attack workloads reach targets through TTL-managed temporary routes. No tenant credentials are ever exposed to the engine.',
    link: '/route-broker',
    linkText: 'Configure Route Broker',
  },
  {
    index: '03',
    title: 'Live Attack Graphs',
    body: 'Watch HTTP, load, and security scenarios propagate in real time across a rendered graph of services and dependencies.',
    link: '/attack-graph',
    linkText: 'Inspect Attack Graph',
  },
  {
    index: '04',
    title: 'Fault Injection',
    body: 'Chaos Mesh hooks introduce controlled latency, packet loss, and pod failure while scenarios execute.',
    link: '/scenarios',
    linkText: 'Browse Simulation Library',
  },
  {
    index: '05',
    title: 'Observability Plane',
    body: 'Prometheus and Loki capture system behavior for every run, correlated back to the scenario timeline.',
    link: '/observability',
    linkText: 'View Observability Metrics',
  },
  {
    index: '06',
    title: 'Defense Reports',
    body: 'Each execution ends in an actionable report: what broke, why it broke, and the remediation worth shipping first.',
    link: '/reports',
    linkText: 'Access Defense Reports',
  },
];

const planes = [
  {
    name: 'Control Plane',
    detail:
      'FastAPI backend and React console managing organizations, applications, scenarios, safety allowlists, and execution jobs.',
    stack: ['FastAPI 0.115', 'React 19', 'Celery 5.4', 'PostgreSQL 16'],
    link: '/dashboard',
    linkText: 'Control Plane Console',
  },
  {
    name: 'Tenant Environment',
    detail:
      'Isolated namespaces holding customer applications with default-deny policies, quotas, and Chaos Mesh fault hooks.',
    stack: ['k3s 1.30', 'Chaos Mesh', 'Buildpacks', 'Registry v2'],
    link: '/infrastructure',
    linkText: 'Infrastructure Topology',
  },
  {
    name: 'Attack Engine',
    detail:
      'Ephemeral attacker workloads executing HTTP, load, and security scenarios across temporary access routes.',
    stack: ['Route Broker', 'Trivy 0.56', 'Redis 7', 'MinIO S3'],
    link: '/route-broker',
    linkText: 'Route Broker & Guard',
  },
];

const stats = [
  { value: 'RS256', label: 'Signed tenant tokens', href: '/route-broker' },
  { value: 'TTL', label: 'Scoped attack routes', href: '/route-broker' },
  { value: 'Deny', label: 'Default network policy', href: '/apps' },
  { value: 'k8s', label: 'Namespace per tenant', href: '/infrastructure' },
];

const pipeline = [
  {
    step: '01',
    title: 'Deploy',
    body: 'Buildpacks compile your target app and push it to the internal registry.',
    link: '/apps',
  },
  {
    step: '02',
    title: 'Isolate',
    body: 'A dedicated namespace spins up with quotas and default-deny networking.',
    link: '/infrastructure',
  },
  {
    step: '03',
    title: 'Broker',
    body: 'A TTL-scoped route opens for the attacker workload. Nothing else gets through.',
    link: '/route-broker',
  },
  {
    step: '04',
    title: 'Execute',
    body: 'HTTP, load, and security scenarios run while chaos hooks perturb the system.',
    link: '/test-runs',
  },
  {
    step: '05',
    title: 'Report',
    body: 'Graphs, metrics, and logs collapse into one prioritized defense report.',
    link: '/reports',
  },
];

function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 120, damping: 30, mass: 0.3 });
  return (
    <motion.div
      style={{ scaleX }}
      className="fixed inset-x-0 top-0 z-[60] h-0.5 origin-left bg-white"
    />
  );
}

function Hero() {
  const headlineWords = ['Attack', 'your', 'own', 'stack'];

  return (
    <section className="relative min-h-[78vh] flex items-center justify-center overflow-hidden border-b border-white/10 pt-24 pb-16 w-full">
      {/* 3D Interactive Canvas in Background */}
      <SceneMount className="absolute inset-0 z-0 pointer-events-auto w-full h-full" />

      {/* Radial Dark Vignette Overlay for Crisp Text Contrast */}
      <div className="pointer-events-none absolute inset-0 z-10 bg-[radial-gradient(ellipse_at_center,rgba(9,10,12,0.7)_25%,#090a0c_85%)]" />

      {/* Hero Content Container - Clean Centered Layout */}
      <div className="landing-content-container relative z-20 text-center">
        <div className="max-w-3xl mx-auto flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex items-center gap-2.5"
          >
            <span className="label-kicker-clean">Enterprise Cyber Range</span>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="font-mono text-[11px] tracking-wider text-zinc-400 uppercase">
              Production-Shaped Resilience
            </span>
          </motion.div>

          <h1 className="mt-6 text-4xl sm:text-5xl md:text-6xl font-semibold tracking-tight text-white leading-[1.1]">
            {headlineWords.map((word, i) => (
              <motion.span
                key={word}
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.06 + i * 0.06, ease: [0.22, 1, 0.36, 1] }}
                className="inline-block mr-2.5 sm:mr-3.5"
              >
                {word}
              </motion.span>
            ))}
            <motion.span
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.32, ease: [0.22, 1, 0.36, 1] }}
              className="block text-zinc-400 mt-1 sm:mt-2"
            >
              before someone else does.
            </motion.span>
          </h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.7, delay: 0.45 }}
            className="mt-6 max-w-xl text-sm sm:text-base leading-relaxed text-zinc-300 font-sans"
          >
            Isolated Kubernetes environments, controlled attack scenarios through ephemeral route
            brokers, and defense recommendations your engineers can act on.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.55 }}
            className="mt-8 flex flex-wrap items-center justify-center gap-3.5"
          >
            <Link
              to="/dashboard"
              className="btn-primary-action"
              data-testid="enter-console-hero-btn"
            >
              Enter Console →
            </Link>
            <Link
              to="/scenarios"
              className="btn-outline-action"
              data-testid="explore-scenarios-hero-btn"
            >
              Explore Scenarios
            </Link>
            <a
              href="#architecture"
              className="px-4 py-2 font-mono text-[11px] tracking-widest text-zinc-400 uppercase transition-colors hover:text-white"
            >
              View Architecture ↓
            </a>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function Marquee() {
  const words = [
    'Isolated',
    'Ephemeral',
    'Observable',
    'Attributable',
    'Reversible',
    'Chaos Mesh Native',
    'Zero Trust Route Broker',
  ];
  return (
    <div className="overflow-hidden border-b border-white/10 bg-[#090a0c] py-3.5 w-full">
      <motion.div
        className="flex w-max gap-12 pr-12"
        animate={{ x: ['0%', '-50%'] }}
        transition={{ duration: 26, repeat: Infinity, ease: 'linear' }}
      >
        {[...words, ...words, ...words, ...words].map((word, i) => (
          <span key={i} className="label-kicker-clean whitespace-nowrap text-zinc-400 text-[11px]">
            {word} <span className="text-zinc-600 ml-4">·</span>
          </span>
        ))}
      </motion.div>
    </div>
  );
}

function PipelineSection() {
  return (
    <section id="pipeline" className="landing-section">
      <div className="landing-content-container">
        {/* Centered Section Header */}
        <Reveal>
          <div className="text-center max-w-2xl mx-auto mb-10">
            <p className="label-kicker-clean">Adversary Execution Pipeline</p>
            <h2 className="mt-2 text-2xl sm:text-3xl md:text-4xl font-semibold tracking-tight text-white">
              Five synchronized phases from build to prioritized report.
            </h2>
            <p className="mt-2.5 text-xs sm:text-sm text-zinc-400 leading-relaxed font-sans">
              Each scenario operates with deterministic isolation and continuous telemetry capture.
            </p>
          </div>
        </Reveal>

        <div className="relative space-y-4 max-w-4xl mx-auto">
          {pipeline.map((item, i) => (
            <Reveal key={item.step} delay={i * 0.06}>
              <div className="pipeline-step-box group">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-white/20 bg-[#090a0c] font-mono text-sm font-bold text-white transition-colors group-hover:border-white group-hover:bg-white group-hover:text-black">
                  {item.step}
                </div>

                <div className="flex-1">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                    <h3 className="text-lg sm:text-xl font-semibold text-white">{item.title}</h3>
                    <Link
                      to={item.link}
                      className="font-mono text-[11px] text-zinc-400 group-hover:text-white inline-flex items-center gap-1 transition-colors"
                    >
                      Inspect in console <ArrowRight size={11} />
                    </Link>
                  </div>
                  <p className="mt-1.5 text-xs sm:text-sm leading-relaxed text-zinc-300 font-sans">
                    {item.body}
                  </p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function PlatformSection() {
  return (
    <section id="platform" className="landing-section">
      <div className="landing-content-container">
        {/* Centered Section Header */}
        <Reveal>
          <div className="text-center max-w-2xl mx-auto mb-10">
            <p className="label-kicker-clean">Platform Primitives</p>
            <h2 className="mt-2 text-2xl sm:text-3xl md:text-4xl font-semibold tracking-tight text-white">
              Six primitives that make adversary simulation safe to run.
            </h2>
            <p className="mt-2.5 text-xs sm:text-sm text-zinc-400 leading-relaxed font-sans">
              Zero trust isolation while capturing deep forensic telemetry across the scenario
              lifecycle.
            </p>
          </div>
        </Reveal>

        {/* Compact 3-column grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {capabilities.map((item, i) => (
            <Reveal key={item.index} delay={(i % 3) * 0.06} className="h-full">
              <article className="capability-card-article group">
                <div>
                  <div className="flex items-center justify-between border-b border-white/10 pb-3">
                    <span className="font-mono text-xs text-emerald-400 tracking-wider font-semibold">
                      {item.index}
                    </span>
                    <span className="font-mono text-[10px] text-zinc-500 uppercase tracking-wider">
                      PRIMITIVE
                    </span>
                  </div>

                  <h3 className="mt-4 text-base sm:text-lg font-semibold text-white group-hover:text-white transition-colors">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-xs sm:text-sm text-zinc-300 leading-relaxed font-sans">
                    {item.body}
                  </p>
                </div>

                <div className="mt-6 pt-3.5 border-t border-white/10">
                  <Link
                    to={item.link}
                    className="font-mono text-[11px] text-zinc-300 group-hover:text-white flex items-center justify-between transition-colors"
                  >
                    <span>{item.linkText}</span>
                    <ArrowRight
                      size={12}
                      className="transition-transform group-hover:translate-x-1"
                    />
                  </Link>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function ArchitectureSection() {
  return (
    <section id="architecture" className="landing-section">
      <div className="landing-content-container">
        {/* Centered Section Header */}
        <Reveal>
          <div className="text-center max-w-2xl mx-auto mb-10">
            <p className="label-kicker-clean">Engineered Topology</p>
            <h2 className="mt-2 text-2xl sm:text-3xl md:text-4xl font-semibold tracking-tight text-white">
              A tenant-isolated control plane and execution model.
            </h2>
            <p className="mt-2.5 text-xs sm:text-sm text-zinc-400 leading-relaxed font-sans">
              Engineered for high-assurance validation without risking tenant credentials or shared
              network paths.
            </p>
          </div>
        </Reveal>

        <div className="relative space-y-4 max-w-4xl mx-auto">
          {planes.map((plane, index) => (
            <Reveal key={plane.name} delay={index * 0.08}>
              <div className="architecture-plane-box group">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-white/20 bg-[#090a0c] font-mono text-sm font-bold text-white transition-colors group-hover:border-white">
                  0{index + 1}
                </div>

                <div className="w-full md:w-60 shrink-0">
                  <h3 className="text-lg sm:text-xl font-semibold text-white">{plane.name}</h3>
                  <Link
                    to={plane.link}
                    className="mt-1.5 inline-flex items-center gap-1 font-mono text-[11px] text-zinc-400 hover:text-white transition-colors"
                  >
                    {plane.linkText} <ExternalLink size={11} />
                  </Link>
                </div>

                <div className="flex-1">
                  <p className="text-xs sm:text-sm leading-relaxed text-zinc-300 font-sans">
                    {plane.detail}
                  </p>
                  <ul className="mt-3.5 flex flex-wrap gap-2">
                    {plane.stack.map((tech) => (
                      <li
                        key={tech}
                        className="border border-white/15 bg-white/[0.04] px-2.5 py-1 rounded-sm font-mono text-[10px] tracking-wide text-zinc-200"
                      >
                        {tech}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function SafetySection() {
  return (
    <section id="security" className="landing-section">
      <div className="landing-content-container">
        {/* Centered Section Header */}
        <Reveal>
          <div className="text-center max-w-2xl mx-auto mb-10">
            <p className="label-kicker-clean">Safety Invariants</p>
            <h2 className="mt-2 text-2xl sm:text-3xl md:text-4xl font-semibold tracking-tight text-white">
              Controlled blast radius, by construction.
            </h2>
            <p className="mt-2.5 text-xs sm:text-sm text-zinc-400 leading-relaxed font-sans">
              Scenarios only execute against allowlisted targets with strict TTL routes and hardware
              kill switches.
            </p>
          </div>
        </Reveal>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center max-w-5xl mx-auto">
          <div className="lg:col-span-6">
            <Reveal>
              <div>
                <p className="text-xs sm:text-sm leading-relaxed text-zinc-300 font-sans">
                  Ephemeral routes expire via strict TTL brokers. Namespaces deny egress by default.
                  Every job is attributable to an organization, an operator, and a signed RS256
                  token.
                </p>

                <div className="mt-5 flex flex-col gap-2.5">
                  <div className="flex items-center gap-2.5 p-3 rounded bg-white/[0.03] border border-white/10 text-xs font-mono text-zinc-200">
                    <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                    <span>Instant Hardware Kill Switch in Route Broker</span>
                  </div>
                  <div className="flex items-center gap-2.5 p-3 rounded bg-white/[0.03] border border-white/10 text-xs font-mono text-zinc-200">
                    <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                    <span>Zero tenant credentials exposed to adversary engine</span>
                  </div>
                  <div className="flex items-center gap-2.5 p-3 rounded bg-white/[0.03] border border-white/10 text-xs font-mono text-zinc-200">
                    <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                    <span>Chaos Mesh faults with auto-remediation rollbacks</span>
                  </div>
                </div>

                <div className="mt-6">
                  <Link to="/route-broker" className="btn-outline-action">
                    Inspect Safety & Kill Switch →
                  </Link>
                </div>
              </div>
            </Reveal>
          </div>

          <div className="lg:col-span-6">
            <Reveal delay={0.1}>
              <div className="terminal-window">
                <div className="terminal-header">
                  <div className="terminal-dot active" />
                  <div className="terminal-dot active" />
                  <div className="terminal-dot active" />
                  <span className="ml-2.5 font-mono text-[11px] text-zinc-400">
                    pantheon-agent: execution-trace
                  </span>
                </div>
                <div className="terminal-body">
                  <p className="text-zinc-500"># scenario initiation sequence</p>
                  <p className="text-emerald-400 font-semibold">POST /v1/scenarios/:id/execute</p>
                  <p className="text-zinc-400">→ allowlist check: PASS (org_allowlist_verified)</p>
                  <p className="text-zinc-400">
                    → broker route initialized (ttl=600s, egress=restricted)
                  </p>
                  <p className="text-zinc-400">→ ephemeral attacker pod spun in tenant namespace</p>
                  <p className="text-zinc-400">→ live attack graph streaming: WebSocket 101</p>
                  <p className="text-zinc-400">→ metrics & traces ingested to Prometheus/Loki</p>
                  <p className="text-white font-bold">
                    → report artifact generated: artifact-2026-run-089.json ✓
                  </p>
                  <p className="text-emerald-400 mt-2 font-semibold">
                    STATUS: COMPLETED WITH 0 SAFETY VIOLATIONS
                  </p>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  );
}

export function LandingPage() {
  const [emailSubmitted, setEmailSubmitted] = useState(false);
  const [email, setEmail] = useState('');

  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const handleAccessRequest = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setEmailSubmitted(true);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem('pantheon_token');
    logout();
  };

  return (
    <div className="landing-container" data-testid="pantheon-landing-page">
      <ScrollProgress />

      {/* Sleek Compact Global Header Bar */}
      <header className="landing-header-bar">
        <div className="landing-content-container flex h-14 items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <img src="/logo.svg" alt="Pantheon Logo" className="h-7 w-7 rounded-sm shrink-0" />
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-[0.22em] uppercase text-white">
                Pantheon
              </span>
              <span className="font-mono text-[9px] tracking-widest text-zinc-400 uppercase">
                Cyber Range v1.0
              </span>
            </div>
          </Link>

          <nav className="hidden items-center gap-6 md:flex">
            <a
              href="#platform"
              className="font-mono text-[11px] tracking-wider text-zinc-400 hover:text-white uppercase transition-colors"
            >
              Platform
            </a>
            <a
              href="#pipeline"
              className="font-mono text-[11px] tracking-wider text-zinc-400 hover:text-white uppercase transition-colors"
            >
              Execution
            </a>
            <a
              href="#architecture"
              className="font-mono text-[11px] tracking-wider text-zinc-400 hover:text-white uppercase transition-colors"
            >
              Architecture
            </a>
            <a
              href="#security"
              className="font-mono text-[11px] tracking-wider text-zinc-400 hover:text-white uppercase transition-colors"
            >
              Security
            </a>
            <Link
              to="/scenarios"
              className="font-mono text-[11px] tracking-wider text-zinc-400 hover:text-white uppercase transition-colors"
            >
              Scenarios
            </Link>
          </nav>

          <div className="flex items-center gap-4">
            {user ? (
              <div className="flex items-center gap-3">
                <Link to="/dashboard" className="btn-enter-console" data-testid="enter-console-btn">
                  ENTER CONSOLE →
                </Link>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="font-mono text-[11px] uppercase tracking-wider text-zinc-400 hover:text-red-400 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <Link to="/dashboard" className="btn-enter-console" data-testid="enter-console-btn">
                ENTER CONSOLE →
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Main Narrative Structure */}
      <main className="w-full">
        <Hero />
        <Marquee />

        {/* Stats Strip - Compact Sizing */}
        <section className="border-b border-white/10 bg-[#090a0c] py-8 w-full">
          <div className="landing-content-container">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
              {stats.map((stat, i) => (
                <Reveal
                  key={stat.label}
                  delay={i * 0.06}
                  className={`py-3 ${i !== 0 ? 'md:border-l md:border-white/10 md:pl-6' : ''}`}
                >
                  <Link to={stat.href} className="group block text-center md:text-left">
                    <p className="font-mono text-2xl sm:text-3xl font-bold text-white group-hover:text-emerald-400 transition-colors">
                      {stat.value}
                    </p>
                    <p className="mt-1 text-xs text-zinc-400 font-sans flex items-center justify-center md:justify-start gap-1.5 group-hover:text-white transition-colors">
                      {stat.label}{' '}
                      <ArrowRight
                        size={12}
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      />
                    </p>
                  </Link>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* Five Synchronized Execution Phases */}
        <PipelineSection />

        {/* Six Core Primitives (Capabilities) */}
        <PlatformSection />

        {/* Architecture Section */}
        <ArchitectureSection />

        {/* Safety & Isolation Section */}
        <SafetySection />

        {/* Call to Action Section - Centered and Prominent */}
        <section id="contact" className="landing-cta-section">
          <div className="landing-content-container">
            <div className="landing-cta-inner">
              <Reveal className="w-full flex flex-col items-center text-center">
                <div className="landing-cta-badge">
                  <Shield size={15} className="text-emerald-400" />
                  <span>Zero Trust Cyber Range Walkthrough</span>
                </div>
                <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-white leading-[1.12]">
                  Run your first scenario this quarter.
                </h2>
                <p className="mt-5 text-base sm:text-lg leading-relaxed text-zinc-300 font-sans max-w-2xl mx-auto">
                  We onboard security and platform teams with a guided range build against a
                  non-production replica of your stack. Deploy, attack, and remediate with
                  confidence.
                </p>
              </Reveal>

              <Reveal delay={0.1} className="w-full flex flex-col items-center text-center">
                {emailSubmitted ? (
                  <div className="mt-9 max-w-lg w-full border border-emerald-500/30 bg-emerald-950/20 p-8 text-center rounded">
                    <CheckCircle2 size={32} className="text-emerald-400 mx-auto mb-3" />
                    <p className="font-mono text-lg text-white font-semibold">
                      Access request received
                    </p>
                    <p className="font-sans text-sm text-zinc-300 mt-2">
                      Our range engineering team will reach out to schedule your range walkthrough.
                    </p>
                    <Link
                      to="/dashboard"
                      className="mt-5 inline-block font-mono text-sm text-emerald-400 hover:underline font-semibold"
                    >
                      Or explore the live console now →
                    </Link>
                  </div>
                ) : (
                  <form
                    className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3.5 max-w-xl w-full mx-auto"
                    onSubmit={handleAccessRequest}
                  >
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="security-team@company.com"
                      aria-label="Work email"
                      className="contact-input flex-1"
                    />
                    <button type="submit" className="btn-contact-submit shrink-0">
                      Request access
                    </button>
                  </form>
                )}

                {/* Centered Secondary Links */}
                <div className="mt-8 flex flex-wrap justify-center items-center gap-7">
                  <Link
                    to="/dashboard"
                    className="font-mono text-sm text-zinc-300 hover:text-white flex items-center gap-2 transition-colors"
                  >
                    Launch Live Console <ArrowRight size={14} />
                  </Link>
                </div>
              </Reveal>
            </div>
          </div>
        </section>
      </main>

      {/* Comprehensive Platform Footer - Spacious Multi-Column Architecture */}
      <footer className="landing-footer">
        <div className="landing-content-container">
          <div className="landing-footer-grid">
            <div className="landing-footer-col landing-footer-brand-col">
              <Link to="/" className="flex items-center gap-3">
                <img src="/logo.svg" alt="Pantheon Logo" className="h-7 w-7" />
                <span className="text-lg font-bold tracking-[0.22em] uppercase text-white">
                  Pantheon
                </span>
              </Link>
              <p className="mt-4 text-sm leading-relaxed text-zinc-300 font-sans">
                B2B Enterprise Cyber Range & Adversary Simulation Platform. Deploy applications into
                isolated namespaces, execute verified attacks through temporary route brokers, and
                generate concrete defense remediations.
              </p>
              <div className="mt-6 flex items-center gap-3">
                <span className="landing-status-dot" style={{ width: 8, height: 8 }} />
                <span className="font-mono text-xs text-zinc-300">
                  PLATFORM STATUS: OPERATIONAL
                </span>
              </div>
            </div>

            <div className="landing-footer-col">
              <p className="landing-footer-heading">Console</p>
              <ul className="landing-footer-links">
                <li>
                  <Link to="/dashboard" className="footer-nav-link">
                    Dashboard
                  </Link>
                </li>
                <li>
                  <Link to="/apps" className="footer-nav-link">
                    Applications
                  </Link>
                </li>
                <li>
                  <Link to="/infrastructure" className="footer-nav-link">
                    Infrastructure View
                  </Link>
                </li>
                <li>
                  <Link to="/team" className="footer-nav-link">
                    Team & Organizations
                  </Link>
                </li>
                <li>
                  <Link to="/login" className="footer-nav-link">
                    Sign In
                  </Link>
                </li>
                <li>
                  <Link to="/register" className="footer-nav-link">
                    Register
                  </Link>
                </li>
              </ul>
            </div>

            <div className="landing-footer-col">
              <p className="landing-footer-heading">Attack Engine</p>
              <ul className="landing-footer-links">
                <li>
                  <Link to="/scenarios" className="footer-nav-link">
                    Simulation Library
                  </Link>
                </li>
                <li>
                  <Link to="/scenario-builder" className="footer-nav-link">
                    AI Scenario Builder
                  </Link>
                </li>
                <li>
                  <Link to="/custom-scenarios" className="footer-nav-link">
                    Custom Authoring
                  </Link>
                </li>
                <li>
                  <Link to="/route-broker" className="footer-nav-link">
                    Route Broker & Kill Switch
                  </Link>
                </li>
                <li>
                  <Link to="/test-runs" className="footer-nav-link">
                    Test Run Execution
                  </Link>
                </li>
              </ul>
            </div>

            <div className="landing-footer-col">
              <p className="landing-footer-heading">Defense & Audit</p>
              <ul className="landing-footer-links">
                <li>
                  <Link to="/attack-graph" className="footer-nav-link">
                    Attack Graph & Replay
                  </Link>
                </li>
                <li>
                  <Link to="/observability" className="footer-nav-link">
                    Observability Plane
                  </Link>
                </li>
                <li>
                  <Link to="/defence" className="footer-nav-link">
                    Defence Engine
                  </Link>
                </li>
                <li>
                  <Link to="/reports" className="footer-nav-link">
                    Defense Reports
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="landing-footer-bottom">
            <p className="font-mono text-xs text-zinc-400 tracking-wider uppercase">
              PANTHEON © 2026 · SECURITY TESTING PLATFORM
            </p>
            <p className="font-mono text-xs text-zinc-400 tracking-wider uppercase">
              ENTERPRISE CYBER RANGE · ZERO CREDENTIAL LEAKAGE
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
