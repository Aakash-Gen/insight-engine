# ResearchMind — Project Status & Roadmap

> **Last updated:** 2026-03-15
> **Purpose:** Track what has been built, what is broken/incomplete, and what to build next. Use this as the starting context for every new session.

---

## Current State

**Phases 1–5 + Quality Improvements are complete. The app is feature-complete and production-ready code-wise. The only remaining work is Phase 6 — Deployment.**

56 tests passing. All core features implemented and tested.

---

## What Has Been Built

### Backend — FastAPI + LangGraph (Python)

| Component | Status | Notes |
|-----------|--------|-------|
| Multi-agent graph (LangGraph) | ✅ Working | planner → researcher → critic loop → synthesizer → writer |
| LLM abstraction (`core/llm.py`) | ✅ Working | Anthropic, xAI Grok, Groq — switch via `LLM_PROVIDER` env var. Both streaming and non-streaming. |
| Streaming LLM output | ✅ Working | `stream_chat()` in `core/llm.py`. Synthesizer streams tokens via `stream_bus.push_token()` → SSE `token` events |
| Tavily web search | ✅ Working | `search_depth="advanced"`, 8 results/query, domain-diversity dedup (max 2 per domain) |
| Supabase persistence | ✅ Working | `research_sessions` table stores logs, report JSON, sources |
| pgvector RAG | ✅ Working | sentence-transformers (all-MiniLM-L6-v2, 384-dim), cosine similarity via RPC |
| Self-RAG reranking | ✅ Working | `rag/retriever.py` filters by cosine similarity ≥ 0.5 |
| JWT auth | ✅ Working | `core/auth.py` — PyJWT HS256, Bearer header + ?token= for SSE |
| Rate limiting | ✅ Working | `core/limiter.py` — 10/hour per IP on POST /research/start (closure-based, not slowapi) |
| SSE streaming | ✅ Working | asyncio.Queue bus (zero-lag) + Supabase polling fallback (1.5s). Handles log, token, complete, heartbeat events |
| Report API | ✅ Working | GET / LIST / DELETE / EXPORT (md/txt) / ASK (Q&A) |
| Research templates | ✅ Working | 7 templates at GET /templates. Competitor analysis, market research, tech deep-dive, lit review, investment thesis, product research, quick overview |
| Email notifications | ✅ Working | `core/email.py` — Resend or SMTP. No-op when unconfigured. Sends on pipeline completion. |
| Structured logging | ✅ Working | structlog JSON + stdlib bridge. All agents use `structlog.get_logger()` |
| Sentry integration | ✅ Working | Optional — activated by `SENTRY_DSN` env var |
| Retry logic | ✅ Working | tenacity on all LLM calls (3×, 2→8s backoff) and Tavily search |
| Health check | ✅ Working | `GET /health` pings Supabase, returns ok/degraded + version + environment |
| Timeout enforcement | ✅ Working | SIGALRM-based 600s hard timeout in research background task |
| CORS | ✅ Fixed | `allow_origins=["*"]`, `allow_credentials=False` (Bearer token auth) |
| Human-in-the-loop override | ✅ Working | Frontend injects guidance mid-session via POST /research/{id}/override |
| Depth-aware research | ✅ Working | Critic iteration caps: quick=1, standard=2, deep=3 |
| Provider-aware synthesis | ✅ Working | Groq: 12 results × 600 chars. Anthropic/xAI: 25 × 1500 chars |

### Frontend — React + Vite + TypeScript

| Component | Status | Notes |
|-----------|--------|-------|
| Landing page | ✅ Done | Particle animation, feature showcase, CTA |
| Login / Signup pages | ✅ Done | Supabase Auth (email/password + Google OAuth) |
| Dashboard | ✅ Done | Start research, list saved reports, templates grid |
| Research templates picker | ✅ Done | 7 template cards pre-fill topic + depth |
| ResearchSession (live view) | ✅ Done | Real-time SSE, agent cards, streaming synthesis preview, structured report |
| Citation linking | ✅ Done | `[SOURCE N]` in report text rendered as clickable superscript links to actual URLs |
| Streaming synthesis preview | ✅ Done | Tokens appear word-by-word in report panel during synthesizer run, replaced by structured sections on complete |
| Export button | ✅ Done | Downloads report as `.md` file via GET /reports/{id}/export |
| Q&A side panel | ✅ Done | Slide-in panel, asks follow-up questions via POST /reports/{id}/ask |
| ProtectedRoute | ✅ Done | Waits for `isInitialized` before redirect (fixes OAuth race) |
| useAuthStore (Zustand) | ✅ Done | Real Supabase Auth |
| useResearchStore (Zustand) | ✅ Done | Real API integration |
| Typed API client (`src/lib/api.ts`) | ✅ Done | All endpoints wired: research, reports, templates, export, Q&A, streaming tokens |
| ConfidenceGauge | ✅ Done | Recharts quality breakdown bar chart |
| AgentCard | ✅ Done | Live status, expandable content |

### Infrastructure

| Item | Status | Notes |
|------|--------|-------|
| Supabase Auth | ✅ Configured | Google OAuth redirect URL added |
| Supabase pgvector | ✅ DDL defined | Must be run manually in Supabase SQL editor (see `core/supabase_client.py`) |
| Environment config | ✅ Done | `.env.example` for backend, `.env` for frontend |
| Test suite | ✅ Done | 56 tests across auth, research routes, report routes, LLM dispatch, health |

---

## Known Remaining Issues

1. **No job queue** — Still using FastAPI `BackgroundTasks`. Fine for low traffic; Celery/arq needed at scale.
2. **Embeddings on CPU** — `sentence-transformers` loads PyTorch on every cold start. Slow on large batches or constrained hosts.
3. **No deployment config** — No Dockerfile, no CI/CD, no cloud deployment yet (Phase 6).
4. **SIGALRM timeout Unix-only** — Hard timeout gracefully no-ops on Windows; research jobs can run indefinitely on Windows hosts.

---

## Production Roadmap

### Phase 1 — Security & Auth Hardening ✅ COMPLETE (2026-03-15)

- [x] Backend JWT verification (`core/auth.py`)
- [x] Row-level ownership checks on all mutating routes
- [x] IP-based rate limiting on POST /research/start
- [x] Input sanitization (Pydantic validators)
- [x] Remove `user_id` from POST body — extracted from JWT
- [x] Frontend auth headers + SSE ?token= param

---

### Phase 2 — Reliability & Observability ✅ COMPLETE (2026-03-15)

- [x] Structured JSON logging (structlog + stdlib bridge)
- [x] Sentry integration (optional, gated on `SENTRY_DSN`)
- [x] Tenacity retry on all LLM calls and Tavily search
- [x] Deep health check with Supabase ping
- [x] SIGALRM-based hard timeout (600s default)

---

### Phase 3 — Real-time Streaming ✅ COMPLETE (2026-03-15)

- [x] asyncio.Queue bus for zero-lag SSE (replaces 1.5s Supabase polling)
- [x] Supabase polling fallback for reconnects / server restarts
- [x] Streaming LLM tokens from synthesizer → SSE `token` events → live frontend preview

---

### Phase 4 — Research Quality ✅ COMPLETE (2026-03-15)

- [x] Domain diversity scoring (max 2 results per domain)
- [x] Depth-aware critic iteration caps (quick=1, standard=2, deep=3)
- [x] Provider-aware synthesis context limits (Groq vs Anthropic/xAI)

---

### Phase 5 — Features ✅ COMPLETE (2026-03-15)

- [x] Report export (Markdown / plain text download)
- [x] Follow-up Q&A chat panel (LLM grounded in report context)
- [x] Research templates (7 types, Dashboard picker)

---

### Quality Improvements ✅ COMPLETE (2026-03-15)

- [x] Streaming LLM output — synthesizer tokens streamed word-by-word to frontend
- [x] Citation linking — `[SOURCE N]` rendered as clickable superscript links to actual URLs
- [x] Email notifications — `core/email.py`, Resend or SMTP, activated by env var

---

### Phase 6 — Deployment ⬅ NEXT

**Goal:** Ship to production.

- [ ] **Dockerize backend** — Multi-stage `Dockerfile` (build → slim runtime). `docker-compose.yml` for local dev.
- [ ] **GitHub Actions CI** — Run `pytest` on every push to main. Auto-deploy on merge.
- [ ] **Deploy backend** — Railway or Render (`railway up` / `render deploy`). Set all env vars.
- [ ] **Deploy frontend** — Vercel (`vercel --prod`). Set `VITE_API_URL` to production backend URL.
- [ ] **Supabase production project** — Separate Supabase project for prod. Run DDL from `core/supabase_client.py`.
- [ ] **Custom domain** — `api.researchmind.io` → backend, `app.researchmind.io` → frontend.
- [ ] **Environment secrets** — All secrets in Railway/Vercel dashboard. Never commit `.env`.

---

## Recommended Next Session Start

**Start Phase 6 — Deployment. Begin with the Dockerfile.**

```
1. Create researchmind-backend/Dockerfile (multi-stage):
   - Stage 1 (builder): python:3.12-slim, install all deps
   - Stage 2 (runtime): copy venv, copy app, CMD uvicorn main:app --host 0.0.0.0 --port 8000
   - .dockerignore: exclude .env, __pycache__, tests/, *.pyc

2. Create docker-compose.yml (local dev):
   - backend service (build: ./researchmind-backend, env_file: .env, ports: 8000)

3. Create .github/workflows/ci.yml:
   - trigger: push to main, PR to main
   - jobs: checkout, python 3.12, pip install -r requirements.txt, pytest

4. Deploy backend to Railway:
   - railway init → railway up
   - Set all env vars in Railway dashboard

5. Deploy frontend to Vercel:
   - vercel --prod from insight-engine/
   - Set VITE_API_URL=https://your-railway-url.railway.app

6. Create production Supabase project:
   - Run DDL from core/supabase_client.py in SQL editor
   - Update SUPABASE_URL + SUPABASE_SERVICE_KEY + SUPABASE_JWT_SECRET in Railway
```

---

## Environment Variables Reference

### Backend (`researchmind-backend/.env`)

| Variable | Required | Notes |
|----------|----------|-------|
| `LLM_PROVIDER` | Yes | `anthropic`, `xai`, or `groq` |
| `ANTHROPIC_API_KEY` | If using Anthropic | |
| `XAI_API_KEY` | If using xAI | |
| `GROQ_API_KEY` | If using Groq | |
| `TAVILY_API_KEY` | Yes | Web search |
| `SUPABASE_URL` | Yes | From Supabase dashboard |
| `SUPABASE_SERVICE_KEY` | Yes | Service role key (not anon key) |
| `SUPABASE_JWT_SECRET` | Yes | JWT Settings → JWT Secret |
| `SENTRY_DSN` | No | Enables Sentry error tracking |
| `RESEND_API_KEY` | No | Enables email notifications via Resend |
| `SMTP_HOST` | No | Alternative to Resend for email |
| `ENVIRONMENT` | No | `development` / `production` |
| `RESEARCH_TIMEOUT_SECONDS` | No | Default 600 |

### Frontend (`insight-engine/.env`)

| Variable | Required | Notes |
|----------|----------|-------|
| `VITE_API_URL` | Yes | Backend URL, e.g. `http://localhost:8000` |
| `VITE_SUPABASE_URL` | Yes | Same Supabase URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Anon/public key (not service key) |

---

## Running the Project Locally

```bash
# Backend
cd researchmind-backend
pip install -r requirements.txt
cp .env.example .env   # fill in required keys
uvicorn main:app --reload --port 8000

# Frontend
cd insight-engine
npm install
npm run dev
# → http://localhost:5173
```

### Supabase DDL (run once in SQL editor)
See `researchmind-backend/core/supabase_client.py` comments for the full DDL.
Tables required: `research_sessions`, `research_chunks`
Extension required: `pgvector`
RPC required: `match_research_chunks`

---

## Key File Map

```
insight-engine/
├── src/
│   ├── App.tsx                    # Routes + auth init
│   ├── lib/
│   │   ├── api.ts                 # Typed API client (all backend calls + streaming)
│   │   └── supabase.ts            # Supabase JS client
│   ├── store/
│   │   ├── useAuthStore.ts        # Auth state (Supabase Auth)
│   │   └── useResearchStore.ts    # Research state + API calls
│   ├── pages/
│   │   ├── Dashboard.tsx          # Start research, list reports, templates picker
│   │   ├── ResearchSession.tsx    # Live streaming, citation linking, Q&A panel, export
│   │   ├── Login.tsx / Signup.tsx
│   │   └── Landing.tsx
│   └── components/
│       ├── ProtectedRoute.tsx
│       ├── AgentCard.tsx
│       └── ConfidenceGauge.tsx
└── researchmind-backend/
    ├── main.py                    # FastAPI app + CORS + Sentry + lifespan
    ├── core/
    │   ├── auth.py                # JWT verification (Bearer + ?token=)
    │   ├── config.py              # All settings (pydantic-settings)
    │   ├── email.py               # Email notifications (Resend / SMTP)
    │   ├── limiter.py             # IP rate limiter (closure-based)
    │   ├── llm.py                 # LLM abstraction: chat() + stream_chat()
    │   ├── logging_config.py      # structlog JSON + stdlib bridge
    │   ├── stream_bus.py          # asyncio.Queue SSE bus + token streaming
    │   └── supabase_client.py     # DB client + DDL reference
    ├── agents/
    │   ├── graph.py               # LangGraph StateGraph
    │   ├── state.py               # ResearchState TypedDict
    │   ├── planner.py             # Decomposes topic into plan
    │   ├── researcher.py          # Tavily search + domain diversity
    │   ├── critic.py              # Evaluates gaps, depth-aware iteration caps
    │   ├── synthesizer.py         # Merges findings + streaming token output
    │   └── writer.py              # Formats final JSON report
    ├── api/
    │   ├── schemas.py             # Pydantic request/response models
    │   └── routes/
    │       ├── research.py        # /research/* (start, stream SSE, override)
    │       ├── reports.py         # /reports/* (get, list, delete, export, Q&A)
    │       └── templates.py       # /templates/* (7 research templates)
    ├── rag/
    │   ├── embeddings.py          # sentence-transformers
    │   ├── vectorstore.py         # Supabase pgvector upsert/search
    │   └── retriever.py          # Self-RAG reranking
    └── tests/
        ├── conftest.py            # Fixtures, JWT minting, Supabase mocks
        ├── test_auth.py           # 10 JWT verification tests
        ├── test_research_routes.py # 14 research endpoint tests
        ├── test_report_routes.py  # 22 report endpoint tests (incl. export + Q&A)
        ├── test_llm.py            # 5 LLM dispatch tests
        └── test_health.py         # 3 health check tests
```
