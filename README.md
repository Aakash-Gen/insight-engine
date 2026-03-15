# ResearchMind

An AI-powered research platform that uses a multi-agent pipeline to produce structured, cited research reports on any topic.

---

## What it does

Enter a research topic, choose a depth (Quick / Standard / Deep Dive), and ResearchMind:

1. **Plans** — decomposes your topic into targeted sub-questions
2. **Researches** — searches the web via Tavily, collecting and deduplicating sources
3. **Critiques** — evaluates gaps and triggers additional research rounds if needed
4. **Synthesizes** — merges findings into a coherent narrative with inline citations
5. **Writes** — formats a structured report with sections, key findings, and confidence scores

Results stream to the UI in real time as each agent works.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion |
| State | Zustand |
| Backend | Python 3.12, FastAPI, LangGraph 0.2+ |
| AI | Groq (llama-3.3-70b) · Anthropic Claude · xAI Grok — switchable via env var |
| Search | Tavily API (advanced depth, domain diversity dedup) |
| Database | Supabase (PostgreSQL + pgvector for RAG) |
| Auth | Supabase Auth (email/password + Google OAuth) |
| Streaming | Server-Sent Events (asyncio.Queue bus + Supabase polling fallback) |
| Deploy | Vercel (frontend) · Render (backend) |

---

## Running locally

### Prerequisites
- Node.js 18+
- Python 3.11+
- A [Supabase](https://supabase.com) project
- A [Tavily](https://tavily.com) API key
- At least one LLM key: [Groq](https://console.groq.com) (free), [Anthropic](https://console.anthropic.com), or [xAI](https://console.x.ai)

### Quickstart

```bash
git clone https://github.com/Aakash-Gen/insight-engine.git
cd insight-engine

# Configure backend
cp researchmind-backend/.env.example researchmind-backend/.env
# Fill in your API keys in researchmind-backend/.env

# Configure frontend — create .env with:
# VITE_API_URL=http://localhost:8000
# VITE_SUPABASE_URL=your-supabase-url
# VITE_SUPABASE_ANON_KEY=your-anon-key

# Start everything
./run.sh
```

Frontend → http://localhost:5173  
Backend → http://localhost:8000  
API docs → http://localhost:8000/docs

### Supabase setup (one-time)

Run the DDL from `researchmind-backend/core/supabase_client.py` in your Supabase SQL editor to create the `research_sessions` and `research_chunks` tables, enable pgvector, and create the `match_research_chunks` RPC function.

---

## Environment variables

### Backend (`researchmind-backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | Yes | `groq`, `anthropic`, or `xai` |
| `GROQ_API_KEY` | If using Groq | |
| `ANTHROPIC_API_KEY` | If using Anthropic | |
| `XAI_API_KEY` | If using xAI | |
| `TAVILY_API_KEY` | Yes | Web search |
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | Service role key (not anon key) |
| `SUPABASE_JWT_SECRET` | Yes | From Supabase → Settings → API |
| `SENTRY_DSN` | No | Enables error tracking |
| `RESEND_API_KEY` | No | Email notifications on completion |

### Frontend (`.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | Yes | Backend URL, e.g. `http://localhost:8000` |
| `VITE_SUPABASE_URL` | Yes | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anon/publishable key |

---

## Deployment

### Backend → Render (free tier)

1. New Web Service → connect this repo
2. Root Directory: `researchmind-backend` · Runtime: Docker
3. Add all backend env vars
4. Set `CORS_ORIGINS=https://your-app.vercel.app`

### Frontend → Vercel (free tier)

```bash
vercel --prod
# Set VITE_API_URL to your Render service URL when prompted
```

---

## Features

- **Real-time streaming** — agent steps and synthesis tokens stream live to the UI
- **Depth control** — Quick (~500 words), Standard (~1200 words), Deep Dive (~2500 words)
- **Citation linking** — `[SOURCE N]` rendered as clickable superscript links
- **Sources panel** — slide-in drawer listing all consulted sources with titles and domains
- **Export** — download report as Markdown or PDF
- **Q&A** — ask follow-up questions grounded in the report context
- **Research templates** — 7 pre-built templates (market research, competitor analysis, etc.)
- **Human-in-the-loop** — redirect research mid-session with a guidance message
- **Confidence scoring** — algorithmic score from source diversity, relevance, and depth
