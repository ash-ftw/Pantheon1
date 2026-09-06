/**
 * AppLayout — Main layout with sidebar navigation.
 *
 * Uses design tokens from Phase 1. Sidebar width is var(--sidebar-width).
 * Each route maps to a PRD module.
 */

import {
  BarChart3,
  Box,
  FileSearch,
  GitBranch,
  Layers,
  Monitor,
  Network,
  Play,
  Route,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
  Users,
  Wrench,
} from 'lucide-react';
import { Link, NavLink, Outlet } from 'react-router';

import './AppLayout.css';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  section?: string;
}

const navItems: NavItem[] = [
  // Core
  { to: '/', label: 'Dashboard', icon: <BarChart3 size={16} />, section: 'Overview' },
  { to: '/design-preview', label: 'Design System', icon: <Sparkles size={16} /> },

  // Deploy
  { to: '/apps', label: 'App Onboarding', icon: <Box size={16} />, section: 'Deploy' },
  { to: '/infrastructure', label: 'Infrastructure', icon: <Layers size={16} /> },

  // Analyze
  {
    to: '/target-analysis',
    label: 'Target Analysis',
    icon: <Search size={16} />,
    section: 'Analyze',
  },
  { to: '/endpoints', label: 'Endpoints', icon: <FileSearch size={16} /> },

  // Test
  { to: '/scenarios', label: 'Scenario Library', icon: <ShieldAlert size={16} />, section: 'Test' },
  { to: '/scenario-builder', label: 'AI Builder', icon: <Sparkles size={16} /> },
  { to: '/custom-scenarios', label: 'Custom Scenarios', icon: <Wrench size={16} /> },
  { to: '/test-runs', label: 'Test Runs', icon: <Play size={16} /> },
  { to: '/route-broker', label: 'Route Broker', icon: <Route size={16} /> },

  // Results
  { to: '/attack-graph', label: 'Attack Graph', icon: <GitBranch size={16} />, section: 'Results' },
  { to: '/observability', label: 'Observability', icon: <Monitor size={16} /> },
  { to: '/defence', label: 'Defence Engine', icon: <Shield size={16} /> },
  { to: '/reports', label: 'Reports', icon: <Network size={16} /> },

  // Admin
  { to: '/team', label: 'Team', icon: <Users size={16} />, section: 'Admin' },
];

export function AppLayout() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <Link to="/" className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <img src="/logo.svg" alt="Pantheon Logo" className="sidebar-logo-img" />
          </div>
          <span className="sidebar-logo-text font-display">Pantheon</span>
        </Link>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <div key={item.to}>
              {item.section && <div className="sidebar-section">{item.section}</div>}
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
                }
              >
                {item.icon}
                <span>{item.label}</span>
              </NavLink>
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="badge badge-primary">Phase 4 (Ingestion)</span>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
