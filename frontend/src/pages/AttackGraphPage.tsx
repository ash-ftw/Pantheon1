/**
 * AttackGraphPage — PRD Module 12 / Module 9 (Phase 10: Attack Graph & Replay Engine).
 *
 * Implements:
 * 1. Interactive React Flow Attack Graph canvas (@xyflow/react)
 * 2. Custom AttackNode & AttackEdge components with status color coding:
 *    (probing = cyan, safe = emerald, blocked = amber, compromised = crimson red)
 * 3. Step-by-Step Replay Mode with timeline scrubber, play/pause, and step-forward/back
 * 4. Real-time Live Run WebSocket streaming sync for active attack scenarios
 * 5. Node Inspector Drawer for deep forensic metadata examination
 */

import {
  Background,
  BaseEdge,
  Controls,
  getBezierPath,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  ChevronLeft,
  ChevronRight,
  Database,
  FastForward,
  Flame,
  GitBranch,
  Globe,
  Network,
  Pause,
  Play,
  RefreshCw,
  Rewind,
  Server,
  Shield,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useAuthStore } from '../stores/authStore';
import { useThemeStore } from '../stores/themeStore';
import './AttackGraphPage.css';

/* ------------------------------------------------------------------ */
/*  Types & Interfaces                                                */
/* ------------------------------------------------------------------ */

export interface AttackNodeData extends Record<string, unknown> {
  label: string;
  nodeType: string;
  status: 'probing' | 'safe' | 'blocked' | 'compromised';
  stepDiscovered: number;
  isCurrentStep?: boolean;
  metadata?: Record<string, unknown>;
}

export type AttackNodeType = Node<AttackNodeData, 'attackNode'>;

export interface AttackEdgeData extends Record<string, unknown> {
  status: 'probing' | 'traversed' | 'blocked' | 'compromised';
  stepDiscovered: number;
  label?: string;
  isCurrentStep?: boolean;
  metadata?: Record<string, unknown>;
}

export type AttackEdgeType = Edge<AttackEdgeData, 'attackEdge'>;

interface TestRunSummary {
  id: string;
  scenario_name: string;
  scenario_category: string;
  status: string;
  current_step: number;
  total_steps: number;
  node_count: number;
  edge_count: number;
  findings_count: number;
  created_at: string;
}

interface RawGraphNode {
  id: string;
  label: string;
  type: string;
  status: 'probing' | 'safe' | 'blocked' | 'compromised';
  step_discovered: number;
  position: { x: number; y: number };
  metadata: Record<string, unknown>;
}

interface RawGraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  status: 'probing' | 'traversed' | 'blocked' | 'compromised';
  step_discovered: number;
  metadata: Record<string, unknown>;
}

const API_BASE = '/api';

/* ------------------------------------------------------------------ */
/* ------------------------------------------------------------------ */
/*  Custom React Flow Node Component                                  */
/* ------------------------------------------------------------------ */

function AttackNodeComponent({ data }: NodeProps<AttackNodeType>) {
  const { label, nodeType, status, stepDiscovered, isCurrentStep, metadata } = data;
  const isMatte = useThemeStore((s) => s.theme === 'matte-mono');

  const getNodeIcon = () => {
    switch (nodeType.toLowerCase()) {
      case 'attacker':
        return <Flame size={15} color={isMatte ? '#ffffff' : '#00d4aa'} />;
      case 'route':
        return <Network size={15} color={isMatte ? '#c8c8c8' : '#00d4aa'} />;
      case 'database':
        return <Database size={15} color={isMatte ? '#eaeaea' : '#ef4444'} />;
      case 'service':
        return <Server size={15} color={isMatte ? '#a8a8b0' : '#fbbf24'} />;
      default:
        return <Globe size={15} color={isMatte ? '#8a8a93' : '#94a3b8'} />;
    }
  };

  return (
    <div
      className={`attack-node-card ${status} ${isCurrentStep ? 'is-current-step' : ''}`}
      id={`node-${label}`}
    >
      <Handle type="target" position={Position.Left} />

      <div className="attack-node-header">
        <div className="attack-node-icon-row">
          <div className="attack-node-icon">{getNodeIcon()}</div>
          <span className="attack-node-type-label">{nodeType}</span>
        </div>
        <div className="flex items-center gap-1">
          {isCurrentStep && (
            <span className="current-step-indicator">
              <span className="current-step-dot" /> ACTIVE
            </span>
          )}
          <span className={`attack-node-badge badge-${status}`}>
            <span className={`status-dot status-dot-${status}`} />
            {status}
          </span>
        </div>
      </div>

      <div className="attack-node-title">{label}</div>

      <div className="attack-node-footer">
        <span>Step {stepDiscovered}</span>
        {metadata && typeof metadata.severity === 'string' && (
          <span style={{ color: '#ef4444', fontWeight: 700 }}>
            {metadata.severity.toUpperCase()}
          </span>
        )}
      </div>

      <Handle type="source" position={Position.Right} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Custom React Flow Edge Component                                  */
/* ------------------------------------------------------------------ */

function AttackEdgeComponent(props: EdgeProps<AttackEdgeType>) {
  const { id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data } = props;
  const isMatte = useThemeStore((s) => s.theme === 'matte-mono');

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const status = data?.status || 'traversed';
  const label = data?.label;
  const isCurrentStep = data?.isCurrentStep ?? false;

  let strokeColor = isMatte ? '#ffffff' : '#00d4aa';
  let strokeDasharray = 'none';

  if (status === 'compromised') {
    strokeColor = isMatte ? '#8a8a93' : '#ef4444';
    strokeDasharray = '6 4';
  } else if (status === 'blocked') {
    strokeColor = isMatte ? '#6e6e73' : '#f59e0b';
    strokeDasharray = '6 4';
  } else if (status === 'probing') {
    strokeColor = isMatte ? '#c8c8c8' : '#00d4aa';
    strokeDasharray = '4 4';
  }

  return (
    <g className="attack-edge-group">
      {/* Main clean edge path */}
      <BaseEdge
        id={id}
        path={edgePath}
        className={`attack-edge-path ${status} ${isCurrentStep ? 'current-step' : ''}`}
        style={{
          stroke: strokeColor,
          strokeWidth: status === 'compromised' || isCurrentStep ? 2.5 : 2,
          strokeDasharray,
        }}
      />

      {label && (
        <foreignObject
          width={140}
          height={28}
          x={labelX - 70}
          y={labelY - 14}
          requiredExtensions="http://www.w3.org/1999/xhtml"
        >
          <div
            className={`attack-edge-label ${status} ${isCurrentStep ? 'current-step' : ''}`}
            style={{
              background: isMatte ? '#141416' : '#090d14',
              border: `1px solid ${isMatte ? '#2e2e32' : strokeColor}`,
              borderRadius: '3px',
              padding: '2px 8px',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              color: isMatte ? '#eaeaea' : '#e2e8f0',
              textAlign: 'center',
              textOverflow: 'ellipsis',
              overflow: 'hidden',
              whiteSpace: 'nowrap',
            }}
          >
            {label}
          </div>
        </foreignObject>
      )}
    </g>
  );
}

const nodeTypes = {
  attackNode: AttackNodeComponent,
};

const edgeTypes = {
  attackEdge: AttackEdgeComponent,
};

/* ------------------------------------------------------------------ */
/*  Interactive React Flow Canvas Wrapper with Auto-Fit & HUD         */
/* ------------------------------------------------------------------ */

function AttackFlowCanvas({
  nodes,
  edges,
  onNodeClick,
  currentStep,
  isRunning,
}: {
  nodes: AttackNodeType[];
  edges: AttackEdgeType[];
  onNodeClick: (_: React.MouseEvent, node: Node) => void;
  currentStep: number;
  isRunning: boolean;
}) {
  const { fitView } = useReactFlow();
  const isMatte = useThemeStore((s) => s.theme === 'matte-mono');

  return (
    <div className="attack-flow-canvas-container">
      {/* Live Simulation Cyber HUD */}
      <div className="canvas-hud-overlay">
        <div className="canvas-hud-pill">
          <span className={`hud-pulse-light ${isRunning ? 'live' : 'idle'}`} />
          <span className="hud-title">
            {isRunning ? 'LIVE ATTACK SYNCHRONIZATION' : 'TOPOLOGY REPLAY ENGINE'}
          </span>
          <span className="hud-divider">|</span>
          <span className="hud-step">CURRENT FOCUS: STEP {currentStep}</span>
        </div>

        <button
          type="button"
          className="canvas-hud-btn"
          onClick={() => fitView({ duration: 500, padding: 0.25 })}
          title="Reset Zoom & Fit Topology"
        >
          Auto Fit View
        </button>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color={isMatte ? '#232323' : '#141e2e'} gap={24} size={1.5} />
        <Controls />
      </ReactFlow>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main AttackGraphPage Component                                    */
/* ------------------------------------------------------------------ */

export function AttackGraphPage() {
  const token = useAuthStore((s) => s.token);
  const isMatte = useThemeStore((s) => s.theme === 'matte-mono');

  // Runs and selection state
  const [runs, setRuns] = useState<TestRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingGraph, setLoadingGraph] = useState(false);

  // Raw Graph Data from API
  const [rawNodes, setRawNodes] = useState<RawGraphNode[]>([]);
  const [rawEdges, setRawEdges] = useState<RawGraphEdge[]>([]);

  // Replay Controller State
  const [isReplayMode, setIsReplayMode] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // Selected Node Drawer
  const [selectedNode, setSelectedNode] = useState<AttackNodeData | null>(null);

  // WebSocket reference for live run streaming
  const wsRef = useRef<WebSocket | null>(null);

  /* ------------------------------------------------------------------ */
  /*  Data Fetching                                                     */
  /* ------------------------------------------------------------------ */

  const fetchRuns = useCallback(async () => {
    try {
      setLoadingRuns(true);
      const res = await fetch(`${API_BASE}/attack-graph/runs`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data: TestRunSummary[] = await res.json();
        setRuns(data);
        if (data.length > 0 && !selectedRunId) {
          // Default to first run or running run
          const active = data.find((r) => r.status === 'running') || data[0];
          setSelectedRunId(active.id);
        }
      }
    } catch {
      // Non-blocking
    } finally {
      setLoadingRuns(false);
    }
  }, [token, selectedRunId]);

  const fetchGraph = useCallback(
    async (runId: string) => {
      if (!runId) return;
      try {
        setLoadingGraph(true);
        const res = await fetch(`${API_BASE}/test-runs/${runId}/graph`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) {
          const data = await res.json();
          const nodes: RawGraphNode[] = data.nodes || [];
          const edges: RawGraphEdge[] = data.edges || [];

          setRawNodes(nodes);
          setRawEdges(edges);

          // Find max step
          const maxS = nodes.reduce((acc, n) => Math.max(acc, n.step_discovered || 0), 0);
          setCurrentStep(maxS);
        }
      } catch {
        // Non-blocking
      } finally {
        setLoadingGraph(false);
      }
    },
    [token],
  );

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    if (selectedRunId) {
      fetchGraph(selectedRunId);
    }
  }, [selectedRunId, fetchGraph]);

  /* ------------------------------------------------------------------ */
  /*  Live Run WebSocket Streaming Sync                                 */
  /* ------------------------------------------------------------------ */

  const currentRun = useMemo(() => runs.find((r) => r.id === selectedRunId), [runs, selectedRunId]);
  const isRunning = currentRun?.status === 'running';

  useEffect(() => {
    if (!selectedRunId || !isRunning) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/test-runs/${selectedRunId}/ws`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const { event: evtType, data } = payload;

        if (evtType === 'graph_updated' && data) {
          if (Array.isArray(data.nodes)) setRawNodes(data.nodes);
          if (Array.isArray(data.edges)) setRawEdges(data.edges);
          const maxS = (data.nodes || []).reduce(
            (acc: number, n: RawGraphNode) => Math.max(acc, n.step_discovered || 0),
            0,
          );
          setCurrentStep(maxS);
        } else if (evtType === 'step_started') {
          setCurrentStep(data.current_step);
        } else if (evtType === 'run_completed' || evtType === 'run_stopped') {
          fetchGraph(selectedRunId);
          fetchRuns();
        }
      } catch {
        // Non-fatal
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [selectedRunId, isRunning, fetchGraph, fetchRuns]);

  /* ------------------------------------------------------------------ */
  /*  Replay Mode Filtering & Playback Timer                            */
  /* ------------------------------------------------------------------ */

  const maxStep = useMemo(() => {
    return rawNodes.reduce((acc, n) => Math.max(acc, n.step_discovered || 0), 0);
  }, [rawNodes]);

  useEffect(() => {
    if (!isPlaying) return;

    const timer = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= maxStep) {
          setIsPlaying(false);
          return maxStep;
        }
        return prev + 1;
      });
    }, 1500);

    return () => clearInterval(timer);
  }, [isPlaying, maxStep]);

  // Nodes & Edges filtered by currentStep in Replay Mode
  const displayNodes: AttackNodeType[] = useMemo(() => {
    return rawNodes
      .filter((n) => (!isReplayMode ? true : n.step_discovered <= currentStep))
      .map((n) => ({
        id: n.id,
        type: 'attackNode',
        position: n.position || { x: 100, y: 100 },
        data: {
          label: n.label,
          nodeType: n.type,
          status: n.status,
          stepDiscovered: n.step_discovered,
          isCurrentStep: isReplayMode
            ? n.step_discovered === currentStep && currentStep > 0
            : false,
          metadata: n.metadata,
        },
      }));
  }, [rawNodes, isReplayMode, currentStep]);

  const displayEdges: AttackEdgeType[] = useMemo(() => {
    const visibleNodeIds = new Set(displayNodes.map((n) => n.id));
    return rawEdges
      .filter((e) => {
        if (!visibleNodeIds.has(e.source) || !visibleNodeIds.has(e.target)) return false;
        return !isReplayMode ? true : e.step_discovered <= currentStep;
      })
      .map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'attackEdge',
        data: {
          status: e.status,
          stepDiscovered: e.step_discovered,
          label: e.label,
          isCurrentStep: isReplayMode
            ? e.step_discovered === currentStep && currentStep > 0
            : false,
          metadata: e.metadata,
        },
      }));
  }, [rawEdges, displayNodes, isReplayMode, currentStep]);

  // Derived stats
  const compromisedCount = useMemo(
    () => rawNodes.filter((n) => n.status === 'compromised').length,
    [rawNodes],
  );
  const blockedCount = useMemo(
    () => rawNodes.filter((n) => n.status === 'blocked').length,
    [rawNodes],
  );

  const onNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNode(node.data as AttackNodeData);
  };

  /* ------------------------------------------------------------------ */
  /*  Render                                                            */
  /* ------------------------------------------------------------------ */

  return (
    <div className="page-container attack-graph-container animate-fade-in">
      {/* Top Header */}
      <div className="attack-graph-header">
        <div>
          <h1 className="page-title">
            <GitBranch className="page-title-icon" /> Attack Graph &amp; Replay Engine
          </h1>
          <p className="page-subtitle">
            Visualise full multi-stage attack paths, compromised assets, and security guard blocks.
            Scrub historical executions step-by-step with timeline replay.
          </p>
        </div>

        <div className="attack-graph-header-actions">
          {/* Test Run Selector */}
          <select
            className="run-select-dropdown"
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
            disabled={loadingRuns || runs.length === 0}
            aria-label="Select Test Run to Inspect"
          >
            {runs.length === 0 ? (
              <option value="">No simulation runs found</option>
            ) : (
              runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.scenario_name} ({r.status.toUpperCase()}) —{' '}
                  {new Date(r.created_at).toLocaleTimeString()}
                </option>
              ))
            )}
          </select>

          <button
            type="button"
            className={`btn ${isReplayMode ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setIsReplayMode(!isReplayMode)}
            title="Toggle Replay Mode"
          >
            {isReplayMode ? 'Replay Mode: Active' : 'Full Topology'}
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              fetchRuns();
              if (selectedRunId) fetchGraph(selectedRunId);
            }}
            title="Refresh Attack Graph"
          >
            <RefreshCw size={15} /> Refresh
          </button>
        </div>
      </div>

      {/* Summary Stats Cards */}
      <div className="attack-graph-stats">
        <div className="attack-graph-stat-card">
          <div className="attack-graph-stat-label">Total Graph Nodes</div>
          <div className="attack-graph-stat-val">
            {displayNodes.length} / {rawNodes.length}
          </div>
        </div>

        <div className="attack-graph-stat-card">
          <div className="attack-graph-stat-label">Active Attack Paths</div>
          <div className="attack-graph-stat-val" style={{ color: isMatte ? '#ffffff' : '#00d4aa' }}>
            {displayEdges.length} / {rawEdges.length}
          </div>
        </div>

        <div className="attack-graph-stat-card danger">
          <div className="attack-graph-stat-label">Compromised Targets</div>
          <div
            className="attack-graph-stat-val"
            style={{ color: isMatte ? '#c8c8c8' : 'var(--danger)' }}
          >
            {compromisedCount}
          </div>
        </div>

        <div className="attack-graph-stat-card">
          <div className="attack-graph-stat-label">Defended / Blocked</div>
          <div className="attack-graph-stat-val" style={{ color: isMatte ? '#a8a8b0' : '#f59e0b' }}>
            {blockedCount}
          </div>
        </div>

        <div className="attack-graph-stat-card">
          <div className="attack-graph-stat-label">Execution Depth</div>
          <div
            className="attack-graph-stat-val"
            style={{ color: isMatte ? '#ffffff' : 'var(--primary)' }}
          >
            Step {currentStep} / {maxStep}
          </div>
        </div>
      </div>

      {/* Replay Controller Bar */}
      <div className="replay-controller-card" id="replay-timeline-controller">
        <div className="replay-controller-top">
          <div className="replay-buttons">
            <button
              type="button"
              className="replay-btn"
              onClick={() => {
                setIsPlaying(false);
                setCurrentStep(0);
              }}
              disabled={currentStep === 0}
              title="Jump to Start"
            >
              <Rewind size={14} /> Start
            </button>

            <button
              type="button"
              className="replay-btn"
              onClick={() => {
                setIsPlaying(false);
                setCurrentStep((prev) => Math.max(0, prev - 1));
              }}
              disabled={currentStep === 0}
              title="Previous Step"
            >
              <ChevronLeft size={16} /> Prev
            </button>

            <button
              type="button"
              className={`replay-btn ${isPlaying ? 'primary' : ''}`}
              onClick={() => {
                if (currentStep >= maxStep) setCurrentStep(0);
                setIsPlaying(!isPlaying);
              }}
              title={isPlaying ? 'Pause Replay' : 'Play Step-by-Step Replay'}
            >
              {isPlaying ? <Pause size={14} /> : <Play size={14} />}
              {isPlaying ? 'Pause' : 'Play Replay'}
            </button>

            <button
              type="button"
              className="replay-btn"
              onClick={() => {
                setIsPlaying(false);
                setCurrentStep((prev) => Math.min(maxStep, prev + 1));
              }}
              disabled={currentStep >= maxStep}
              title="Next Step"
            >
              Next <ChevronRight size={16} />
            </button>

            <button
              type="button"
              className="replay-btn"
              onClick={() => {
                setIsPlaying(false);
                setCurrentStep(maxStep);
              }}
              disabled={currentStep >= maxStep}
              title="Jump to End"
            >
              End <FastForward size={14} />
            </button>
          </div>

          <div className="flex items-center gap-3">
            {isRunning && (
              <span className="badge badge-success flex items-center gap-1">
                <span className="pulsing-indicator" /> LIVE EXECUTION
              </span>
            )}
            <span className="replay-step-badge">
              Viewing Timeline: Step {currentStep} of {maxStep}
            </span>
          </div>
        </div>

        {/* Scrubber Range Slider */}
        <div className="replay-slider-container">
          <span className="font-mono text-xs text-muted">0</span>
          <input
            type="range"
            min={0}
            max={maxStep || 1}
            value={currentStep}
            onChange={(e) => {
              setIsPlaying(false);
              setCurrentStep(Number(e.target.value));
            }}
            className="replay-slider"
            aria-label="Replay Timeline Scrubber"
          />
          <span className="font-mono text-xs text-muted">{maxStep}</span>
        </div>
      </div>

      {/* React Flow Graph Canvas */}
      <div className="graph-canvas-wrapper">
        <div className="graph-canvas-area">
          {loadingGraph ? (
            <div className="flex items-center justify-center h-full text-muted">
              Loading attack graph topology...
            </div>
          ) : rawNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-muted">
              <GitBranch size={40} className="text-muted-foreground" />
              <span>No attack graph recorded for this simulation run.</span>
            </div>
          ) : (
            <ReactFlowProvider>
              <AttackFlowCanvas
                nodes={displayNodes}
                edges={displayEdges}
                onNodeClick={onNodeClick}
                currentStep={currentStep}
                isRunning={isRunning}
              />
            </ReactFlowProvider>
          )}
        </div>

        {/* Forensic Node Inspector Sidebar */}
        {selectedNode && (
          <aside className="node-inspector-sidebar" id="node-inspector">
            <div className="node-inspector-header">
              <div className="flex items-center gap-2">
                <Shield size={16} color={isMatte ? '#ffffff' : '#00d4aa'} />
                <span className="node-inspector-title">Forensic Node Inspector</span>
              </div>
              <button
                type="button"
                className="node-inspector-close"
                onClick={() => setSelectedNode(null)}
                aria-label="Close Inspector"
              >
                <X size={16} />
              </button>
            </div>

            <div className="node-inspector-field">
              <span className="node-inspector-label">Node Label</span>
              <div className="node-inspector-value font-bold">{selectedNode.label}</div>
            </div>

            <div className="node-inspector-field">
              <span className="node-inspector-label">Entity Classification</span>
              <div className="node-inspector-value uppercase">{selectedNode.nodeType}</div>
            </div>

            <div className="node-inspector-field">
              <span className="node-inspector-label">State / Assessment</span>
              <div className="node-inspector-value">
                <span className={`badge badge-${selectedNode.status} uppercase`}>
                  {selectedNode.status}
                </span>
              </div>
            </div>

            <div className="node-inspector-field">
              <span className="node-inspector-label">Timeline Step Discovered</span>
              <div className="node-inspector-value">Step {selectedNode.stepDiscovered}</div>
            </div>

            {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
              <div className="node-inspector-field">
                <span className="node-inspector-label">Forensic Metadata &amp; Evidence</span>
                <pre
                  className="node-inspector-value"
                  style={{ fontSize: '11px', maxHeight: '200px', overflowY: 'auto' }}
                >
                  {JSON.stringify(selectedNode.metadata, null, 2)}
                </pre>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}
