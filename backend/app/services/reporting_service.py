"""Reporting Engine Service — PRD Module 12 (Phase 13).

Generates auditable, exportable security test reports from completed simulation runs.
Markdown is the single source of truth; PDF and CSV exports are strictly derived from it.
Includes automatic Before/After posture comparison against prior runs on the same application.
"""

from __future__ import annotations

import asyncio
import csv
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Set matplotlib backend to headless Agg before importing pyplot
import matplotlib
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.logging import get_logger
from app.models import App, DefenceRecommendation, Finding, Report, TestRun

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ReportLab imports for pure Python vector PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus import (
    Image as RLImage,
)

logger = get_logger(__name__)

SEVERITY_COLORS = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#ca8a04",
    "low": "#2563eb",
    "info": "#4b5563",
}

SEVERITY_WEIGHTS = {
    "critical": 10.0,
    "high": 5.0,
    "medium": 2.0,
    "low": 1.0,
    "info": 0.2,
}


class ReportingService:
    """Reporting engine managing markdown generation, PDF/CSV exports, and baseline comparisons."""

    def __init__(self) -> None:
        self.reports_dir = Path("data/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _get_org_report_dir(self, org_id: uuid.UUID) -> Path:
        target = self.reports_dir / str(org_id)
        target.mkdir(parents=True, exist_ok=True)
        return target

    async def compute_before_after_comparison(
        self,
        db: AsyncSession,
        current_run: TestRun,
        current_findings: list[Finding],
    ) -> dict[str, Any]:
        """Compute before/after posture delta against the most recent prior completed run on this app."""
        stmt = (
            select(TestRun)
            .where(
                TestRun.app_id == current_run.app_id,
                TestRun.id != current_run.id,
                TestRun.status.in_(["completed", "stopped"]),
            )
            .order_by(desc(TestRun.created_at))
            .limit(1)
            .options(selectinload(TestRun.findings))
        )
        result = await db.execute(stmt)
        prior_run = result.scalar_one_or_none()

        if not prior_run:
            current_score = sum(
                SEVERITY_WEIGHTS.get(f.severity.lower(), 1.0) for f in current_findings
            )
            return {
                "prior_run_id": None,
                "prior_run_date": None,
                "prior_findings_count": 0,
                "current_findings_count": len(current_findings),
                "resolved_findings": [],
                "new_findings": [
                    {
                        "title": f.title,
                        "severity": f.severity,
                        "category": f.category,
                        "cwe_id": f.cwe_id,
                    }
                    for f in current_findings
                ],
                "posture_delta": "initial_run",
                "posture_score_delta": 0.0,
                "current_posture_score": round(current_score, 1),
                "summary": "Initial baseline run. No prior execution recorded for this application.",
            }

        prior_findings = prior_run.findings or []
        prior_titles = {f.title for f in prior_findings}
        current_titles = {f.title for f in current_findings}

        resolved = [
            {
                "title": f.title,
                "severity": f.severity,
                "category": f.category,
                "cwe_id": f.cwe_id,
            }
            for f in prior_findings
            if f.title not in current_titles
        ]

        new_findings = [
            {
                "title": f.title,
                "severity": f.severity,
                "category": f.category,
                "cwe_id": f.cwe_id,
            }
            for f in current_findings
            if f.title not in prior_titles
        ]

        prior_score = sum(SEVERITY_WEIGHTS.get(f.severity.lower(), 1.0) for f in prior_findings)
        current_score = sum(SEVERITY_WEIGHTS.get(f.severity.lower(), 1.0) for f in current_findings)
        score_delta = round(prior_score - current_score, 1)

        if score_delta > 0:
            posture_delta = "improved"
            summary = f"Security posture improved. Vulnerability score decreased by {score_delta} points ({len(resolved)} findings resolved)."
        elif score_delta < 0:
            posture_delta = "degraded"
            summary = f"Security posture degraded. Vulnerability score increased by {abs(score_delta)} points ({len(new_findings)} new findings detected)."
        else:
            posture_delta = "unchanged"
            summary = "Security posture unchanged compared to previous execution baseline."

        return {
            "prior_run_id": str(prior_run.id),
            "prior_run_date": prior_run.created_at.strftime("%Y-%m-%d %H:%M UTC")
            if prior_run.created_at
            else None,
            "prior_findings_count": len(prior_findings),
            "current_findings_count": len(current_findings),
            "resolved_findings": resolved,
            "new_findings": new_findings,
            "posture_delta": posture_delta,
            "posture_score_delta": score_delta,
            "prior_posture_score": round(prior_score, 1),
            "current_posture_score": round(current_score, 1),
            "summary": summary,
        }

    def generate_charts(
        self,
        severity_counts: dict[str, int],
        output_dir: Path,
        report_id: uuid.UUID,
    ) -> str | None:
        """Generate a headless PNG chart for severity breakdown and save locally."""
        try:
            levels = ["critical", "high", "medium", "low", "info"]
            counts = [severity_counts.get(lvl, 0) for lvl in levels]
            palette = [SEVERITY_COLORS[lvl] for lvl in levels]

            # Only plot if there's at least one finding, else draw clean empty state
            fig, ax = plt.subplots(figsize=(6, 2.5), dpi=150)
            fig.patch.set_facecolor("#0b1120")
            ax.set_facecolor("#0f172a")

            y_pos = range(len(levels))
            bars = ax.barh(y_pos, counts, color=palette, height=0.55, edgecolor="#1e293b")

            ax.set_yticks(y_pos)
            ax.set_yticklabels(
                [lvl.upper() for lvl in levels], color="#94a3b8", fontsize=9, fontweight="bold"
            )
            ax.invert_yaxis()
            ax.tick_params(axis="x", colors="#94a3b8", labelsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#334155")
            ax.spines["bottom"].set_color("#334155")
            ax.xaxis.grid(True, linestyle="--", alpha=0.3, color="#334155")

            # Add count labels on ends of bars
            for bar, count in zip(bars, counts, strict=False):
                if count > 0:
                    ax.text(
                        bar.get_width() + 0.1,
                        bar.get_y() + bar.get_height() / 2,
                        str(count),
                        va="center",
                        ha="left",
                        color="#f8fafc",
                        fontsize=9,
                        fontweight="bold",
                    )

            plt.title(
                "Findings by Severity Level",
                color="#f8fafc",
                fontsize=11,
                fontweight="bold",
                pad=12,
            )
            plt.tight_layout()

            chart_path = output_dir / f"{report_id}_severity_chart.png"
            fig.savefig(chart_path, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            return str(chart_path)
        except Exception as e:
            logger.warning("Failed to render chart via matplotlib: %s", e)
            return None

    def build_markdown_report(
        self,
        report_id: uuid.UUID,
        title: str,
        test_run: TestRun,
        app: App | None,
        findings: list[Finding],
        recommendations: list[DefenceRecommendation],
        comparison: dict[str, Any],
        metrics: dict[str, Any],
        chart_path: str | None = None,
    ) -> str:
        """Construct the authoritative Markdown representation of the security report."""
        app_name = app.name if app else "Unknown Application"
        run_date = (
            test_run.created_at.strftime("%Y-%m-%d %H:%M UTC") if test_run.created_at else "N/A"
        )
        duration = ""
        if test_run.started_at and test_run.completed_at:
            delta = test_run.completed_at - test_run.started_at
            duration = f"{int(delta.total_seconds())}s"
        else:
            duration = "N/A"

        sev_counts = {
            "critical": sum(1 for f in findings if f.severity.lower() == "critical"),
            "high": sum(1 for f in findings if f.severity.lower() == "high"),
            "medium": sum(1 for f in findings if f.severity.lower() == "medium"),
            "low": sum(1 for f in findings if f.severity.lower() == "low"),
            "info": sum(1 for f in findings if f.severity.lower() == "info"),
        }

        # Header & Metadata
        md = f"""# {title}

**Target Application:** {app_name}
**Scenario:** {test_run.scenario_name} (`{test_run.scenario_category}`)
**Test Run ID:** `{test_run.id}`
**Report ID:** `{report_id}`
**Execution Timestamp:** {run_date}
**Duration:** {duration}
**Overall Status:** `{test_run.status.upper()}`

---

## 1. Executive Summary

This report documents the security posture and resilience evaluation conducted by **Pantheon Security Platform** on **{app_name}**. The simulation assessed resistance against targeted attack scenarios and chaos conditions.

### Severity Breakdown
- **CRITICAL:** {sev_counts["critical"]}
- **HIGH:** {sev_counts["high"]}
- **MEDIUM:** {sev_counts["medium"]}
- **LOW:** {sev_counts["low"]}
- **INFO:** {sev_counts["info"]}
- **Total Findings:** {len(findings)}

**Posture Assessment:** {comparison.get("summary", "Evaluation complete.")}

---

## 2. Before / After Posture Comparison

| Metric | Prior Baseline | Current Run | Delta |
| :--- | :--- | :--- | :--- |
| **Run Reference** | `{comparison.get("prior_run_id") or "N/A"}` | `{test_run.id}` | — |
| **Execution Date** | {comparison.get("prior_run_date") or "N/A"} | {run_date} | — |
| **Total Findings** | {comparison.get("prior_findings_count", 0)} | {len(findings)} | {len(findings) - comparison.get("prior_findings_count", 0):+d} |
| **Risk Score** | {comparison.get("prior_posture_score", 0.0)} | {comparison.get("current_posture_score", 0.0)} | {comparison.get("posture_score_delta", 0.0):+.1f} ({comparison.get("posture_delta", "baseline").upper()}) |

"""
        # Resolved & New Findings Subsections
        resolved = comparison.get("resolved_findings", [])
        if resolved:
            md += "### Resolved Findings (Fixed Since Baseline)\n"
            for r in resolved:
                md += f"- **[{r.get('severity', '').upper()}]** {r.get('title')} ({r.get('category')})\n"
            md += "\n"

        new_f = comparison.get("new_findings", [])
        if new_f and comparison.get("prior_run_id"):
            md += "### New Findings (Introduced or Newly Detected)\n"
            for nf in new_f:
                md += f"- **[{nf.get('severity', '').upper()}]** {nf.get('title')} ({nf.get('category')})\n"
            md += "\n"

        md += f"""---

## 3. Performance & Reliability Metrics

| Metric | Measured Value |
| :--- | :--- |
| **Total HTTP Requests** | {metrics.get("total_requests", 0)} |
| **Failed Requests** | {metrics.get("failed_requests", 0)} |
| **Error Rate** | {metrics.get("error_rate_pct", 0.0):.2f}% |
| **Avg Latency** | {metrics.get("avg_latency_ms", 0.0):.2f} ms |
| **P95 Latency** | {metrics.get("p95_latency_ms", 0.0):.2f} ms |
| **Total Execution Steps** | {test_run.total_steps} |

---

## 4. Security Findings & Vulnerability Matrix

"""
        if not findings:
            md += "_No security findings were identified during this simulation run._\n\n"
        else:
            md += "| # | Severity | Category | Title | CWE / OWASP | Status |\n"
            md += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            for idx, f in enumerate(findings, start=1):
                cwe_owasp = f"{f.cwe_id or ''} {f.owasp_category or ''}".strip() or "N/A"
                md += f"| {idx} | **{f.severity.upper()}** | {f.category} | {f.title} | {cwe_owasp} | `{f.status}` |\n"
            md += "\n"

            md += "### Detailed Finding Profiles\n\n"
            for idx, f in enumerate(findings, start=1):
                md += f"#### {idx}. {f.title} (`{f.severity.upper()}`)\n"
                md += f"- **Category:** {f.category}\n"
                if f.cwe_id:
                    md += f"- **CWE:** {f.cwe_id}\n"
                if f.owasp_category:
                    md += f"- **OWASP:** {f.owasp_category}\n"
                md += f"- **Description:** {f.description}\n"
                md += f"- **Remediation Guidance:** {f.remediation_guidance}\n\n"

        md += """---

## 5. Defensive Mitigations & Recommendations

"""
        if not recommendations:
            md += "_No active defense recommendations recorded._\n\n"
        else:
            md += "| Mitigation Title | Category | Type | Mechanics | Status |\n"
            md += "| :--- | :--- | :--- | :--- | :--- |\n"
            for r in recommendations:
                mech = "1-Click Auto" if r.mechanically_applicable else "Code Guidance"
                md += (
                    f"| {r.title} | {r.category} | {r.mitigation_type} | {mech} | `{r.status}` |\n"
                )
            md += "\n"

        md += f"""---

## 6. Audit & Platform Verification

- **Generated by:** Pantheon Security & Chaos Platform v1.0
- **Organization ID:** `{test_run.org_id}`
- **Report Generation Time:** {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **Verification Hash:** `{uuid.uuid5(uuid.NAMESPACE_DNS, str(report_id))}`
"""
        return md

    def generate_csv(self, findings: list[Finding], output_path: Path) -> None:
        """Write structured findings CSV file."""
        fieldnames = [
            "id",
            "severity",
            "category",
            "title",
            "cwe_id",
            "owasp_category",
            "status",
            "remediation_guidance",
            "created_at",
        ]
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for finding in findings:
                writer.writerow(
                    {
                        "id": str(finding.id),
                        "severity": finding.severity,
                        "category": finding.category,
                        "title": finding.title,
                        "cwe_id": finding.cwe_id or "",
                        "owasp_category": finding.owasp_category or "",
                        "status": finding.status,
                        "remediation_guidance": finding.remediation_guidance,
                        "created_at": finding.created_at.isoformat() if finding.created_at else "",
                    }
                )

    def generate_pdf(
        self,
        title: str,
        test_run: TestRun,
        app: App | None,
        findings: list[Finding],
        recommendations: list[DefenceRecommendation],
        comparison: dict[str, Any],
        metrics: dict[str, Any],
        chart_path: str | None,
        output_path: Path,
    ) -> None:
        """Generate clean, professional vector PDF using pure-Python ReportLab."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            fontName="Helvetica-Bold",
            spaceAfter=6,
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
            fontName="Helvetica",
            spaceAfter=12,
        )

        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica-Bold",
            spaceBefore=12,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
            fontName="Helvetica",
            spaceAfter=6,
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica",
        )

        story = []

        # 1. Header Banner
        app_name = app.name if app else "Unknown Application"
        run_date = (
            test_run.created_at.strftime("%Y-%m-%d %H:%M UTC") if test_run.created_at else "N/A"
        )

        story.append(Paragraph(title, title_style))
        story.append(
            Paragraph(
                f"<b>Application:</b> {app_name} | <b>Scenario:</b> {test_run.scenario_name} | <b>Status:</b> {test_run.status.upper()} | <b>Date:</b> {run_date}",
                subtitle_style,
            )
        )
        story.append(
            HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10)
        )

        # 2. Executive Summary Box
        story.append(Paragraph("1. Executive Summary", h2_style))
        summary_text = comparison.get("summary", "Security and resilience evaluation completed.")
        story.append(Paragraph(f"<b>Posture Assessment:</b> {summary_text}", body_style))

        # Severity count pills
        sev_counts = {
            "critical": sum(1 for f in findings if f.severity.lower() == "critical"),
            "high": sum(1 for f in findings if f.severity.lower() == "high"),
            "medium": sum(1 for f in findings if f.severity.lower() == "medium"),
            "low": sum(1 for f in findings if f.severity.lower() == "low"),
            "info": sum(1 for f in findings if f.severity.lower() == "info"),
        }

        sev_data = [
            [
                Paragraph("<b>CRITICAL</b>", table_header_style),
                Paragraph("<b>HIGH</b>", table_header_style),
                Paragraph("<b>MEDIUM</b>", table_header_style),
                Paragraph("<b>LOW</b>", table_header_style),
                Paragraph("<b>INFO</b>", table_header_style),
                Paragraph("<b>TOTAL</b>", table_header_style),
            ],
            [
                Paragraph(f"<b>{sev_counts['critical']}</b>", table_cell_style),
                Paragraph(f"<b>{sev_counts['high']}</b>", table_cell_style),
                Paragraph(f"<b>{sev_counts['medium']}</b>", table_cell_style),
                Paragraph(f"<b>{sev_counts['low']}</b>", table_cell_style),
                Paragraph(f"<b>{sev_counts['info']}</b>", table_cell_style),
                Paragraph(f"<b>{len(findings)}</b>", table_cell_style),
            ],
        ]
        t_sev = Table(sev_data, colWidths=[80, 80, 80, 80, 80, 80])
        t_sev.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#dc2626")),
                    ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#ea580c")),
                    ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#ca8a04")),
                    ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#2563eb")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_sev)
        story.append(Spacer(1, 8))

        # If chart exists, embed image
        if chart_path and os.path.exists(chart_path):
            try:
                img = RLImage(chart_path, width=4.5 * inch, height=1.8 * inch)
                story.append(img)
                story.append(Spacer(1, 8))
            except Exception as ex:
                logger.warning("Could not include chart in PDF: %s", ex)

        # 3. Before / After Comparison
        story.append(Paragraph("2. Before / After Posture Comparison", h2_style))
        delta_str = f"{comparison.get('posture_score_delta', 0.0):+.1f} ({comparison.get('posture_delta', 'baseline').upper()})"
        comp_data = [
            [
                Paragraph("<b>Metric</b>", table_header_style),
                Paragraph("<b>Prior Baseline</b>", table_header_style),
                Paragraph("<b>Current Run</b>", table_header_style),
                Paragraph("<b>Delta / Trend</b>", table_header_style),
            ],
            [
                Paragraph("Run Reference", table_cell_style),
                Paragraph(str(comparison.get("prior_run_id") or "N/A")[:12], table_cell_style),
                Paragraph(str(test_run.id)[:12], table_cell_style),
                Paragraph("—", table_cell_style),
            ],
            [
                Paragraph("Execution Date", table_cell_style),
                Paragraph(str(comparison.get("prior_run_date") or "N/A"), table_cell_style),
                Paragraph(run_date, table_cell_style),
                Paragraph("—", table_cell_style),
            ],
            [
                Paragraph("Total Findings", table_cell_style),
                Paragraph(str(comparison.get("prior_findings_count", 0)), table_cell_style),
                Paragraph(str(len(findings)), table_cell_style),
                Paragraph(
                    f"{len(findings) - comparison.get('prior_findings_count', 0):+d}",
                    table_cell_style,
                ),
            ],
            [
                Paragraph("Risk Score", table_cell_style),
                Paragraph(str(comparison.get("prior_posture_score", 0.0)), table_cell_style),
                Paragraph(str(comparison.get("current_posture_score", 0.0)), table_cell_style),
                Paragraph(delta_str, table_cell_style),
            ],
        ]
        t_comp = Table(comp_data, colWidths=[130, 120, 120, 130])
        t_comp.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#f8fafc"), colors.white],
                    ),
                ]
            )
        )
        story.append(t_comp)
        story.append(Spacer(1, 10))

        # 4. Performance Metrics Table
        story.append(Paragraph("3. Performance & Reliability Metrics", h2_style))
        perf_data = [
            [
                Paragraph("<b>Metric</b>", table_header_style),
                Paragraph("<b>Value</b>", table_header_style),
                Paragraph("<b>Metric</b>", table_header_style),
                Paragraph("<b>Value</b>", table_header_style),
            ],
            [
                Paragraph("Total Requests", table_cell_style),
                Paragraph(str(metrics.get("total_requests", 0)), table_cell_style),
                Paragraph("Avg Latency", table_cell_style),
                Paragraph(f"{metrics.get('avg_latency_ms', 0.0):.1f} ms", table_cell_style),
            ],
            [
                Paragraph("Failed Requests", table_cell_style),
                Paragraph(str(metrics.get("failed_requests", 0)), table_cell_style),
                Paragraph("P95 Latency", table_cell_style),
                Paragraph(f"{metrics.get('p95_latency_ms', 0.0):.1f} ms", table_cell_style),
            ],
            [
                Paragraph("Error Rate", table_cell_style),
                Paragraph(f"{metrics.get('error_rate_pct', 0.0):.2f}%", table_cell_style),
                Paragraph("Total Steps", table_cell_style),
                Paragraph(str(test_run.total_steps), table_cell_style),
            ],
        ]
        t_perf = Table(perf_data, colWidths=[120, 130, 120, 130])
        t_perf.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(t_perf)
        story.append(Spacer(1, 10))

        # 5. Security Findings Table
        story.append(Paragraph("4. Security Findings Matrix", h2_style))
        if not findings:
            story.append(
                Paragraph("<i>No security findings identified during simulation.</i>", body_style)
            )
        else:
            findings_data = [
                [
                    Paragraph("<b>#</b>", table_header_style),
                    Paragraph("<b>Severity</b>", table_header_style),
                    Paragraph("<b>Category</b>", table_header_style),
                    Paragraph("<b>Title</b>", table_header_style),
                    Paragraph("<b>CWE / OWASP</b>", table_header_style),
                ]
            ]
            for idx, f in enumerate(findings, start=1):
                cwe_str = f"{f.cwe_id or ''} {f.owasp_category or ''}".strip() or "—"
                sev_color = SEVERITY_COLORS.get(f.severity.lower(), "#4b5563")
                findings_data.append(
                    [
                        Paragraph(str(idx), table_cell_style),
                        Paragraph(
                            f"<font color='{sev_color}'><b>{f.severity.upper()}</b></font>",
                            table_cell_style,
                        ),
                        Paragraph(f.category, table_cell_style),
                        Paragraph(f.title, table_cell_style),
                        Paragraph(cwe_str, table_cell_style),
                    ]
                )
            t_findings = Table(findings_data, colWidths=[24, 70, 96, 210, 100])
            t_findings.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.HexColor("#f8fafc"), colors.white],
                        ),
                    ]
                )
            )
            story.append(t_findings)

        story.append(Spacer(1, 10))

        # 6. Defensive Recommendations
        story.append(Paragraph("5. Defensive Mitigations", h2_style))
        if not recommendations:
            story.append(Paragraph("<i>No defence recommendations recorded.</i>", body_style))
        else:
            recs_data = [
                [
                    Paragraph("<b>Title</b>", table_header_style),
                    Paragraph("<b>Category</b>", table_header_style),
                    Paragraph("<b>Type</b>", table_header_style),
                    Paragraph("<b>Status</b>", table_header_style),
                ]
            ]
            for r in recommendations:
                recs_data.append(
                    [
                        Paragraph(r.title, table_cell_style),
                        Paragraph(r.category, table_cell_style),
                        Paragraph(r.mitigation_type, table_cell_style),
                        Paragraph(r.status.upper(), table_cell_style),
                    ]
                )
            t_recs = Table(recs_data, colWidths=[200, 110, 100, 90])
            t_recs.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.HexColor("#f8fafc"), colors.white],
                        ),
                    ]
                )
            )
            story.append(t_recs)

        story.append(Spacer(1, 12))
        story.append(
            HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#94a3b8"), spaceAfter=6)
        )
        story.append(
            Paragraph(
                f"<font color='#64748b'>Pantheon Security Platform v1.0 • Generated on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')} • Org: {test_run.org_id}</font>",
                body_style,
            )
        )

        doc.build(story)

    async def generate_report(
        self,
        db: AsyncSession,
        test_run_id: uuid.UUID,
        org_id: uuid.UUID,
        title: str | None = None,
    ) -> Report:
        """Main orchestrator: creates authoritative report from test run and exports PDF and CSV."""
        # 1. Fetch Test Run
        stmt = (
            select(TestRun)
            .where(TestRun.id == test_run_id, TestRun.org_id == org_id)
            .options(
                selectinload(TestRun.findings),
                selectinload(TestRun.recommendations),
                selectinload(TestRun.app),
            )
        )
        result = await db.execute(stmt)
        test_run = result.scalar_one_or_none()
        if not test_run:
            raise ValueError(f"Test run {test_run_id} not found for org {org_id}")

        findings = test_run.findings or []
        recommendations = test_run.recommendations or []
        app = test_run.app

        # 2. Before / After Comparison
        comparison = await self.compute_before_after_comparison(db, test_run, findings)

        # 3. Metrics Aggregation
        raw_metrics = test_run.metrics or {}
        total_reqs = raw_metrics.get("total_requests", 0)
        failed_reqs = raw_metrics.get("failed_requests", 0)
        err_rate = (failed_reqs / total_reqs * 100.0) if total_reqs > 0 else 0.0

        metrics_summary = {
            "total_requests": total_reqs,
            "failed_requests": failed_reqs,
            "error_rate_pct": round(err_rate, 2),
            "avg_latency_ms": raw_metrics.get("avg_latency_ms", 0.0),
            "p95_latency_ms": raw_metrics.get("p95_latency_ms", 0.0),
            "total_steps": test_run.total_steps,
            "total_findings": len(findings),
            "severity_counts": {
                "critical": sum(1 for f in findings if f.severity.lower() == "critical"),
                "high": sum(1 for f in findings if f.severity.lower() == "high"),
                "medium": sum(1 for f in findings if f.severity.lower() == "medium"),
                "low": sum(1 for f in findings if f.severity.lower() == "low"),
                "info": sum(1 for f in findings if f.severity.lower() == "info"),
            },
        }

        # 4. Directories & IDs
        report_id = uuid.uuid4()
        org_dir = self._get_org_report_dir(org_id)
        default_title = f"Security Evaluation Report: {test_run.scenario_name} ({test_run.created_at.strftime('%Y-%m-%d')})"
        resolved_title = title.strip() if title and title.strip() else default_title

        # 5. Chart generation
        chart_path = self.generate_charts(metrics_summary["severity_counts"], org_dir, report_id)

        # 6. Authoritative Markdown document
        markdown_content = self.build_markdown_report(
            report_id=report_id,
            title=resolved_title,
            test_run=test_run,
            app=app,
            findings=findings,
            recommendations=recommendations,
            comparison=comparison,
            metrics=metrics_summary,
            chart_path=chart_path,
        )

        # Save Markdown file
        md_file_path = org_dir / f"{report_id}.md"
        await asyncio.to_thread(md_file_path.write_text, markdown_content, encoding="utf-8")

        # 7. CSV Export
        csv_file_path = org_dir / f"{report_id}.csv"
        self.generate_csv(findings, csv_file_path)

        # 8. PDF Export
        pdf_file_path = org_dir / f"{report_id}.pdf"
        self.generate_pdf(
            title=resolved_title,
            test_run=test_run,
            app=app,
            findings=findings,
            recommendations=recommendations,
            comparison=comparison,
            metrics=metrics_summary,
            chart_path=chart_path,
            output_path=pdf_file_path,
        )

        executive_summary = (
            f"{comparison.get('summary', 'Security evaluation complete.')} "
            f"Evaluated {len(findings)} findings ({metrics_summary['severity_counts']['critical']} critical, "
            f"{metrics_summary['severity_counts']['high']} high). Error rate: {metrics_summary['error_rate_pct']}%."
        )

        # 9. Store in DB
        report = Report(
            id=report_id,
            org_id=org_id,
            test_run_id=test_run.id,
            app_id=test_run.app_id,
            title=resolved_title,
            executive_summary=executive_summary,
            markdown_content=markdown_content,
            pdf_path=str(pdf_file_path),
            csv_path=str(csv_file_path),
            before_after_comparison=comparison,
            metrics_summary=metrics_summary,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    async def get_report(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
        org_id: uuid.UUID,
    ) -> Report | None:
        """Fetch a single report by ID scoped to the organization."""
        stmt = select(Report).where(Report.id == report_id, Report.org_id == org_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_reports(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        test_run_id: uuid.UUID | None = None,
        app_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[Report]:
        """List reports scoped to organization with optional filtering."""
        stmt = select(Report).where(Report.org_id == org_id)
        if test_run_id:
            stmt = stmt.where(Report.test_run_id == test_run_id)
        if app_id:
            stmt = stmt.where(Report.app_id == app_id)
        stmt = stmt.order_by(desc(Report.created_at)).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def preview_report(
        self,
        db: AsyncSession,
        test_run_id: uuid.UUID,
        org_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Generate an in-memory preview of the report before persistence."""
        stmt = (
            select(TestRun)
            .where(TestRun.id == test_run_id, TestRun.org_id == org_id)
            .options(
                selectinload(TestRun.findings),
                selectinload(TestRun.recommendations),
                selectinload(TestRun.app),
            )
        )
        result = await db.execute(stmt)
        test_run = result.scalar_one_or_none()
        if not test_run:
            raise ValueError(f"Test run {test_run_id} not found for org {org_id}")

        findings = test_run.findings or []
        comparison = await self.compute_before_after_comparison(db, test_run, findings)
        raw_metrics = test_run.metrics or {}
        total_reqs = raw_metrics.get("total_requests", 0)
        failed_reqs = raw_metrics.get("failed_requests", 0)
        err_rate = (failed_reqs / total_reqs * 100.0) if total_reqs > 0 else 0.0

        metrics_summary = {
            "total_requests": total_reqs,
            "failed_requests": failed_reqs,
            "error_rate_pct": round(err_rate, 2),
            "avg_latency_ms": raw_metrics.get("avg_latency_ms", 0.0),
            "p95_latency_ms": raw_metrics.get("p95_latency_ms", 0.0),
            "total_steps": test_run.total_steps,
            "total_findings": len(findings),
            "severity_counts": {
                "critical": sum(1 for f in findings if f.severity.lower() == "critical"),
                "high": sum(1 for f in findings if f.severity.lower() == "high"),
                "medium": sum(1 for f in findings if f.severity.lower() == "medium"),
                "low": sum(1 for f in findings if f.severity.lower() == "low"),
                "info": sum(1 for f in findings if f.severity.lower() == "info"),
            },
        }

        mock_id = uuid.uuid4()
        md = self.build_markdown_report(
            report_id=mock_id,
            title=f"Security Evaluation Preview: {test_run.scenario_name}",
            test_run=test_run,
            app=test_run.app,
            findings=findings,
            recommendations=test_run.recommendations or [],
            comparison=comparison,
            metrics=metrics_summary,
        )

        return {
            "test_run_id": str(test_run.id),
            "scenario_name": test_run.scenario_name,
            "markdown_preview": md,
            "before_after_comparison": comparison,
            "metrics_summary": metrics_summary,
        }

    async def get_export_bytes(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
        org_id: uuid.UUID,
        format_type: str,
    ) -> tuple[bytes, str, str]:
        """Retrieve raw export file bytes, media type, and download filename."""
        report = await self.get_report(db, report_id, org_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        format_clean = format_type.lower().strip()
        safe_title = (
            "".join(c for c in report.title if c.isalnum() or c in ("-", "_")).rstrip() or "report"
        )

        def _read_export_bytes(file_path: str | None, missing_msg: str) -> bytes:
            if not file_path or not os.path.exists(file_path):
                raise ValueError(missing_msg)
            with open(file_path, "rb") as f:
                return f.read()

        if format_clean == "pdf":
            file_bytes = await asyncio.to_thread(
                _read_export_bytes, report.pdf_path, "PDF file not found for this report"
            )
            return file_bytes, "application/pdf", f"{safe_title}.pdf"

        elif format_clean == "csv":
            file_bytes = await asyncio.to_thread(
                _read_export_bytes, report.csv_path, "CSV file not found for this report"
            )
            return file_bytes, "text/csv", f"{safe_title}.csv"

        elif format_clean in ["md", "markdown"]:
            return report.markdown_content.encode("utf-8"), "text/markdown", f"{safe_title}.md"

        else:
            raise ValueError(f"Unsupported export format: {format_type}. Allowed: pdf, csv, md")


reporting_service = ReportingService()
