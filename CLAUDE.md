# Agent Instructions — Read Before Every Action

Read in this order, every session:

1. `~/daily-builder/prompts/rules/session_protocol.md`
2. `~/daily-builder/prompts/rules/quality_bar.md`
3. `~/daily-builder/prompts/rules/code_rules.md`
4. `state.md` in this directory
5. This file

---

# Project: Keystroke Sentinel

**Tagline:** Trains on how you type, detects when someone else is.

**Domain:** Cybersecurity and Offensive/Defensive Security Tools

**Tech stack:** Python, scikit-learn, FastAPI, WebSockets, TypeScript, React, D3.js, Vite, Tailwind CSS, Docker Compose

**Problem:** Password-based sessions are binary gates — once stolen, an attacker owns the session with no further checks. Keystroke Sentinel trains a per-user Random Forest classifier on keystroke dynamics (dwell time, inter-key flight time, digraph latency matrices, error rate) and continuously scores live typing against that behavioral baseline, triggering a re-auth challenge the instant the session's biometric signature drifts beyond a calibrated threshold.

**Why it stands out:** Implements real biometric feature engineering — timing statistics, digraph co-occurrence matrices, live decision boundary scoring — with a continuous ML inference loop that demonstrates session-integrity security beyond anything a password manager can offer, backed by a UI that makes the invisible signal visible

---

# Core features

    • Browser-side telemetry layer captures per-keystroke dwell time, flight time, digraph/trigraph latency matrices, WPM, and error rates — batched into burst payloads and streamed over WebSocket to the inference backend in real time
    • Per-user enrollment pipeline: Random Forest classifier trained on 5+ minutes of baseline typing with cross-validated feature importance output, confusion matrix on held-out enrollment data, and stored model artifacts per identity
    • Live behavioral waveform dashboard: scrolling D3 timeline of anomaly score per typing burst, per-feature distribution overlay comparing enrolled baseline vs. live session, and a configurable deviation threshold that triggers a visible re-auth challenge with session freeze

---

# Full Implementation Plan

Read `~/daily-builder/prompts/new_project.md` for the complete instructions.
Start at STEP 3 — the idea is already chosen and approved. Details are above.
Do not regenerate ideas.

Estimated sessions: 3
