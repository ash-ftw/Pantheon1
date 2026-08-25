import React from 'react';
import { Server, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Badge, Button, Card, CardContent } from './ui';

interface OrgInfraStatus {
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

export const TenantProvisioningBanner: React.FC = () => {
  const queryClient = useQueryClient();

  const {
    data: infra,
    isLoading,
    isError,
  } = useQuery<OrgInfraStatus>({
    queryKey: ['org', 'infrastructure'],
    queryFn: async () => {
      const token = localStorage.getItem('pantheon_token');
      const res = await fetch('/api/infrastructure/resources', {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
        },
      });
      if (!res.ok) throw new Error('Failed to fetch cluster status');
      return res.json();
    },
    refetchInterval: (query) => {
      return query.state.data?.status === 'provisioning' ? 3000 : false;
    },
  });

  const retriggerMutation = useMutation({
    mutationFn: async () => {
      const token = localStorage.getItem('pantheon_token');
      const res = await fetch('/api/infrastructure/provision', {
        method: 'POST',
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
        },
      });
      if (!res.ok) throw new Error('Failed to trigger provisioning');
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org', 'infrastructure'] });
    },
  });

  if (isLoading) {
    return (
      <Card accentColor="info">
        <CardContent className="p-4 flex items-center gap-3">
          <Loader2 size={18} className="animate-spin text-[var(--primary)]" />
          <span className="text-xs font-mono text-[var(--foreground)]">
            Checking tenant Kubernetes environment...
          </span>
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card accentColor="danger">
        <CardContent className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle size={20} className="text-[var(--danger)]" />
            <div>
              <div className="text-xs font-bold text-[var(--danger)]">
                Environment Provisioning Warning
              </div>
              <div className="text-[11px] text-[var(--muted-foreground)]">
                Tenant cluster isolated namespace pending initialization.
              </div>
            </div>
          </div>
          <Button
            variant="danger"
            size="sm"
            onClick={() => retriggerMutation.mutate()}
            isLoading={retriggerMutation.isPending}
            iconLeft={<RefreshCw size={12} />}
          >
            Retry Setup
          </Button>
        </CardContent>
      </Card>
    );
  }

  const isReady = infra?.status === 'ready';
  const maxPods = infra?.quota?.max_pods || infra?.quota?.pods || '20';
  const maxCpu = infra?.quota?.max_cpu || infra?.quota?.cpu_requested || '4 Cores';
  const maxMem = infra?.quota?.max_memory || infra?.quota?.memory_requested || '8 GiB';

  return (
    <Card accentColor={isReady ? 'primary' : 'warning'}>
      <CardContent className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div
            style={{
              padding: 10,
              borderRadius: 8,
              backgroundColor: isReady ? 'rgba(0, 212, 170, 0.1)' : 'rgba(245, 158, 11, 0.1)',
              border: `1px solid ${isReady ? 'rgba(0, 212, 170, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
            }}
          >
            <Server
              size={22}
              className={isReady ? 'text-[var(--primary)]' : 'text-[var(--warning)]'}
            />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <span className="font-display font-bold text-sm text-[var(--foreground)] uppercase tracking-wide">
                Tenant Kubernetes Environment
              </span>
              <Badge variant={isReady ? 'success' : 'warning'} showDot pulseDot={!isReady}>
                {isReady ? 'READY' : 'PROVISIONING'}
              </Badge>
            </div>
            <div className="text-xs font-mono text-[var(--muted-foreground)] mt-1">
              Namespace:{' '}
              <span className="text-[var(--primary)]">{infra?.namespace || 'pantheon-tenant'}</span>{' '}
              | Security: <span className="text-[var(--success)]">Default-Deny Enforced</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 border-t md:border-t-0 border-[var(--card-border)] pt-3 md:pt-0">
          <div className="text-right hidden sm:block">
            <div className="text-[11px] font-mono text-[var(--muted-foreground)] uppercase">
              Hard Quota Limits
            </div>
            <div className="text-xs font-mono font-bold text-[var(--foreground)] mt-0.5">
              {maxPods} Pods | {maxCpu} CPU | {maxMem} RAM
            </div>
          </div>
          {isReady ? (
            <Badge variant="success" showDot>
              Isolated & Active
            </Badge>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={() => retriggerMutation.mutate()}
              isLoading={retriggerMutation.isPending}
              iconLeft={<RefreshCw size={12} />}
            >
              Provision Now
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
