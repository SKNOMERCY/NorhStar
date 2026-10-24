# NORTHSTAR — AI Agent Long-Horizon Goal Tracking System
> **Cognition 2026 Problem Statement 5: Long-Horizon Goal Tracking**  
> *A persistent goal-representation layer that survives context decay, detects semantic drift, enforces invariant guardrails, and distinguishes legitimate goal evolution from agent distraction.*

---

## 🧭 Executive Overview

Multi-session and multi-day autonomous agent runs frequently suffer from the **"lost in the middle"** context decay problem:
- As sub-tasks accumulate across sessions, agents drift away from the overarching objective.
- Agents get trapped in tangential rabbit holes (e.g., writing custom games, endless cosmetic refactoring, or installing unvetted utilities).
- Traditional systems lack a mechanism to separate immutable / versioned **North Star Invariants** from transient working memory.

**Northstar** solves this by introducing:
1. **Persistent Goal-Representation Layer**: Survives context truncation, system restarts, and multi-session boundaries.
2. **Multi-Factor Drift Detector**: Real-time scoring using semantic distance, negative constraint inspection, and horizon decay penalties.
3. **Automated Circuit Breaker & Re-Grounding Engine**: Intercepts high-drift actions, halts divergence, and dynamically injects synthesized grounding context.
4. **Goal Evolution vs. Drift Classifier**: Distinguishes between legitimate requirements evolution (e.g., API deprecation, compliance changes) and unwarranted agent drift.
5. **Side-by-Side Multi-Session Benchmark Lab**: Deterministic head-to-head simulations demonstrating **Baseline Agent (Without Northstar)** vs. **Guarded Agent (With Northstar)**.

---

## ⚡ Quick Start (1-Click Run)

### Requirements
- **Python 3.10+** (Python 3.12 verified)
- **Node.js 18+** & **npm** (Node v26 verified)

### Running on Windows
Simply double-click:
```bash
start_northstar.bat
```
Or start manually:

#### Terminal 1 — Backend (FastAPI):
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Health: http://127.0.0.1:8000/api/health
- Swagger Docs: http://127.0.0.1:8000/docs

#### Terminal 2 — Frontend (React + Vite):
```bash
cd frontend
npm ci
npm run preview -- --host 127.0.0.1 --port 5173
```
- Mission Control UI: http://localhost:5173

This checkout includes the prebuilt frontend in `frontend/dist`. The original `frontend/src` source files are missing, so `npm run dev` and `npm run build` cannot run until that source is restored. The checked-in `dist` bundle is served by Vite Preview.

---

## 📐 Architecture & Modules

```
c:\Users\jiyal\OneDrive\Desktop\pro\
├── backend/
│   ├── app/
│   │   ├── config.py                  # Thresholds, weights & paths
│   │   ├── database.py                # SQLite schema (zero external ORM dependencies)
│   │   ├── models/                    # Pydantic data schemas
│   │   │   ├── goal.py                # Goal, Milestone & Invariant models
│   │   │   ├── session.py             # Session, Step & Drift Audit models
│   │   │   └── evolution.py           # Evolution RFC & Versioning models
│   │   ├── services/
│   │   │   ├── drift_detector.py      # Multi-factor drift scoring algorithm
│   │   │   ├── regrounding.py         # Grounding prompt injection & recovery
│   │   │   ├── evolution_service.py   # Legitimate evolution vs drift classifier
│   │   │   ├── simulation_service.py  # 3 multi-session benchmark suites
│   │   │   ├── ai_provider.py         # OpenAI / Ollama / Heuristic provider adapter
│   │   │   ├── tool_guardrails.py     # Pre-execution guardrail enforcement
│   │   │   └── agent_orchestrator.py  # Controlled execution loop with drift interception
│   │   ├── routers/                   # REST API endpoints
│   │   │   ├── goals.py               # Invariant definition & milestones
│   │   │   ├── sessions.py            # Step submission & audit interception
│   │   │   ├── drift.py               # Drift statistics & audit logs
│   │   │   ├── evolutions.py          # RFC proposals & decisions
│   │   │   ├── simulations.py         # Side-by-side benchmark runner
│   │   │   └── orchestrator.py        # Live AI execution endpoints
│   │   └── main.py                    # FastAPI application & CORS & orchestrator
│   ├── test_backend_sync.py           # Verified backend test suite (11 tests)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx             # Celestial navigation bar & coordinate header
│   │   │   ├── NorthStarOverviewCard.tsx # Fixed North Star immutable objective anchor
│   │   │   ├── CelestialMap.tsx       # Interactive SVG star chart & milestone topology
│   │   │   ├── InstrumentPanel.tsx    # SVG compass rose & sextant drift telemetry
│   │   │   ├── VoyageLogbook.tsx      # Step audit log & course submission form
│   │   │   ├── LiveRunPanel.tsx       # Live AI execution console & guardrail status
│   │   │   ├── ComparisonMatrix.tsx   # Side-by-side benchmark scorecards
│   │   │   └── EvolutionModal.tsx     # RFC proposal modal (Star Chart Revision)
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx      # Executive Mission Control
│   │   │   ├── SimulationsPage.tsx    # Multi-session comparative lab
│   │   │   ├── GoalManagerPage.tsx    # Goal & Invariant editor
│   │   │   └── EvolutionLogPage.tsx   # Evolution lineage & audit records
│   │   ├── api/client.ts              # Backend API connector
│   │   ├── types/index.ts             # Shared TypeScript types
│   │   ├── App.tsx
│   │   └── index.css                  # Modern glassmorphism & Tailwind styles
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── start_northstar.bat                # 1-click launch script
└── README.md
```

---

## 🎯 Drift Scoring Formula

$$\text{Drift Score } D = w_{\text{sem}} \cdot S_{\text{sem}} + w_{\text{con}} \cdot S_{\text{con}} + w_{\text{hor}} \cdot S_{\text{hor}}$$

Where:
- $S_{\text{sem}}$: Inverted cosine similarity between agent action embedding and the North Star Root Intent + Active Milestone.
- $S_{\text{con}}$: Constraint breach penalty (anti-goals and negative constraints like building games, unvetted dependencies, etc.).
- $S_{\text{hor}}$: Horizon decay penalty (steps accumulated without advancing milestone state).
- $w_{\text{sem}} = 0.45$, $w_{\text{con}} = 0.40$, $w_{\text{hor}} = 0.15$.

### Drift Tiers:
| Drift Score $D$ | Tier | Behavior |
| :--- | :--- | :--- |
| **0.00 – 0.25** | `NORMAL` | Aligned with North Star. Execution proceeds without interruption. |
| **0.25 – 0.50** | `WARNING` | Mild divergence. Northstar injects grounding reminder into context. |
| **0.50 – 0.75** | `INTERVENE` | **Circuit Breaker Fires**. Action halted; agent steered back to milestone. |
| **0.75 – 1.00** | `CRITICAL` | Severe contradiction / Anti-Goal breach. Action aborted; RFC required. |

---

## 🧪 Benchmark Scenarios (Side-by-Side Lab)

1. **Enterprise E-Commerce Cloud Migration** (DevOps & Full-Stack):
   - *Baseline Agent*: Diverges at Session 2 into terminal ASCII art and arcade mini-game; achieves **41.8%** alignment, 0 milestones finished.
   - *Northstar Agent*: Circuit breaker halts mini-game; applies Stripe API evolution RFC; completes all 4 milestones (**96.2%** alignment).

2. **Financial Portfolio Risk & Compliance Audit** (Quant Finance):
   - *Baseline Agent*: Drifts into scraping celebrity social media and meme coins (**38.5%** alignment).
   - *Northstar Agent*: Re-grounds to stress-testing milestone; produces SEC Rule 15c3-1 Capital Compliance report (**97.4%** alignment).

3. **Drug Discovery Meta-Analysis** (Bioinformatics):
   - *Baseline Agent*: Hallucinates non-existent molecules (**45.0%** alignment).
   - *Northstar Agent*: Distinguishes new clinical binding data as legitimate evolution, validates candidate molecules (**98.1%** alignment).

---

## 🛡️ Workspace & Security Isolation

- Built strictly inside the project root `c:\Users\jiyal\OneDrive\Desktop\pro`.
- Zero credentials or tokens hardcoded.
- Uses native SQLite persistence without requiring external database setups.

---

## 🤖 AI Provider Configuration

Northstar supports three execution modes selected automatically based on environment variables:

| Priority | Provider | Configuration |
| :--- | :--- | :--- |
| **1st** | OpenAI API (Live) | Set `OPENAI_API_KEY` |
| **2nd** | Ollama Local (Live) | Set `OLLAMA_ENABLED=true` |
| **3rd** | Heuristic Model (Built-in) | Default — no config required |

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# OpenAI Integration
OPENAI_API_KEY=sk-...               # Your OpenAI API key
OPENAI_BASE_URL=https://api.openai.com/v1   # Or Azure/proxy endpoint
OPENAI_MODEL=gpt-4o-mini            # Model name

# Ollama Local Integration
OLLAMA_ENABLED=false                # Set true to use local Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b               # Model loaded in Ollama
```

### Running the Backend with API Key

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-key-here"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Windows CMD
set OPENAI_API_KEY=sk-your-key-here
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The **Live Run Console** on the dashboard shows the active provider and model, and allows you to execute guardrailed agent steps against the real AI model.

---

## 🔒 Pre-Execution Guardrails

The Agent Orchestrator enforces mandatory pre-execution checks on every proposed tool call:

- **Allowlisted tools only**: `read_file`, `write_file`, `list_files`, `validate_test`, `check_milestone_deliverable`
- **Path traversal blocking**: Rejects any `../` or absolute-path attempts
- **Anti-goal matching**: Flags tool calls that match any goal's anti-goal patterns
- **Workspace containment**: All file operations must stay within the project root
- **Circuit breaker**: Fires on drift score ≥ 0.50 (`INTERVENE`) or anti-goal breach

All guardrail violations are persisted in SQLite as drift audit records and surfaced in the Evolution Log page.
