/**
 * Types for the Pantheon Scroll-Driven Narrative Landing Page
 */

export interface ChapterDef {
  id: string;
  numeral: string; // e.g., "00", "01"
  label: string; // e.g., "HERO", "MANIFESTO"
  title: string;
}

export const CHAPTERS: ChapterDef[] = [
  { id: 'chapter-00', numeral: '00', label: 'HERO', title: 'Chapter 00 — The Adversary Within' },
  { id: 'chapter-01', numeral: '01', label: 'MANIFESTO', title: 'Chapter 01 — Assumed Breach' },
  {
    id: 'chapter-02',
    numeral: '02',
    label: 'PLATFORM',
    title: 'Chapter 02 — Built To Be Attacked',
  },
  { id: 'chapter-03', numeral: '03', label: 'STACK', title: 'Chapter 03 — By The Numbers' },
  { id: 'chapter-04', numeral: '04', label: 'ENGINE', title: 'Chapter 04 — The Four Movements' },
  { id: 'chapter-05', numeral: '05', label: 'SCENARIOS', title: 'Chapter 05 — Attack Horizons' },
  { id: 'chapter-06', numeral: '06', label: 'TRUST', title: 'Chapter 06 — Signal & Proof' },
  { id: 'chapter-07', numeral: '07', label: 'CTA', title: 'Chapter 07 — The Safe Breach' },
];

export interface EnginePhase {
  id: string;
  numeral: string;
  title: string;
  tagline: string;
  description: string;
  badge: string;
  telemetry: string;
}

export interface FindingItem {
  id: string;
  cve: string;
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  category: 'Kubernetes' | 'Auth & RBAC' | 'API Surface' | 'Supply Chain';
  cvss: number;
  timeDetected: string;
  blastRadius: string;
}
