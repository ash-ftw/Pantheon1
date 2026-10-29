# Security Policy

The Pantheon security and engineering team takes security vulnerabilities seriously. We appreciate the responsible disclosure of security issues and are committed to addressing valid reports promptly.

---

## 🛡️ Supported Versions

Only the latest release and the current active development branch (`main`) receive official security patches and updates.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| < 1.0   | :x:                |

---

## 🚨 Reporting a Vulnerability

**Please do NOT file public GitHub issues for security vulnerabilities.**

If you discover a security vulnerability in Pantheon or its dependencies, please report it privately:

1. **Email Disclosure**: Send a detailed report to **[ashishjacob810@gmail.com](mailto:ashishjacob810@gmail.com)**.
2. **Subject Line**: Use `[SECURITY REPORT] Pantheon - Brief description`.
3. **Report Details**:
   - Detailed description of the vulnerability.
   - Proof-of-concept (PoC) code or exact steps to reproduce.
   - Affected components (backend, frontend sandbox, container daemon interface, reverse proxy, etc.).
   - Potential impact and severity assessment (CVSS rating if available).
   - Any suggested mitigations or patches.

### Response Timelines

- **Initial Acknowledgement**: Within **48 hours**.
- **Triage & Severity Confirmation**: Within **5 business days**.
- **Fix & Public Advisory**: We work with reporters to coordinate an appropriate patch release and disclosure timeline (typically 30 to 90 days depending on complexity).

---

## 🔒 Sandboxing & Scope Clarification

Pantheon is a cyber range platform specifically designed to execute controlled security scenarios, fuzzing, and containerized target applications.

- Vulnerabilities inside an *onboarded target application* are within user-controlled scope.
- Security vulnerabilities in Pantheon's **host isolation, container escape barriers, tenant separation, reverse proxy sanitization, authentication, or control plane APIs** are in-scope and treated with high priority.
