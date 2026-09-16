import React, { useState } from 'react';
import {
  Users,
  UserPlus,
  Shield,
  Clock,
  Key,
  Trash2,
  Edit2,
  RefreshCw,
  Mail,
  UserCheck,
  FileText,
  Lock,
  LogOut,
  Search,
  Eye,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Badge,
  Modal,
  Input,
  Select,
  Alert,
} from '../components/ui';
import { useAuthStore } from '../stores/authStore';

interface OrgDetail {
  id: string;
  name: string;
  slug: string;
  plan: string;
  cluster_status: string;
}

interface OrgMember {
  id: string;
  org_id: string;
  user_id: string;
  role: 'admin' | 'tester' | 'viewer';
  joined_at: string;
  user_email: string;
  user_name: string;
}

interface PendingInvitation {
  id: string;
  org_id: string;
  email: string;
  role: 'admin' | 'tester' | 'viewer';
  expires_at: string;
  created_at: string;
}

interface AuditLogEntry {
  id: string;
  org_id: string;
  user_id: string | null;
  user_email: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export const TeamManagementPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user, org, token, setUser, setOrg, setToken, logout } = useAuthStore();

  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');

  // Form states
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'tester' | 'viewer'>('tester');
  const [inviteError, setInviteError] = useState<string | null>(null);

  // Auth form states
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authFullName, setAuthFullName] = useState('');
  const [authOrgName, setAuthOrgName] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);

  // Member role edit state
  const [editingMember, setEditingMember] = useState<OrgMember | null>(null);
  const [newRole, setNewRole] = useState<'admin' | 'tester' | 'viewer'>('tester');

  // Audit log filter & inspection state
  const [auditActionFilter, setAuditActionFilter] = useState<string>('all');
  const [auditSearchQuery, setAuditSearchQuery] = useState<string>('');
  const [selectedAuditLog, setSelectedAuditLog] = useState<AuditLogEntry | null>(null);

  // Helper for authenticated requests
  const getHeaders = () => {
    const activeToken = token || localStorage.getItem('pantheon_token');
    return {
      'Content-Type': 'application/json',
      Authorization: activeToken ? `Bearer ${activeToken}` : '',
    };
  };

  // 1. Fetch Current Org Details
  const { data: orgData, refetch: refetchOrg } = useQuery<OrgDetail>({
    queryKey: ['org', 'current'],
    queryFn: async () => {
      const res = await fetch('/api/orgs/current', { headers: getHeaders() });
      if (!res.ok) throw new Error('Failed to load org details');
      const data = await res.json();
      setOrg({ id: data.id, name: data.name });
      return data;
    },
    retry: false,
  });

  // 2. Fetch Team Members
  const {
    data: members = [],
    isLoading: isLoadingMembers,
    refetch: refetchMembers,
  } = useQuery<OrgMember[]>({
    queryKey: ['org', 'members'],
    queryFn: async () => {
      const res = await fetch('/api/orgs/members', { headers: getHeaders() });
      if (!res.ok) return [];
      return res.json();
    },
  });

  // 3. Fetch Pending Invitations
  const { data: invitations = [], refetch: refetchInvitations } = useQuery<PendingInvitation[]>({
    queryKey: ['org', 'invitations'],
    queryFn: async () => {
      const res = await fetch('/api/orgs/invitations', { headers: getHeaders() });
      if (!res.ok) return [];
      return res.json();
    },
  });

  // 4. Fetch Audit Log
  const { data: auditLogs = [], refetch: refetchAudit } = useQuery<AuditLogEntry[]>({
    queryKey: ['org', 'audit-log', auditActionFilter],
    queryFn: async () => {
      const url =
        auditActionFilter !== 'all'
          ? `/api/orgs/audit-log?action=${encodeURIComponent(auditActionFilter)}`
          : '/api/orgs/audit-log';
      const res = await fetch(url, { headers: getHeaders() });
      if (!res.ok) return [];
      return res.json();
    },
  });

  const filteredAuditLogs = auditLogs.filter((log) => {
    if (!auditSearchQuery.trim()) return true;
    const q = auditSearchQuery.toLowerCase();
    return (
      log.action.toLowerCase().includes(q) ||
      (log.resource_type && log.resource_type.toLowerCase().includes(q)) ||
      (log.user_email && log.user_email.toLowerCase().includes(q)) ||
      (log.resource_id && log.resource_id.toLowerCase().includes(q))
    );
  });

  // Mutation: Invite Member
  const inviteMutation = useMutation({
    mutationFn: async () => {
      setInviteError(null);
      const res = await fetch('/api/orgs/invitations', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to send invitation');
      }
      return res.json();
    },
    onSuccess: () => {
      setIsInviteModalOpen(false);
      setInviteEmail('');
      refetchInvitations();
      refetchAudit();
    },
    onError: (err: Error) => {
      setInviteError(err.message);
    },
  });

  // Mutation: Update Role
  const updateRoleMutation = useMutation({
    mutationFn: async ({ memberId, role }: { memberId: string; role: string }) => {
      const res = await fetch(`/api/orgs/members/${memberId}`, {
        method: 'PATCH',
        headers: getHeaders(),
        body: JSON.stringify({ role }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to update member role');
      }
      return res.json();
    },
    onSuccess: () => {
      setEditingMember(null);
      refetchMembers();
      refetchAudit();
    },
  });

  // Mutation: Remove Member
  const removeMemberMutation = useMutation({
    mutationFn: async (memberId: string) => {
      const res = await fetch(`/api/orgs/members/${memberId}`, {
        method: 'DELETE',
        headers: getHeaders(),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to remove member');
      }
    },
    onSuccess: () => {
      refetchMembers();
      refetchAudit();
    },
  });

  // Auth Handler (Login / Register)
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    try {
      const url = authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const body =
        authMode === 'register'
          ? {
              email: authEmail,
              password: authPassword,
              full_name: authFullName,
              org_name: authOrgName,
            }
          : { email: authEmail, password: authPassword };

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Authentication failed');
      }

      const data = await res.json();
      localStorage.setItem('pantheon_token', data.access_token);
      setToken(data.access_token);

      // Fetch user profile
      const meRes = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      if (meRes.ok) {
        const me = await meRes.json();
        setUser({ id: me.id, email: me.email, name: me.full_name, role: me.role });
      }

      setIsAuthModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ['org'] });
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('pantheon_token');
    logout();
    queryClient.invalidateQueries({ queryKey: ['org'] });
  };

  return (
    <div className="page-container animate-fade-in space-y-8">
      {/* Header & Auth Controls */}
      <div className="page-header border-b border-[var(--card-border)] pb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="page-title">Auth, Organization & Team Management</h1>
            <Badge variant="primary">Phase 2</Badge>
          </div>
          <p className="page-subtitle">
            Manage organization members, RBAC security roles, pending team invitations, and audit
            logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {token || user ? (
            <div className="flex items-center gap-3 bg-[var(--card)] border border-[var(--card-border)] px-4 py-2 rounded">
              <div className="text-right">
                <div className="text-xs font-semibold text-[var(--foreground)]">
                  {user?.name || user?.email || 'Logged In'}
                </div>
                <div className="text-[10px] font-mono text-[var(--primary)] uppercase">
                  {user?.role || 'Admin'}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                iconLeft={<LogOut size={12} />}
              >
                Logout
              </Button>
            </div>
          ) : (
            <Button
              variant="primary"
              iconLeft={<Key size={14} />}
              onClick={() => setIsAuthModalOpen(true)}
            >
              Login / Sign Up
            </Button>
          )}

          <Button
            variant="secondary"
            iconLeft={<RefreshCw size={14} className={isLoadingMembers ? 'animate-spin' : ''} />}
            onClick={() => {
              refetchOrg();
              refetchMembers();
              refetchInvitations();
              refetchAudit();
            }}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Org Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card accentColor="primary">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-mono text-[var(--muted-foreground)] uppercase">
                Organization Name
              </div>
              <div className="text-lg font-bold text-[var(--foreground)] mt-1">
                {orgData?.name || org?.name || 'Default Organization'}
              </div>
            </div>
            <Users size={24} className="text-[var(--primary)]" />
          </CardContent>
        </Card>

        <Card accentColor="info">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-mono text-[var(--muted-foreground)] uppercase">
                Org Slug
              </div>
              <div className="text-xs font-mono text-[var(--primary)] mt-1">
                {orgData?.slug || 'default-org'}
              </div>
            </div>
            <Shield size={24} className="text-[var(--info)]" />
          </CardContent>
        </Card>

        <Card accentColor="accent">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-mono text-[var(--muted-foreground)] uppercase">
                Subscription Plan
              </div>
              <div className="text-sm font-bold text-[var(--accent)] mt-1 uppercase">
                {orgData?.plan || 'Starter'}
              </div>
            </div>
            <FileText size={24} className="text-[var(--accent)]" />
          </CardContent>
        </Card>

        <Card accentColor="warning">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-[11px] font-mono text-[var(--muted-foreground)] uppercase">
                Tenant Cluster Status
              </div>
              <div className="text-xs font-semibold text-[var(--warning)] mt-1 uppercase">
                {orgData?.cluster_status || 'Provisioning'}
              </div>
            </div>
            <Lock size={24} className="text-[var(--warning)]" />
          </CardContent>
        </Card>
      </div>

      {/* Team Members List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <UserCheck size={18} className="text-[var(--primary)]" />
              Team Members ({members.length})
            </CardTitle>
            <CardDescription>
              Role-Based Access Control (RBAC) enforced per organization scope
            </CardDescription>
          </div>
          <Button
            variant="primary"
            iconLeft={<UserPlus size={14} />}
            onClick={() => setIsInviteModalOpen(true)}
          >
            Invite Teammate
          </Button>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Joined</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-[var(--muted-foreground)]">
                  No members found or authentication required.
                </TableCell>
              </TableRow>
            ) : (
              members.map((m) => (
                <TableRow key={m.id}>
                  <TableCell className="font-semibold text-[var(--foreground)]">
                    {m.user_name}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-[var(--secondary-foreground)]">
                    {m.user_email}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        m.role === 'admin' ? 'primary' : m.role === 'tester' ? 'info' : 'neutral'
                      }
                    >
                      {m.role.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-[var(--muted-foreground)]">
                    {new Date(m.joined_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        iconLeft={<Edit2 size={12} />}
                        onClick={() => {
                          setEditingMember(m);
                          setNewRole(m.role);
                        }}
                      >
                        Edit Role
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        iconLeft={<Trash2 size={12} />}
                        onClick={() => removeMemberMutation.mutate(m.id)}
                      >
                        Remove
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Pending Invitations */}
      {invitations.length > 0 && (
        <Card accentColor="accent">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail size={18} className="text-[var(--accent)]" />
              Pending Team Invitations ({invitations.length})
            </CardTitle>
            <CardDescription>
              Invitations sent via email awaiting recipient password setup
            </CardDescription>
          </CardHeader>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email Address</TableHead>
                <TableHead>Assigned Role</TableHead>
                <TableHead>Expires At</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invitations.map((inv) => (
                <TableRow key={inv.id}>
                  <TableCell className="font-mono text-xs text-[var(--foreground)]">
                    {inv.email}
                  </TableCell>
                  <TableCell>
                    <Badge variant="accent">{inv.role.toUpperCase()}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-[var(--muted-foreground)]">
                    {new Date(inv.expires_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Badge variant="warning" showDot pulseDot>
                      PENDING ACCEPTANCE
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Security Audit Log */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Clock size={18} className="text-[var(--primary)]" />
                Append-Only Security Audit Log (FR-11.2)
              </CardTitle>
              <CardDescription>
                Cryptographic immutable log of all tenant mutations, simulation starts, routes, and
                mitigations
              </CardDescription>
            </div>

            {/* Filter and Search Controls */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-1.5 bg-[var(--secondary)] border border-[var(--card-border)] rounded px-2 py-1">
                <Search size={13} className="text-[var(--muted-foreground)]" />
                <input
                  type="text"
                  placeholder="Search logs..."
                  className="bg-transparent border-none text-xs text-[var(--foreground)] focus:outline-none w-28"
                  value={auditSearchQuery}
                  onChange={(e) => setAuditSearchQuery(e.target.value)}
                />
              </div>

              <select
                className="bg-[var(--secondary)] border border-[var(--card-border)] text-xs text-[var(--foreground)] rounded px-2 py-1.5 focus:outline-none"
                value={auditActionFilter}
                onChange={(e) => setAuditActionFilter(e.target.value)}
              >
                <option value="all">All Actions</option>
                <option value="auth.login">auth.login</option>
                <option value="auth.register">auth.register</option>
                <option value="app.demo_deployed">app.demo_deployed</option>
                <option value="app.created">app.created</option>
                <option value="route.created">route.created</option>
                <option value="route.revoked">route.revoked</option>
                <option value="simulation.started">simulation.started</option>
                <option value="simulation.completed">simulation.completed</option>
                <option value="defence.applied">defence.applied</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead>User / Actor</TableHead>
              <TableHead>IP Address</TableHead>
              <TableHead className="text-right">Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredAuditLogs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-[var(--muted-foreground)]">
                  No matching audit log entries found.
                </TableCell>
              </TableRow>
            ) : (
              filteredAuditLogs.slice(0, 20).map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="font-mono text-xs text-[var(--muted-foreground)]">
                    {new Date(log.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-xs font-bold text-[var(--primary)]">
                      {log.action}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-[var(--secondary-foreground)]">
                    {log.resource_type}{' '}
                    {log.resource_id ? `(${log.resource_id.substring(0, 8)})` : ''}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-[var(--foreground)]">
                    {log.user_email || 'System'}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-[var(--muted-foreground)]">
                    {log.ip_address || '127.0.0.1'}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      iconLeft={<Eye size={12} />}
                      onClick={() => setSelectedAuditLog(log)}
                    >
                      Inspect
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Audit Log Details Inspect Modal */}
      {selectedAuditLog && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedAuditLog(null)}
          title={`Audit Log Event: ${selectedAuditLog.action}`}
          footer={
            <Button variant="secondary" onClick={() => setSelectedAuditLog(null)}>
              Close
            </Button>
          }
        >
          <div className="space-y-4 font-mono text-xs">
            <div className="grid grid-cols-2 gap-2 bg-[var(--secondary)] p-3 rounded border border-[var(--card-border)]">
              <div>
                <span className="text-[var(--muted-foreground)]">Action:</span>{' '}
                <strong className="text-[var(--primary)]">{selectedAuditLog.action}</strong>
              </div>
              <div>
                <span className="text-[var(--muted-foreground)]">Resource Type:</span>{' '}
                <span>{selectedAuditLog.resource_type}</span>
              </div>
              <div>
                <span className="text-[var(--muted-foreground)]">Actor:</span>{' '}
                <span>{selectedAuditLog.user_email || 'System'}</span>
              </div>
              <div>
                <span className="text-[var(--muted-foreground)]">Timestamp:</span>{' '}
                <span>{new Date(selectedAuditLog.created_at).toISOString()}</span>
              </div>
              {selectedAuditLog.resource_id && (
                <div className="col-span-2">
                  <span className="text-[var(--muted-foreground)]">Resource ID:</span>{' '}
                  <span className="text-[var(--secondary-foreground)]">
                    {selectedAuditLog.resource_id}
                  </span>
                </div>
              )}
            </div>

            <div>
              <span className="text-[var(--muted-foreground)] block mb-1">
                Payload Details (JSON):
              </span>
              <pre className="bg-[#050709] border border-[var(--card-border)] rounded p-3 text-[11px] text-[var(--foreground)] overflow-x-auto max-h-60">
                {JSON.stringify(selectedAuditLog.details, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}

      {/* Invite Modal */}
      <Modal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        title="Invite Teammate to Organization"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsInviteModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={inviteMutation.isPending}
              onClick={() => inviteMutation.mutate()}
            >
              Send Invitation
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {inviteError && (
            <Alert type="danger" title="Invitation Failed">
              {inviteError}
            </Alert>
          )}

          <Input
            label="Recipient Email Address"
            placeholder="colleague@company.com"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            leftIcon={<Mail size={14} />}
          />

          <Select
            label="Assigned RBAC Role"
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as 'admin' | 'tester' | 'viewer')}
            options={[
              { value: 'admin', label: 'Admin (Full cluster, team, and ingestion privileges)' },
              { value: 'tester', label: 'Tester (Can trigger builds, runs, and view findings)' },
              { value: 'viewer', label: 'Viewer (Read-only access to dashboards and reports)' },
            ]}
          />
        </div>
      </Modal>

      {/* Edit Role Modal */}
      <Modal
        isOpen={!!editingMember}
        onClose={() => setEditingMember(null)}
        title={`Change Role: ${editingMember?.user_name}`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditingMember(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={updateRoleMutation.isPending}
              onClick={() => {
                if (editingMember) {
                  updateRoleMutation.mutate({ memberId: editingMember.id, role: newRole });
                }
              }}
            >
              Update Role
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-[var(--secondary-foreground)]">
            Updating security role for{' '}
            <strong className="text-[var(--foreground)]">{editingMember?.user_email}</strong>.
          </p>

          <Select
            label="Security Role"
            value={newRole}
            onChange={(e) => setNewRole(e.target.value as 'admin' | 'tester' | 'viewer')}
            options={[
              { value: 'admin', label: 'Admin (Full Access)' },
              { value: 'tester', label: 'Tester (Standard Operations)' },
              { value: 'viewer', label: 'Viewer (Read-Only)' },
            ]}
          />
        </div>
      </Modal>

      {/* Auth Modal (Login / Register) */}
      <Modal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        title={authMode === 'login' ? 'User Login' : 'Register New Organization'}
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
            >
              Switch to {authMode === 'login' ? 'Sign Up' : 'Login'}
            </Button>
            <Button variant="primary" onClick={handleAuthSubmit}>
              {authMode === 'login' ? 'Login' : 'Create Organization'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleAuthSubmit} className="space-y-4">
          {authError && (
            <Alert type="danger" title="Auth Failed">
              {authError}
            </Alert>
          )}

          {authMode === 'register' && (
            <>
              <Input
                label="Full Name"
                placeholder="Alice Smith"
                value={authFullName}
                onChange={(e) => setAuthFullName(e.target.value)}
                required
              />
              <Input
                label="Organization Name"
                placeholder="Acme Cybersec Inc."
                value={authOrgName}
                onChange={(e) => setAuthOrgName(e.target.value)}
                required
              />
            </>
          )}

          <Input
            label="Email Address"
            type="email"
            placeholder="user@company.com"
            value={authEmail}
            onChange={(e) => setAuthEmail(e.target.value)}
            required
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            value={authPassword}
            onChange={(e) => setAuthPassword(e.target.value)}
            required
          />
        </form>
      </Modal>
    </div>
  );
};
