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
  LogOut,
} from 'lucide-react';
import { useEffect } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router';

import { useAuthStore } from '../stores/authStore';
import './AppLayout.css';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  section?: string;
}

const navItems: NavItem[] = [
  // Core
  { to: '/dashboard', label: 'Dashboard', icon: <BarChart3 size={16} />, section: 'Overview' },

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

import { NotificationBell } from '../components/notifications/NotificationBell';
import { ThemeSwitcher } from '../components/ui/ThemeSwitcher';

export function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      const activeToken = localStorage.getItem('pantheon_token');
      fetch('/api/auth/me', {
        headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {},
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data) {
            setUser({
              id: data.id,
              email: data.email,
              name: data.full_name,
              role: data.role,
            });
          }
        })
        .catch(() => {});
    }
  }, [user, setUser]);

  const handleLogout = () => {
    localStorage.removeItem('pantheon_token');
    logout();
    navigate('/login');
  };

  const displayRole = (user?.role || 'admin').toUpperCase();
  const displayEmail = user?.email || 'dev@pantheon.local';

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <Link to="/dashboard" className="sidebar-logo">
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
                end={item.to === '/dashboard'}
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
          <span className="badge badge-primary font-mono text-xs">v1.0 · All Modules Active</span>
        </div>
      </aside>

      <div className="main-wrapper">
        <header className="top-navbar">
          <div className="top-navbar-left">
            <div className="cluster-status-indicator">
              <span className="status-dot online" />
              <span className="status-text font-mono">
                Tenant Cluster: <strong>Isolated</strong> · Default-Deny Active
              </span>
            </div>
          </div>

          <div className="top-navbar-right">
            <ThemeSwitcher />
            <NotificationBell />
            <div className="user-profile-badge font-mono">
              <span className="user-role-tag">{displayRole}</span>
              <span className="user-email-text">{displayEmail}</span>
            </div>
            <button
              type="button"
              className="navbar-logout-btn font-mono"
              onClick={handleLogout}
              title="Sign out of Pantheon"
              aria-label="Logout"
            >
              <LogOut size={13} />
              <span>LOGOUT</span>
            </button>
          </div>
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
