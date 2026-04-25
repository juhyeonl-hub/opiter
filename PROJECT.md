# Opiter — Project

## Vision

Build a **free, open-source, privacy-respecting document editor** that eventually replaces the fragmented landscape of proprietary editors (Adobe Acrobat, Microsoft Office, Hancom Office) for common document workflows — starting with PDF, expanding to DOCX and HWP.

## Philosophy

### 1. 100% Free
No ads. No subscriptions. No "premium" feature gates. If code-signing certificates or infrastructure require funding, it will come from voluntary donations — never paywalls.

### 2. Open Source
AGPL-3.0 licensed (driven by upstream PyMuPDF and pyhwp dependencies). All source on GitHub. Anyone can audit, fork, modify, and redistribute under the same license.

### 3. Privacy-First
All file processing happens locally. No telemetry, no cloud uploads, no accounts. Your documents never leave your machine unless you explicitly share them.

### 4. Cross-Platform
Single codebase supporting Windows, macOS, and Linux via Qt for Python. No platform-specific forks.

## Scope

### What Opiter IS
- A desktop application for viewing, editing, and annotating documents
- A user-facing tool — not a library, not a server

### What Opiter is NOT (Non-Goals)
- **NOT a cloud service** — no remote processing, no accounts
- **NOT a DRM-circumvention tool** — encrypted/protected PDFs require their original password; no bypass features
- **NOT a clone** of Adobe Acrobat, Hancom, or Microsoft Office — no reverse engineering, no trademark infringement. All implementation must be based on public format specifications (ISO 32000 for PDF, etc.) and open-source libraries
- **NOT an AI-writing platform** — focus is on format handling, not content generation

## Stages

| Stage | Scope | Status |
|-------|-------|--------|
| MVP Prototype | Phase 1~3: PDF viewer + page ops + annotations | ✅ Done |
| Advanced PDF | Phase 4: image conversion, compression, watermark, metadata | ✅ Done |
| Multi-format | Phase 5: DOCX/HWP viewers + cross-format export | ✅ Done |
| Distribution (v0.1) | Linux PyInstaller build, GitHub release | **🚧 In progress** (current) |
| DOCX editor | Phase 6: rich-text DOCX editing | 📋 Planned |
| Cross-platform builds | Win/Mac PyInstaller, code signing | 📋 Post v0.1 |

See [FEATURES.md](./FEATURES.md) for phase-level feature details and [PROJECT_BRIEF.md](./PROJECT_BRIEF.md) for the current iteration's working brief.

## Governance

This is a single-maintainer project in early stage. Contribution model, release cadence, and decision process will be formalized once the prototype stabilizes.

## Sustainability

Project costs (domain, code-signing certificates, infrastructure) will be covered through **voluntary donations**. Development labor is volunteer.

## Legal & Ethical Constraints

These rules are non-negotiable and enforced at code-review time:

1. **No reverse engineering** of Adobe Acrobat, Hancom Office, Microsoft Office, or any other commercial software. All format handling must derive from public specifications and OSS libraries.
2. **No trademark infringement**. Do not use names like "Adobe", "Acrobat", "한글", "Office", "Word", or close variants in code, docs, or marketing.
3. **No DRM-circumvention features**. We will not implement password-bypass, copy-protection removal, or similar.
4. **License compatibility**. All dependencies must be compatible with AGPL-3.0 distribution. Adding a more-restrictive or incompatible dependency requires explicit review.
