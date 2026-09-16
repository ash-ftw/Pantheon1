/**
 * Page component barrel exports.
 * Each module gets its own page — placeholder now, replaced with real
 * implementation in the relevant phase.
 */

import { Box, type LucideProps } from 'lucide-react';

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
export { DashboardPage } from './DashboardPage';

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
export { TargetAnalysisPage } from './TargetAnalysisPage';

// PRD Module 6 — Endpoint Discovery (Phase 5)
export { EndpointDiscoveryPage } from './EndpointDiscoveryPage';

// PRD Module 7 — Simulation Library (Phase 6)
export { SimulationLibraryPage } from './SimulationLibraryPage';

// PRD Module 8 — AI Scenario Builder (Phase 6)
export { ScenarioBuilderPage } from './ScenarioBuilderPage';

// PRD Module 9 — Custom Scenario Authoring (Phase 6)
export { CustomScenarioPage } from './CustomScenarioPage';

// PRD Module 10 — Test Run Execution (Phase 9)
export { TestRunPage } from './TestRunPage';

// PRD Module 11 — Route Broker & Kill Switch (Phase 8)
export { RouteBrokerPage } from './RouteBrokerPage';

// PRD Module 12 — Attack Graph (Phase 10)
export { AttackGraphPage } from './AttackGraphPage';

// PRD Module 13 — Observability (Phase 11)
export { ObservabilityPage } from './ObservabilityPage';

// PRD Module 14 — Defence Engine (Phase 11)
export { DefenceEnginePage } from './DefenceEnginePage';

// PRD Module 15 — Reporting (Phase 13)
export { ReportingPage } from './ReportingPage';

// PRD Module 16 — Org & Team Management (Phase 2)
export { TeamManagementPage } from './TeamManagementPage';

// Scroll-Driven Narrative Landing Page
export { LandingPage } from '../landing';
