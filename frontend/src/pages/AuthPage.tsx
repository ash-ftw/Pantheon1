import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Key,
  Loader2,
  LogOut,
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import './AuthPage.css';

interface AuthPageProps {
  initialMode?: 'login' | 'register';
}

export function AuthPage({ initialMode }: AuthPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryMode = searchParams.get('mode');
  const [mode, setMode] = useState<'login' | 'register'>(
    queryMode === 'register' || initialMode === 'register' ? 'register' : 'login',
  );

  const navigate = useNavigate();
  const { user, setUser, setToken, logout } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [orgName, setOrgName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (queryMode === 'register' || queryMode === 'login') {
      setMode(queryMode);
    }
  }, [queryMode]);

  const switchMode = (newMode: 'login' | 'register') => {
    setMode(newMode);
    setError(null);
    setSearchParams({ mode: newMode });
  };

  const parseErrorMessage = (errData: any): string => {
    if (!errData) return 'Authentication failed. Please verify credentials.';
    if (typeof errData === 'string') return errData;
    if (typeof errData.detail === 'string') return errData.detail;
    if (Array.isArray(errData.detail)) {
      return errData.detail
        .map((d: any) => {
          const field = d.loc && d.loc.length > 1 ? `${d.loc[d.loc.length - 1]}: ` : '';
          return `${field}${d.msg}`;
        })
        .join('; ');
    }
    if (errData.detail && typeof errData.detail === 'object') {
      return errData.detail.msg || JSON.stringify(errData.detail);
    }
    if (errData.message) return errData.message;
    return 'Authentication failed';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (mode === 'register') {
      if (!fullName.trim()) {
        setError('Full Name is required.');
        return;
      }
      if (!orgName.trim()) {
        setError('Organization Name is required.');
        return;
      }
      if (password.length < 8) {
        setError('Password must be at least 8 characters long.');
        return;
      }
    }

    setLoading(true);

    try {
      const url = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const body =
        mode === 'register'
          ? {
              email: email.trim(),
              password,
              full_name: fullName.trim(),
              org_name: orgName.trim(),
            }
          : { email: email.trim(), password };

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(parseErrorMessage(errJson));
      }

      const data = await res.json();
      localStorage.setItem('pantheon_token', data.access_token);
      setToken(data.access_token);

      // Hydrate profile
      const meRes = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      if (meRes.ok) {
        const me = await meRes.json();
        setUser({
          id: me.id,
          email: me.email,
          name: me.full_name,
          role: me.role,
        });
      }

      navigate('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('pantheon_token');
    logout();
    setEmail('');
    setPassword('');
    setError(null);
  };

  return (
    <div className="auth-page-container">
      <div className="auth-page-bg-grid" />

      <div className="auth-card animate-fade-in">
        <div className="auth-header">
          <Link to="/" className="auth-logo-row">
            <img src="/logo.svg" alt="Pantheon Logo" className="auth-logo-img" />
            <span className="auth-logo-text">Pantheon</span>
          </Link>
          <h2 className="auth-header-title">
            {user
              ? 'Authenticated Session'
              : mode === 'login'
                ? 'Sign in to Platform'
                : 'Create Tenant Workspace'}
          </h2>
          <p className="auth-header-sub">
            {user
              ? 'You are currently authenticated in this browser.'
              : mode === 'login'
                ? 'Enter your credentials to access the security console.'
                : 'Register a new tenant organization and cluster workspace.'}
          </p>
        </div>

        {user ? (
          <div className="auth-body">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '14px',
                borderRadius: 'var(--radius, 4px)',
                backgroundColor: 'var(--secondary)',
                border: '1px solid var(--card-border)',
              }}
            >
              <CheckCircle2 size={20} style={{ color: 'var(--success, #10b981)' }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--foreground)' }}>
                  {user.name || user.email}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: 'var(--muted-foreground)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {user.email} • Role:{' '}
                  <strong style={{ color: 'var(--foreground)' }}>{user.role.toUpperCase()}</strong>
                </div>
              </div>
            </div>

            <button
              type="button"
              className="btn-primary auth-submit-btn"
              onClick={() => navigate('/dashboard')}
            >
              <span>Continue to Console</span>
              <ArrowRight size={14} />
            </button>

            <button
              type="button"
              className="btn-secondary auth-submit-btn"
              onClick={handleLogout}
              style={{ marginTop: 0 }}
            >
              <LogOut size={14} />
              <span>Sign Out</span>
            </button>
          </div>
        ) : (
          <>
            <div className="auth-tabs">
              <button
                type="button"
                className={`auth-tab-btn ${mode === 'login' ? 'active' : ''}`}
                onClick={() => switchMode('login')}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`auth-tab-btn ${mode === 'register' ? 'active' : ''}`}
                onClick={() => switchMode('register')}
              >
                Register Org
              </button>
            </div>

            <form onSubmit={handleSubmit} className="auth-body">
              {error && (
                <div className="auth-error-banner animate-fade-in">
                  <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <strong style={{ display: 'block', marginBottom: 2 }}>
                      Authentication Failed
                    </strong>
                    <span>{error}</span>
                  </div>
                </div>
              )}

              {mode === 'register' && (
                <>
                  <div className="auth-field">
                    <label className="auth-label" htmlFor="full-name">
                      Full Name
                    </label>
                    <input
                      id="full-name"
                      type="text"
                      className="input"
                      placeholder="e.g. Alex Rivera"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      disabled={loading}
                      required
                    />
                  </div>

                  <div className="auth-field">
                    <label className="auth-label" htmlFor="org-name">
                      Organization Name
                    </label>
                    <input
                      id="org-name"
                      type="text"
                      className="input"
                      placeholder="e.g. Acme Cybersec Inc."
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      disabled={loading}
                      required
                    />
                  </div>
                </>
              )}

              <div className="auth-field">
                <label className="auth-label" htmlFor="auth-email">
                  Email Address
                </label>
                <input
                  id="auth-email"
                  type="email"
                  className="input font-mono"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>

              <div className="auth-field">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <label className="auth-label" htmlFor="auth-password">
                    Password
                  </label>
                  {mode === 'register' && (
                    <span className="auth-field-hint font-mono">Min 8 characters</span>
                  )}
                </div>
                <input
                  id="auth-password"
                  type="password"
                  className="input font-mono"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  minLength={mode === 'register' ? 8 : 1}
                  required
                />
              </div>

              <button type="submit" className="btn-primary auth-submit-btn" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 size={14} className="spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <Key size={14} />
                    <span>
                      {mode === 'login' ? 'Sign In to Console' : 'Create Organization & Admin'}
                    </span>
                  </>
                )}
              </button>
            </form>
          </>
        )}

        <div className="auth-footer">
          <Link
            to="/"
            style={{
              color: 'var(--muted-foreground)',
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <ArrowLeft size={12} />
            <span>Return to Landing Page</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
