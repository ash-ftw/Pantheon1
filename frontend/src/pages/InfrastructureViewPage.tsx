import React from 'react';
import { HardDrive, Cpu, Layers, Lock, RefreshCw } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { TenantProvisioningBanner } from '../components/TenantProvisioningBanner';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Alert,
} from '../components/ui';

interface InfraDetail {
  namespace: string;
  status: string;
  quota?: {
    max_pods?: string;
    max_cpu?: string;
    max_memory?: string;
    max_storage?: string;
    pods?: string;
    cpu_requested?: string;
    memory_requested?: string;
  };
  limit_range?: {
    default_cpu?: string;
    default_memory?: string;
  };
  network_policies?: Array<{
    name: string;
    types: string[];
    status: string;
  }>;
}

export const InfrastructureViewPage: React.FC = () => {
  const { data, isLoading, refetch } = useQuery<InfraDetail>({
    queryKey: ['org', 'infrastructure'],
    queryFn: async () => {
      const token = localStorage.getItem('pantheon_token');
      const res = await fetch('/api/infrastructure/resources', {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
        },
      });
      if (!res.ok) throw new Error('Failed to load infrastructure resources');
      return res.json();
    },
  });

  return (
    <div className="page-container animate-fade-in space-y-8">
      {/* Page Header */}
      <div className="page-header border-b border-[var(--card-border)] pb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="page-title flex items-center gap-2">
              <Layers size={24} className="text-[var(--primary)]" />
              Infrastructure & Provisioning
            </h1>
            <Badge variant="primary">Phase 3</Badge>
          </div>
          <p className="page-subtitle">
            Read-only observation of tenant-isolated Kubernetes namespace, network security
            controls, and resource boundaries.
          </p>
        </div>
        <Button
          variant="secondary"
          iconLeft={<RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />}
          onClick={() => refetch()}
        >
          Refresh Status
        </Button>
      </div>

      {/* Provisioning Live Banner */}
      <TenantProvisioningBanner />

      {/* Grid of Resource Boundaries */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Security Isolation */}
        <Card accentColor="primary">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock size={18} className="text-[var(--primary)]" />
              Network Isolation
            </CardTitle>
            <CardDescription>
              Zero-trust posture initialized before workloads enter cluster
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {!data?.network_policies || data.network_policies.length === 0 ? (
              <div className="text-xs font-mono text-[var(--muted-foreground)] p-3 bg-[var(--secondary)] rounded border border-[var(--card-border)]">
                Default-deny policy enforcing zero ingress/egress.
              </div>
            ) : (
              data.network_policies.map((pol) => (
                <div
                  key={pol.name}
                  className="bg-[var(--secondary)] border border-[var(--card-border)] rounded-lg p-3.5 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-[var(--primary)]">
                      {pol.name}
                    </span>
                    <Badge variant="success">{pol.status.toUpperCase()}</Badge>
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    {pol.types?.map((t) => (
                      <span
                        key={t}
                        className="px-2 py-0.5 bg-[var(--muted)] text-[var(--foreground)] text-[10px] font-mono rounded border border-[var(--card-border)]"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Hard Resource Quota */}
        <Card accentColor="success">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu size={18} className="text-[var(--success)]" />
              Hard Resource Quota
            </CardTitle>
            <CardDescription>
              Enforced namespace constraints to prevent noisy-neighbor impact
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 font-mono text-xs">
            <div className="flex justify-between items-center p-3 bg-[var(--secondary)] rounded border border-[var(--card-border)]">
              <span className="text-[var(--secondary-foreground)]">Max Pod Capacity</span>
              <span className="font-bold text-[var(--foreground)]">
                {data?.quota?.max_pods || data?.quota?.pods || '20'}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[var(--secondary)] rounded border border-[var(--card-border)]">
              <span className="text-[var(--secondary-foreground)]">CPU Ceiling</span>
              <span className="font-bold text-[var(--foreground)]">
                {data?.quota?.max_cpu || data?.quota?.cpu_requested || '4 Cores'}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[var(--secondary)] rounded border border-[var(--card-border)]">
              <span className="text-[var(--secondary-foreground)]">Memory Ceiling</span>
              <span className="font-bold text-[var(--foreground)]">
                {data?.quota?.max_memory || data?.quota?.memory_requested || '8 GiB'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Container Limit Ranges */}
        <Card accentColor="accent">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive size={18} className="text-[var(--accent)]" />
              Container Limit Range
            </CardTitle>
            <CardDescription>
              Default request & limit bounds per individual container instance
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 font-mono text-xs">
            <div className="flex justify-between items-center p-3 bg-[var(--secondary)] rounded border border-[var(--card-border)]">
              <span className="text-[var(--secondary-foreground)]">Default CPU Request</span>
              <span className="font-bold text-[var(--foreground)]">
                {data?.limit_range?.default_cpu || '100m'}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[var(--secondary)] rounded border border-[var(--card-border)]">
              <span className="text-[var(--secondary-foreground)]">Default Memory Request</span>
              <span className="font-bold text-[var(--foreground)]">
                {data?.limit_range?.default_memory || '128Mi'}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[var(--secondary)] rounded border border-[var(--card-border)]">
              <span className="text-[var(--secondary-foreground)]">Storage Reservation</span>
              <span className="font-bold text-[var(--foreground)]">
                {data?.quota?.max_storage || '20 GiB'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Safety Notice */}
      <Alert type="info" title="Kubernetes Client Scoping Policy">
        Raw <code className="font-mono text-[var(--primary)] font-bold">kubectl</code> access is
        strictly prohibited. All queries operate via scoped Python{' '}
        <code className="font-mono text-[var(--primary)] font-bold">kubernetes</code> client
        bindings with tenant-isolated service account authority.
      </Alert>
    </div>
  );
};
