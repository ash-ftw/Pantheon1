# Accessibility Statement for Pantheon

Pantheon is committed to ensuring digital accessibility for people with disabilities. We continually strive to improve the user experience for everyone and apply relevant accessibility standards to our user interfaces, attack visualizations, and documentation.

---

## 🎯 Conformance Status

We aim to adhere to the **[Web Content Accessibility Guidelines (WCAG) 2.1 Level AA](https://www.w3.org/TR/WCAG21/)** standards across our web application frontend and documentation.

Key accessibility principles implemented in Pantheon:
- **Perceivable**: High-contrast dark and light theme tokens, text resizability without loss of functionality, semantic HTML elements, and ARIA labels on interactive elements.
- **Operable**: Full keyboard accessibility for primary workflows, visible focus indicators, skip navigation links, and screen reader-friendly navigation structures.
- **Understandable**: Consistent UI layouts, clear validation messages, predictable interactive components, and descriptive error dialogs.
- **Robust**: Valid HTML5 markup engineered to work seamlessly with modern assistive technologies.

---

## 🖥️ Supported Environments & Assistive Technologies

Pantheon's frontend is designed and tested for compatibility with:
- **Browsers**: Modern evergreen browsers (Chrome, Firefox, Safari, Microsoft Edge).
- **Screen Readers**: NVDA, JAWS (Windows), VoiceOver (macOS/iOS), and Orca (Linux).
- **Input Methods**: Standard keyboards, screen magnifiers, and voice control software.

---

## ⚠️ Known Limitations & Alternative Solutions

While we strive for comprehensive accessibility, certain complex data visualizations and interactive graphs may present challenges:

1. **Interactive Attack Graphs (XYFlow / React Flow)**:
   - *Limitation*: Complex node-edge attack topology graphs rely heavily on 2D visual layout and spatial dragging.
   - *Alternative*: Tabular and textual route disclosures, security finding summaries, and vulnerability lists provide keyboard-navigable, screen-reader-accessible representations of the same underlying data.
2. **Terminal / Streaming Log Outputs**:
   - *Limitation*: High-frequency real-time attack stream logs can flood screen reader live regions.
   - *Alternative*: Live regions are throttled, and users can pause stream feeds or download full plaintext execution logs.

We are actively working on improving the accessible alternative views for node topology diagrams.

---

## 📣 Feedback & Reporting Accessibility Barriers

We welcome your feedback on the accessibility of Pantheon. If you encounter accessibility barriers or have suggestions for improvement, please let us know:

- **Email**: [ashishjacob810@gmail.com](mailto:ashishjacob810@gmail.com)
- **GitHub Issues**: Open an issue using the [Accessibility barrier tag](https://github.com/ash-ftw/Pantheon1/issues/new)
- **What to include**:
  - The URL, component, or workflow where you encountered the barrier.
  - A description of the issue and what assistive technology or device you were using.
  - Expected behavior vs. what occurred.

We aim to acknowledge accessibility reports within **3 business days** and prioritize remediation in our product roadmap.
