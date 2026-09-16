import {
  Database,
  Download,
  Filter,
  Layers,
  Lock,
  Play,
  Plus,
  Search,
  Shield,
  Sparkles,
  Terminal,
  Trash2,
} from 'lucide-react';
import React, { useState } from 'react';

import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CodeBlock,
  Input,
  Modal,
  Select,
  SeverityBadge,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Textarea,
  ThemeSwitcher,
} from '../components/ui';
import { useThemeStore } from '../stores/themeStore';

export const DesignPreviewPage: React.FC = () => {
  const { theme } = useThemeStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [btnLoading, setBtnLoading] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [selectValue, setSelectValue] = useState('sqli');

  const triggerLoading = () => {
    setBtnLoading(true);
    setTimeout(() => setBtnLoading(false), 2000);
  };

  return (
    <div className="page-container animate-fade-in space-y-8">
      {/* Page Header */}
      <div className="page-header border-b border-[var(--card-border)] pb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="page-title">Design System Foundation</h1>
            <Badge variant="primary">Phase 1 Preview</Badge>
            <Badge variant="accent">
              {theme === 'matte-mono' ? 'Matte Studio' : 'Cyber Obsidian'}
            </Badge>
          </div>
          <p className="page-subtitle">
            Token specs, brand identity guidelines, shared primitives, and dark theme variations.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ThemeSwitcher />
          <Button
            variant="primary"
            iconLeft={<Sparkles size={14} />}
            onClick={() => setIsModalOpen(true)}
          >
            Test Interactive Modal
          </Button>
        </div>
      </div>

      {/* 1. Brand Identity Guidelines Palette (Minimal & Sophisticated) */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-semibold text-sm uppercase tracking-wider text-[var(--foreground)] flex items-center gap-2">
            <Layers size={16} className="text-[var(--primary)]" />
            Brand Identity Guidelines — Monochrome Color Palette
          </h2>
          <span className="font-mono text-[10px] text-[var(--muted-foreground)]">
            PACKAGING DESIGN STUDIO · CREATIVE WISE
          </span>
        </div>

        <p className="text-xs text-[var(--secondary-foreground)] leading-relaxed max-w-3xl">
          Our color palette is minimal, timeless and sophisticated. It reflects our brand personality
          and ensures consistency across all applications.
        </p>

        {/* 5-Color Grid from Brand Identity Spec */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          {/* Matte Black */}
          <div className="p-4 rounded border border-[var(--card-border)] bg-[var(--card)] flex flex-col justify-between">
            <div>
              <div
                className="h-16 rounded mb-3 border border-white/10 shadow-inner"
                style={{ backgroundColor: '#0F0F10' }}
              />
              <div className="font-display font-bold text-sm tracking-wider text-[var(--foreground)]">
                MATTE BLACK
              </div>
              <div className="font-mono text-xs text-[var(--secondary-foreground)] mt-0.5">
                #0F0F10
              </div>
            </div>
            <div className="font-mono text-[10px] text-[var(--muted-foreground)] space-y-0.5 pt-3 border-t border-[var(--card-border)] mt-3">
              <div>RGB 15 15 16</div>
              <div>CMYK 60 60 60 100</div>
              <div className="text-[var(--foreground)]">PANTONE Black 6 C</div>
            </div>
          </div>

          {/* Charcoal */}
          <div className="p-4 rounded border border-[var(--card-border)] bg-[var(--card)] flex flex-col justify-between">
            <div>
              <div
                className="h-16 rounded mb-3 border border-white/10 shadow-inner"
                style={{ backgroundColor: '#232323' }}
              />
              <div className="font-display font-bold text-sm tracking-wider text-[var(--foreground)]">
                CHARCOAL
              </div>
              <div className="font-mono text-xs text-[var(--secondary-foreground)] mt-0.5">
                #232323
              </div>
            </div>
            <div className="font-mono text-[10px] text-[var(--muted-foreground)] space-y-0.5 pt-3 border-t border-[var(--card-border)] mt-3">
              <div>RGB 35 35 35</div>
              <div>CMYK 0 0 0 85</div>
              <div className="text-[var(--foreground)]">PANTONE 432 C</div>
            </div>
          </div>

          {/* Silver */}
          <div className="p-4 rounded border border-[var(--card-border)] bg-[var(--card)] flex flex-col justify-between">
            <div>
              <div
                className="h-16 rounded mb-3 border border-black/20 shadow-inner"
                style={{ backgroundColor: '#C8C8C8' }}
              />
              <div className="font-display font-bold text-sm tracking-wider text-[var(--foreground)]">
                SILVER
              </div>
              <div className="font-mono text-xs text-[var(--secondary-foreground)] mt-0.5">
                #C8C8C8
              </div>
            </div>
            <div className="font-mono text-[10px] text-[var(--muted-foreground)] space-y-0.5 pt-3 border-t border-[var(--card-border)] mt-3">
              <div>RGB 200 200 200</div>
              <div>CMYK 0 0 0 20</div>
              <div className="text-[var(--foreground)]">PANTONE 877 C</div>
            </div>
          </div>

          {/* Light Gray */}
          <div className="p-4 rounded border border-[var(--card-border)] bg-[var(--card)] flex flex-col justify-between">
            <div>
              <div
                className="h-16 rounded mb-3 border border-black/20 shadow-inner"
                style={{ backgroundColor: '#EAEAEA' }}
              />
              <div className="font-display font-bold text-sm tracking-wider text-[var(--foreground)]">
                LIGHT GRAY
              </div>
              <div className="font-mono text-xs text-[var(--secondary-foreground)] mt-0.5">
                #EAEAEA
              </div>
            </div>
            <div className="font-mono text-[10px] text-[var(--muted-foreground)] space-y-0.5 pt-3 border-t border-[var(--card-border)] mt-3">
              <div>RGB 234 234 234</div>
              <div>CMYK 0 0 0 8</div>
              <div className="text-[var(--muted-foreground)] opacity-50">—</div>
            </div>
          </div>

          {/* Pure White */}
          <div className="p-4 rounded border border-[var(--card-border)] bg-[var(--card)] flex flex-col justify-between">
            <div>
              <div
                className="h-16 rounded mb-3 border border-black/20 shadow-inner"
                style={{ backgroundColor: '#FFFFFF' }}
              />
              <div className="font-display font-bold text-sm tracking-wider text-[var(--foreground)]">
                PURE WHITE
              </div>
              <div className="font-mono text-xs text-[var(--secondary-foreground)] mt-0.5">
                #FFFFFF
              </div>
            </div>
            <div className="font-mono text-[10px] text-[var(--muted-foreground)] space-y-0.5 pt-3 border-t border-[var(--card-border)] mt-3">
              <div>RGB 255 255 255</div>
              <div>CMYK 0 0 0 0</div>
              <div className="text-[var(--muted-foreground)] opacity-50">—</div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Active Theme Live Tokens */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-semibold text-sm uppercase tracking-wider text-[var(--foreground)] flex items-center gap-2">
            <Layers size={16} className="text-[var(--primary)]" />
            Active Theme Tokens (Dynamically Reacts to Theme Toggle)
          </h2>
          <ThemeSwitcher variant="compact" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3">
          <div className="p-3 rounded border border-[var(--card-border)] bg-[var(--card)]">
            <div className="h-8 rounded mb-2 bg-[var(--background)] border border-white/10" />
            <div className="font-mono text-[10px] text-[var(--foreground)]">--background</div>
            <div className="font-mono text-[9px] text-[var(--muted-foreground)]">Canvas surface</div>
          </div>
          <div className="p-3 rounded border border-[var(--card-border)] bg-[var(--card)]">
            <div className="h-8 rounded mb-2 bg-[var(--sidebar)] border border-white/10" />
            <div className="font-mono text-[10px] text-[var(--foreground)]">--sidebar</div>
            <div className="font-mono text-[9px] text-[var(--muted-foreground)]">Nav sidebar</div>
          </div>
          <div className="p-3 rounded border border-[var(--card-border)] bg-[var(--card)]">
            <div className="h-8 rounded mb-2 bg-[var(--card)] border border-[var(--card-border)]" />
            <div className="font-mono text-[10px] text-[var(--foreground)]">--card</div>
            <div className="font-mono text-[9px] text-[var(--muted-foreground)]">Elevated card</div>
          </div>
          <div className="p-3 rounded border border-[var(--card-border)] bg-[var(--card)]">
            <div className="h-8 rounded mb-2 bg-[var(--card-border)] border border-white/10" />
            <div className="font-mono text-[10px] text-[var(--foreground)]">--card-border</div>
            <div className="font-mono text-[9px] text-[var(--muted-foreground)]">Dividers / lines</div>
          </div>
          <div className="p-3 rounded border border-[var(--card-border)] bg-[var(--card)]">
            <div className="h-8 rounded mb-2 bg-[var(--primary)] border border-[var(--card-border)] shadow-sm" />
            <div className="font-mono text-[10px] text-[var(--foreground)]">--primary</div>
            <div className="font-mono text-[9px] text-[var(--muted-foreground)]">Key action</div>
          </div>
          <div className="p-3 rounded border border-[var(--card-border)] bg-[var(--card)]">
            <div className="h-8 rounded mb-2 bg-[var(--accent)] border border-[var(--card-border)] shadow-sm" />
            <div className="font-mono text-[10px] text-[var(--foreground)]">--accent</div>
            <div className="font-mono text-[9px] text-[var(--muted-foreground)]">Secondary highlight</div>
          </div>
          <div className="p-3 rounded border border-[var(--card-border)] bg-[var(--card)]">
            <div className="h-8 rounded mb-2 bg-[var(--danger)] border border-[var(--card-border)] shadow-sm" />
            <div className="font-mono text-[10px] text-[var(--foreground)]">--danger</div>
            <div className="font-mono text-[9px] text-[var(--muted-foreground)]">Critical alert</div>
          </div>
        </div>
      </section>

      {/* 2. Component Primitives Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Buttons Showcase */}
        <Card accentColor="primary">
          <CardHeader>
            <CardTitle>Button Primitives</CardTitle>
            <CardDescription>Variants, sizes, states, and icon configurations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="primary" iconLeft={<Play size={14} />}>
                Run Attack Test
              </Button>
              <Button variant="secondary" iconLeft={<Filter size={14} />}>
                Filter Findings
              </Button>
              <Button variant="danger" iconLeft={<Trash2 size={14} />}>
                Kill Switch
              </Button>
              <Button variant="ghost">Cancel</Button>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button variant="primary" size="sm" iconLeft={<Plus size={12} />}>
                Add Target
              </Button>
              <Button variant="primary" size="md">
                Standard Button
              </Button>
              <Button variant="primary" size="lg" iconRight={<Download size={14} />}>
                Export PDF Report
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Button variant="primary" isLoading={btnLoading} onClick={triggerLoading}>
                {btnLoading ? 'Simulating...' : 'Test Async Action'}
              </Button>
              <Button variant="primary" disabled>
                Disabled State
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Badges & Severity Mapping */}
        <Card accentColor="accent">
          <CardHeader>
            <CardTitle>Badges & Security Severity</CardTitle>
            <CardDescription>
              Status indicators and standardized severity colors (PRD §5)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <div className="text-xs font-mono text-[var(--muted-foreground)]">
                SYSTEM STATUS BADGES
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant="primary" showDot pulseDot>
                  Active Run
                </Badge>
                <Badge variant="success" showDot>
                  Cluster Ready
                </Badge>
                <Badge variant="warning">Provisioning</Badge>
                <Badge variant="danger">Broker Closed</Badge>
                <Badge variant="info">Phase 1</Badge>
                <Badge variant="accent">AI Agent</Badge>
                <Badge variant="neutral">Draft</Badge>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs font-mono text-[var(--muted-foreground)]">
                FINDING SEVERITY MAPPING
              </div>
              <div className="flex flex-wrap gap-2">
                <SeverityBadge level="critical" />
                <SeverityBadge level="high" />
                <SeverityBadge level="medium" />
                <SeverityBadge level="low" />
                <SeverityBadge level="info" />
                <SeverityBadge level="resolved" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 3. Form Inputs Showcase */}
      <Card accentColor="info">
        <CardHeader>
          <CardTitle>Form Control Primitives</CardTitle>
          <CardDescription>
            Dark mode inputs, dropdown selects, and monospaced textareas
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Input
            label="Target Service URL"
            placeholder="http://api.tenant-alpha.internal:8000"
            leftIcon={<Search size={14} />}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            helperText="Internal route broker proxy address"
          />

          <Select
            label="Scenario Type"
            options={[
              { value: 'sqli', label: 'SQL Injection (Blind & Time-Based)' },
              { value: 'xss', label: 'Cross-Site Scripting (Reflected)' },
              { value: 'auth_bypass', label: 'JWT Signature Bypass' },
              { value: 'dos', label: 'HTTP Flood DDoS' },
            ]}
            value={selectValue}
            onChange={(e) => setSelectValue(e.target.value)}
            helperText="Preset simulation payload"
          />

          <Input
            label="API Key / Auth Header"
            placeholder="Bearer pth_live_8923..."
            leftIcon={<Lock size={14} />}
            error="Required for private endpoints"
          />

          <div className="md:col-span-3">
            <Textarea
              label="Custom Attack Vector Script (YAML)"
              placeholder={`steps:\n  - name: Auth Probe\n    path: /api/v1/auth/login\n    method: POST`}
              helperText="Monospaced editor formatting with input validation"
            />
          </div>
        </CardContent>
      </Card>

      {/* 4. Alert Callouts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Alert type="info" title="Route Broker Safety Active">
          The kill switch is currently armed. All outbound attack traffic will expire in 15 minutes
          automatically.
        </Alert>
        <Alert type="danger" title="Safety Policy Warning">
          Attempting to target external IP ranges outside the tenant cluster is strictly prohibited
          and logged.
        </Alert>
      </div>

      {/* 5. Data Table Specimen */}
      <Card>
        <CardHeader>
          <CardTitle>Data Table Primitive</CardTitle>
          <CardDescription>Live active runs and tenant cluster resource metrics</CardDescription>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Target App</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Route Expiry</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell className="font-mono font-medium text-[var(--primary)] flex items-center gap-2">
                <Database size={14} />
                payment-gateway-v2
              </TableCell>
              <TableCell>
                <Badge variant="success" showDot pulseDot>
                  RUNNING
                </Badge>
              </TableCell>
              <TableCell>
                <SeverityBadge level="high" />
              </TableCell>
              <TableCell className="font-mono text-xs text-[var(--secondary-foreground)]">
                14m 22s
              </TableCell>
              <TableCell className="text-right">
                <Button variant="danger" size="sm">
                  Stop
                </Button>
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="font-mono font-medium text-[var(--primary)] flex items-center gap-2">
                <Shield size={14} />
                auth-service
              </TableCell>
              <TableCell>
                <Badge variant="info">COMPLETED</Badge>
              </TableCell>
              <TableCell>
                <SeverityBadge level="critical" />
              </TableCell>
              <TableCell className="font-mono text-xs text-[var(--secondary-foreground)]">
                Expired
              </TableCell>
              <TableCell className="text-right">
                <Button variant="secondary" size="sm">
                  View Report
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>

      {/* 6. Code Block / Log Viewer */}
      <section className="space-y-3">
        <h2 className="font-display font-semibold text-sm uppercase tracking-wider text-[var(--foreground)] flex items-center gap-2">
          <Terminal size={16} className="text-[var(--primary)]" />
          Code & Log Viewer Primitive
        </h2>
        <CodeBlock
          filename="attack-runner.log"
          language="json"
          code={`{\n  "timestamp": "2026-08-07T14:45:00Z",\n  "event": "route_broker_opened",\n  "tenant_id": "org_pantheon_test",\n  "route": "http://10.96.0.45:8000",\n  "kill_switch_active": true,\n  "ttl_seconds": 900\n}`}
        />
      </section>

      {/* Modal Demonstration */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Interactive Modal Primitive"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Close
            </Button>
            <Button variant="primary" onClick={() => setIsModalOpen(false)}>
              Confirm Action
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Alert type="warning" title="Safety System">
            This dialog modal primitive is fully accessible with ESC key handling and backdrop blur
            effects.
          </Alert>
          <p>
            All components in the design system use predefined tokens from{' '}
            <code className="font-mono text-[var(--primary)]">src/index.css</code> and CSS
            variables.
          </p>
        </div>
      </Modal>
    </div>
  );
};
