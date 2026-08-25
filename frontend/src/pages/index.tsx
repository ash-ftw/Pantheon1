/**
 * Page component barrel exports.
 * Each module gets its own page — placeholder now, replaced with real
 * implementation in the relevant phase.
 */

import {
  BarChart3,
  Box,
  FileSearch,
  GitBranch,
  type LucideProps,
  Monitor,
  Network,
  Play,
  Route,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
  Wrench,
} from 'lucide-react';
import type { ForwardRefExoticComponent, RefAttributes } from 'react';

import { PlaceholderPage } from './PlaceholderPage';

// Helper to create placeholder pages for each module
function makePlaceholder(
  title: string,
  phase: string,
  description: string,
  Icon: ForwardRefExoticComponent<Omit<LucideProps, 'ref'> & RefAttributes<SVGSVGElement>>,
) {
  return function ModulePage() {
    return (
      <PlaceholderPage
        title={title}
        phase={phase}
        description={description}
        icon={<Icon size={48} />}
      />
    );
  };
}

// PRD Module 1 — Dashboard (Phase 14)
export const DashboardPage = makePlaceholder(
  'Dashboard',
  'Phase 14',
  'Org-level overview: test run history, findings trends, improvement over time.',
  BarChart3,
);

// PRD Module 2 — App Onboarding (Phase 4)
export { AppOnboardingPage } from './AppOnboardingPage';

// PRD Module 3 — Infrastructure View (Phase 3)
export { InfrastructureViewPage as InfrastructurePage } from './InfrastructureViewPage';

// PRD Module 4 — Ingestion Pipeline (Phase 4)
export const IngestionPage = makePlaceholder(
  'Ingestion Pipeline',
  'Phase 4',
  'Build progress, deployment status, and version history.',
  Box,
);

// PRD Module 5 — AI Target Analysis (Phase 5)
export const TargetAnalysisPage = makePlaceholder(
  'Target Analysis',
  'Phase 5',
  'Automated profiling: language, framework, ports, endpoints.',
  Search,
);

// PRD Module 6 — Endpoint Discovery (Phase 5)
export const EndpointDiscoveryPage = makePlaceholder(
  'Endpoint Discovery',
  'Phase 5',
  'OpenAPI/Swagger discovery and endpoint classification.',
  FileSearch,
);

// PRD Module 7 — Simulation Library (Phase 6)
export const SimulationLibraryPage = makePlaceholder(
  'Simulation Library',
  'Phase 6',
  'Preset attack scenarios: SQLi, brute force, traffic flood, and more.',
  ShieldAlert,
);

// PRD Module 8 — AI Scenario Builder (Phase 6)
export const ScenarioBuilderPage = makePlaceholder(
  'AI Scenario Builder',
  'Phase 6',
  'Describe what you want tested in plain language.',
  Sparkles,
);

// PRD Module 9 — Custom Scenario Authoring (Phase 6)
export const CustomScenarioPage = makePlaceholder(
  'Custom Scenarios',
  'Phase 6',
  'Author fully custom scenarios via structured form/editor.',
  Wrench,
);

// PRD Module 10 — Test Run Execution (Phase 9)
export const TestRunPage = makePlaceholder(
  'Test Runs',
  'Phase 9',
  'Execute scenarios, watch live progress, stop instantly.',
  Play,
);

// PRD Module 11 — Route Broker & Kill Switch (Phase 8)
export const RouteBrokerPage = makePlaceholder(
  'Route Broker',
  'Phase 8',
  'Scoped, time-boxed routes with kill switch.',
  Route,
);

// PRD Module 12 — Attack Graph (Phase 10)
export const AttackGraphPage = makePlaceholder(
  'Attack Graph',
  'Phase 10',
  'Visual, step-by-step replayable attack path.',
  GitBranch,
);

// PRD Module 13 — Observability (Phase 11)
export const ObservabilityPage = makePlaceholder(
  'Observability',
  'Phase 11',
  'Metrics, logs, and Kubernetes events per test run.',
  Monitor,
);

// PRD Module 14 — Defence Engine (Phase 11)
export const DefenceEnginePage = makePlaceholder(
  'Defence Engine',
  'Phase 11',
  'Actionable mitigation recommendations for every finding.',
  Shield,
);

// PRD Module 15 — Reporting (Phase 13)
export const ReportingPage = makePlaceholder(
  'Reporting',
  'Phase 13',
  'Generate PDF/Markdown reports per run or across app history.',
  Network,
);

// PRD Module 16 — Org & Team Management (Phase 2)
export { TeamManagementPage } from './TeamManagementPage';

// Phase 1 — Design System Foundation Preview Page
export { DesignPreviewPage } from './DesignPreviewPage';
