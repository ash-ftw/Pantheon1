/**
 * React Router 7.x — Data Router Configuration
 *
 * Uses createBrowserRouter per pantheon-exact-stack.md.
 * Placeholder routes for each PRD module, ready for loaders in Phase 2+.
 */

import { createBrowserRouter } from 'react-router';

import { AppLayout } from '../layouts/AppLayout';
import {
  AppOnboardingPage,
  AttackGraphPage,
  CustomScenarioPage,
  DashboardPage,
  DefenceEnginePage,
  EndpointDiscoveryPage,
  InfrastructurePage,
  LandingPage,
  ObservabilityPage,
  ReportingPage,
  RouteBrokerPage,
  ScenarioBuilderPage,
  SimulationLibraryPage,
  TargetAnalysisPage,
  TeamManagementPage,
  TestRunPage,
  AuthPage,
} from '../pages';

export const router = createBrowserRouter([
  // Scroll-Driven Narrative Landing Page
  {
    path: '/',
    element: <LandingPage />,
  },
  {
    path: '/landing',
    element: <LandingPage />,
  },

  // Standalone Auth & Registration Pages
  {
    path: '/login',
    element: <AuthPage />,
  },
  {
    path: '/register',
    element: <AuthPage initialMode="register" />,
  },

  // Operational Platform App
  {
    element: <AppLayout />,
    children: [
      // Module 1 — Dashboard (Phase 14)
      { path: 'dashboard', element: <DashboardPage /> },

      // Module 2 — App Onboarding (Phase 4)
      { path: 'apps', element: <AppOnboardingPage /> },

      // Module 3 — Infrastructure View (Phase 3)
      { path: 'infrastructure', element: <InfrastructurePage /> },

      // Module 5 — AI Target Analysis (Phase 5)
      { path: 'target-analysis', element: <TargetAnalysisPage /> },

      // Module 6 — Endpoint Discovery (Phase 5)
      { path: 'endpoints', element: <EndpointDiscoveryPage /> },

      // Module 7 — Simulation Library (Phase 6)
      { path: 'scenarios', element: <SimulationLibraryPage /> },

      // Module 8 — AI Scenario Builder (Phase 6)
      { path: 'scenario-builder', element: <ScenarioBuilderPage /> },

      // Module 9 — Custom Scenario Authoring (Phase 6)
      { path: 'custom-scenarios', element: <CustomScenarioPage /> },

      // Module 10 — Test Run Execution (Phase 9)
      { path: 'test-runs', element: <TestRunPage /> },

      // Module 11 — Route Broker & Kill Switch (Phase 8)
      { path: 'route-broker', element: <RouteBrokerPage /> },

      // Module 12 — Attack Graph (Phase 10)
      { path: 'attack-graph', element: <AttackGraphPage /> },

      // Module 13 — Observability (Phase 11)
      { path: 'observability', element: <ObservabilityPage /> },

      // Module 14 — Defence Engine (Phase 11)
      { path: 'defence', element: <DefenceEnginePage /> },

      // Module 15 — Reporting (Phase 13)
      { path: 'reports', element: <ReportingPage /> },

      // Module 16 — Org & Team Management (Phase 2)
      { path: 'team', element: <TeamManagementPage /> },
    ],
  },
]);
