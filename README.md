# Keystroke Sentinel

**Trains on how you type, detects when someone else is.**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178c6?logo=typescript)](https://typescriptlang.org)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4-f7931e?logo=scikitlearn)](https://scikit-learn.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## What it is

Password-based sessions are binary gates — once a password is stolen, an attacker owns the session with no further friction. Keystroke Sentinel adds a continuous behavioral layer: it trains a per-user Random Forest classifier on keystroke dynamics (dwell time, inter-key flight intervals, digraph latency matrices, WPM, error rates) and scores every typing burst in real time against that baseline. When the behavioral fingerprint drifts beyond a calibrated threshold, the session is flagged and a re-authentication challenge fires.

This is not a novelty demo. The feature engineering is real: the system builds digraph co-occurrence matrices per enrollment session, selects the top-50 most stable key pairs as the canonical feature set, and trains a classifier that distinguishes genuine typing rhythm from both synthetic impostors and organic drift. The ML inference loop runs at sub-100ms latency over a persistent WebSocket.

---

## Live workflow

A full end-to-end run: enrollment → classifier training → live behavioral monitoring → anomaly detection → re-auth challenge.

**1. Enrollment screen** — enter a user identity to begin capturing your keystroke baseline.

![01 enrollment empty state](docs/screenshots/01_enrollment_empty.png)

**2. User ID entered** — identity is validated before any API calls are made.

![02 user ID entered](docs/screenshots/02_enrollment_user_id_entered.png)

**3. Typing phase begins** — keystroke events are captured in real time (dwell, flight, digraph latencies) and batched into 2.5s bursts.

![03 typing phase](docs/screenshots/03_enrollment_typing_phase.png)

**4. Keystrokes accumulating** — the progress bar tracks keystroke count toward the 300-keystroke training threshold; WPM updates live.

![04 typing progress](docs/screenshots/04_enrollment_typing_progress.png)

**5. Ready to train** — 300+ keystrokes collected; the Train classifier button activates.

![05 ready to train](docs/screenshots/05_enrollment_ready_to_train.png)

**6. Training complete** — Random Forest trained with 5-fold cross-validation (95.8% accuracy shown). Feature importance chart reveals which timing statistics drive classification.

![06 training complete with CV scores and feature importances](docs/screenshots/06_enrollment_training_complete.png)

**7. Live monitoring dashboard** — WebSocket connected; behavioral waveform, feature snapshot, session score ring, and threshold slider are live.

![07 dashboard connected](docs/screenshots/07_dashboard_connected.png)

**8. Genuine typing scored** — burst arrives, classifier scores 26% anomaly (well below 0.65 threshold), status shows NOMINAL.

![08 live scoring nominal](docs/screenshots/08_dashboard_live_scoring.png)

**9. Waveform history building** — multiple bursts scored; the D3 timeline shows the behavioral signal across the session.

![09 waveform history](docs/screenshots/09_dashboard_waveform_history.png)

**10. Anomaly detected — re-auth challenge fires** — robotic uniform-cadence typing scores 95.4% anomaly, crossing the threshold. Session freezes and the re-auth modal demands identity verification.

![10 re-auth challenge 95.4% anomaly](docs/screenshots/10_dashboard_reauth_challenge.png)

---

## Architecture

```
Browser (React + D3)
│
│  Per-keystroke telemetry: dwell, flight, digraph latency
│  Batched into bursts every 2.5s → sent over WebSocket
│
WebSocket /ws/{user_id}/{session_id}
│
FastAPI Backend (Python)
├── Feature Extractor
│   ├── Dwell times (press→release per key)
│   ├── Flight times (release→press between keys)
│   ├── Digraph latency matrix (top 50 key pairs)
│   ├── WPM, error rate
│   └── Statistical moments (mean, std, median, p25, p75)
│
├── Enrollment Pipeline
│   ├── Buffer bursts until 300+ keystrokes
│   ├── Build canonical digraph set from frequency
│   └── Train Random Forest (200 trees, 5-fold CV)
│
├── Inference Loop
│   ├── Score each burst: P(legitimate) → anomaly = 1 − P
│   └── Broadcast score + feature snapshot over WebSocket
│
└── SQLite (enrollment metadata) + joblib (model artifacts)
```

**Data flow:**

1. User types in the browser → keystroke events captured via `keydown`/`keyup` listeners with `performance.now()` timestamps
2. Every 2.5 seconds, buffered events are packaged into a `KeystrokeBurst` and sent over WebSocket
3. Backend extracts a fixed-length feature vector (13 statistical features + 50 digraph latencies = 63 features)
4. The enrolled Random Forest scores the vector and returns an anomaly score in [0, 1]
5. The score is rendered in the live D3 waveform and compared against the configurable threshold
6. Score > threshold → re-auth challenge fires, session is frozen

---

## Installation

### Option A: Local dev (recommended for development)

**Requirements:** Python 3.11, Node.js 20+

```bash
git clone https://github.com/rayancheca/keystroke-sentinel.git
cd keystroke-sentinel

# Backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Option B: Docker Compose

```bash
docker compose up --build
```

Open `http://localhost`.

---

## Usage

### 1. Enroll

Enter a user ID and type naturally for ~2-3 minutes until the progress bar reaches 100% (300 keystrokes). Use the "Next prompt" button to get fresh text. Click **Train classifier** when ready.

The enrollment screen shows:
- A progress bar tracking total keystrokes collected
- Live WPM counter
- Cross-validated accuracy score after training
- Feature importance bar chart showing which keystroke features drive classification

### 2. Monitor

After enrollment, the live dashboard opens:

- **Behavioral waveform**: D3 scrolling timeline of anomaly score per typing burst (teal = safe, amber = anomalous)
- **Score ring**: Current anomaly score as a radial fill
- **Feature snapshot**: Bar chart of live biometric features per burst
- **Threshold slider**: Tune sensitivity (0.30 = very sensitive, 0.90 = lenient)

### 3. Re-auth challenge

When the anomaly score exceeds the threshold, a modal freezes the session and requests password re-verification.

---

## Technical deep-dive

### Why Random Forest over a neural net?

Behavioral biometrics with small enrollment datasets (300–2000 keystrokes) produce ~15–100 feature vectors per user. Neural networks need orders of magnitude more data. Random Forest handles this regime naturally, produces calibrated probabilities via `predict_proba`, and outputs feature importances that make the system interpretable. Cross-validated accuracy on 5-fold splits provides an honest estimate of generalization.

### The impostor synthesis problem

One-class classifiers (Isolation Forest, One-Class SVM) tend to underperform on keystroke data because the genuine class is tightly clustered while the "everything else" space is unbounded. Instead, we synthesize synthetic impostors during training: we perturb genuine feature vectors by sampling noise with 1.5–3× the genuine population's standard deviation. This gives the RF a balanced binary classification problem and empirically outperforms pure one-class approaches on held-out tests.

### Digraph selection is non-obvious

Raw keystroke data is high-dimensional: a full digraph matrix has 26²+ = 700+ potential key pairs. But most pairs appear rarely in any given session. We compute the frequency of each digraph across all enrollment bursts and select the top-50 most stable pairs as the canonical feature set. Unknown digraphs in live bursts are filled with the session mean. This keeps the feature vector fixed at training time and prevents the curse of dimensionality.

### WebSocket burst protocol

Rather than streaming individual keystrokes (which would create thousands of round-trips per minute), telemetry is batched into bursts. Each burst contains all key events in a 2.5-second window, WPM, and error counts. The backend extracts features from the burst atomically — this is important because digraph latencies are computed from the sequence of events in order, not from individual events.

---

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest --cov=app --cov-report=term-missing
```

56 tests, 80%+ coverage across the feature extractor, ML classifier, trainer, storage, session management, and API endpoints.

---

## Project structure

```
keystroke-sentinel/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes (enrollment REST + WebSocket)
│   │   ├── core/         # Config, structured logging
│   │   ├── features/     # Keystroke feature extraction
│   │   ├── ml/           # Random Forest classifier, trainer, model storage
│   │   └── models/       # Pydantic schemas, SQLAlchemy models, session store
│   └── tests/            # 56 unit + integration tests
├── frontend/
│   └── src/
│       ├── components/   # Enrollment UI, live dashboard, D3 charts, re-auth
│       ├── hooks/        # useKeystrokeCapture, useAnomalyStream
│       ├── lib/          # API client, TypeScript types
│       └── styles/       # Design tokens, global styles
└── docker-compose.yml
```

---

## License

MIT
