"""Image Vulnerability Scanner — PRD Module 4 Item 7.

Invokes Trivy 0.56+ against built container images before deployment.
Results are informational and non-blocking per PRD.
Gracefully degrades when Trivy CLI is not installed.
"""

import json
import subprocess
from typing import Any

from app.logging import get_logger

logger = get_logger(__name__)


class ScanResult:
    """Structured scan result with severity counts."""

    def __init__(
        self,
        critical: int = 0,
        high: int = 0,
        medium: int = 0,
        low: int = 0,
        unknown: int = 0,
        findings: list[dict[str, Any]] | None = None,
        scan_available: bool = True,
        error: str | None = None,
    ) -> None:
        self.critical = critical
        self.high = high
        self.medium = medium
        self.low = low
        self.unknown = unknown
        self.findings = findings or []
        self.scan_available = scan_available
        self.error = error

    @property
    def total(self) -> int:
        return self.critical + self.high + self.medium + self.low + self.unknown

    def summary_line(self) -> str:
        """One-line summary for build logs."""
        if not self.scan_available:
            return f"Scan skipped: {self.error or 'Trivy not available'}"
        return (
            f"Scan complete: {self.critical} Critical, {self.high} High, "
            f"{self.medium} Medium, {self.low} Low vulnerabilities detected."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "unknown": self.unknown,
            "total": self.total,
            "scan_available": self.scan_available,
            "error": self.error,
            "findings": self.findings[:50],  # Cap at 50 for storage
        }


class ImageScanner:
    """Trivy-based container image vulnerability scanner.

    Non-blocking per PRD — scan results are surfaced as informational,
    never prevent deployment. Gracefully handles missing Trivy CLI.
    """

    def __init__(self) -> None:
        self._trivy_available: bool | None = None

    def _check_trivy(self) -> bool:
        """Check if Trivy CLI is installed and accessible."""
        if self._trivy_available is not None:
            return self._trivy_available

        try:
            result = subprocess.run(
                ["trivy", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._trivy_available = result.returncode == 0
            if self._trivy_available:
                version = result.stdout.strip().split("\n")[0]
                logger.info("trivy_available", version=version)
            else:
                logger.warning("trivy_check_failed", stderr=result.stderr[:200])
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._trivy_available = False
            logger.warning("trivy_not_installed")

        return self._trivy_available

    def scan_image(
        self,
        image_tag: str,
        log_callback: Any = None,
    ) -> ScanResult:
        """Scan a container image for vulnerabilities using Trivy.

        Args:
            image_tag: Full image tag to scan (e.g. localhost:5000/org-xxx/app-foo:v1).
            log_callback: Optional callable(str) for streaming scan output.

        Returns:
            ScanResult with severity counts and individual findings.
        """

        def _log(msg: str) -> None:
            if log_callback:
                log_callback(msg)

        if not self._check_trivy():
            _log("Trivy CLI not found. Skipping vulnerability scan.")
            _log(
                "Install Trivy: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
            )
            return ScanResult(
                scan_available=False,
                error="Trivy CLI not installed. Install with: choco install trivy (Windows) "
                "or brew install trivy (macOS).",
            )

        _log(f"Scanning image: {image_tag}")

        try:
            # Run Trivy in JSON output mode for structured parsing
            result = subprocess.run(  # noqa: S603
                [
                    "trivy",
                    "image",
                    "--format",
                    "json",
                    "--severity",
                    "CRITICAL,HIGH,MEDIUM,LOW",
                    "--no-progress",
                    "--timeout",
                    "5m",
                    image_tag,
                ],
                capture_output=True,
                text=True,
                timeout=600,  # 10 min hard timeout
            )

            if result.returncode != 0 and not result.stdout:
                _log(f"Trivy scan warning: {result.stderr[:300]}")
                return ScanResult(
                    scan_available=True,
                    error=f"Trivy exited with code {result.returncode}: {result.stderr[:200]}",
                )

            # Parse JSON output
            scan_data = json.loads(result.stdout)
            return self._parse_trivy_results(scan_data, _log)

        except json.JSONDecodeError as e:
            _log(f"Trivy output parse error: {e!s}")
            return ScanResult(scan_available=True, error=f"Failed to parse Trivy output: {e!s}")

        except subprocess.TimeoutExpired:
            _log("Trivy scan timed out after 10 minutes.")
            return ScanResult(scan_available=True, error="Scan timed out after 10 minutes.")

        except Exception as e:
            _log(f"Trivy scan error: {e!s}")
            return ScanResult(scan_available=True, error=str(e))

    def _parse_trivy_results(
        self,
        scan_data: dict[str, Any],
        log_callback: Any = None,
    ) -> ScanResult:
        """Parse Trivy JSON output into a structured ScanResult."""

        def _log(msg: str) -> None:
            if log_callback:
                log_callback(msg)

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        findings: list[dict[str, Any]] = []

        # Trivy JSON format: {"Results": [{"Vulnerabilities": [...]}]}
        results = scan_data.get("Results", [])
        for result_block in results:
            vulns = result_block.get("Vulnerabilities") or []
            target = result_block.get("Target", "unknown")

            for vuln in vulns:
                severity = vuln.get("Severity", "UNKNOWN").upper()
                if severity in severity_counts:
                    severity_counts[severity] += 1
                else:
                    severity_counts["UNKNOWN"] += 1

                findings.append(
                    {
                        "id": vuln.get("VulnerabilityID", ""),
                        "severity": severity,
                        "package": vuln.get("PkgName", ""),
                        "installed_version": vuln.get("InstalledVersion", ""),
                        "fixed_version": vuln.get("FixedVersion", ""),
                        "title": vuln.get("Title", ""),
                        "target": target,
                    }
                )

        scan_result = ScanResult(
            critical=severity_counts["CRITICAL"],
            high=severity_counts["HIGH"],
            medium=severity_counts["MEDIUM"],
            low=severity_counts["LOW"],
            unknown=severity_counts["UNKNOWN"],
            findings=findings,
            scan_available=True,
        )

        _log(scan_result.summary_line())

        # Log top critical/high findings
        for f in findings[:5]:
            if f["severity"] in ("CRITICAL", "HIGH"):
                _log(
                    f"  [{f['severity']}] {f['id']}: {f['package']} "
                    f"{f['installed_version']} → {f.get('fixed_version', 'no fix')}"
                )

        return scan_result


# Global singleton
image_scanner = ImageScanner()
