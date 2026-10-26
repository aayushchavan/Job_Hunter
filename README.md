# AI Job Hunter 🤖 — Autonomous Job Discovery & Auto-Apply Bot

An end-to-end, full-stack AI-powered job application system. Finds jobs across multiple sources, semantically scores matches against candidate resumes, prepares AI-generated cover letters & tailored ATS question answers, and manages an interactive application pipeline.

---

## ⚡ Quick Start (Single Command)

Start both the **FastAPI Backend** and the **Next.js Frontend** simultaneously:

### Windows (Batch)
```cmd
start.bat
```

### PowerShell
```powershell
.\start.ps1
```

### Cross-Platform Python
```powershell
python run.py
```

### Node / NPM
```powershell
npm start
```

Once running:
- 🌐 **Frontend Application**: [http://localhost:3000](http://localhost:3000)
- ⚡ **Backend API**: [http://localhost:8000](http://localhost:8000)
- 📖 **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🏗️ Architecture

```
Job-apply-bot/
├── run.py                   # Unified runner for Backend & Frontend
├── start.bat                # Windows 1-click batch launcher
├── start.ps1                # PowerShell launcher
├── package.json             # Root npm scripts
├── .env                     # Central environment configuration
│
├── frontend/                # Next.js 16 (App Router) + React 19 + Tailwind CSS
│   ├── app/
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx          # Real-time stats & activity chart
│   │   │   ├── jobs/page.tsx     # Job discovery with match scoring
│   │   │   ├── applications/page.tsx # Application queue & review drawer
│   │   │   ├── resumes/page.tsx  # Drag & drop resume manager
│   │   │   ├── settings/page.tsx # Auto-apply bot configuration
│   │   │   └── layout.tsx        # Protected dashboard shell & sidebar
│   │   ├── login/page.tsx        # Glassmorphism auth (Login / Register)
│   │   ├── register/page.tsx     # Direct register route
│   │   ├── globals.css           # Glassmorphism dark mode design system
│   │   └── providers.tsx         # React Query & Toast notification providers
│   ├── components/layout/        # Sidebar navigation & Topbar
│   ├── lib/api.ts                # Axios client with auto-refresh JWT interceptor
│   └── store/authStore.ts        # Zustand auth state with localStorage sync
│
└── backend/                 # FastAPI + Async SQLAlchemy + Playwright + Gemini
    ├── app/
    │   ├── main.py               # FastAPI entry point & CORS configuration
    │   ├── core/
    │   │   ├── config.py         # Pydantic Settings from .env
    │   │   ├── database.py       # Async SQLAlchemy sessionmaker
    │   │   └── security.py       # JWT creation & bcrypt password hashing
    │   ├── ai/
    │   │   ├── factory.py        # Selects local, gemini, or claude
    │   │   ├── gemini_provider.py# Google Gemini 1.5 Flash (1500 req/day free)
    │   │   ├── local_provider.py # Deterministic keyword matcher (free fallback)
    │   │   └── claude_provider.py# Anthropic Claude 3.5 Sonnet
    │   ├── browser/
    │   │   ├── browser_engine.py # Playwright automation engine
    │   │   ├── form_detector.py  # ATS form fields & questions detector
    │   │   └── form_filler.py    # Auto-fills candidate data into ATS forms
    │   ├── models/               # Database ORM models (User, Job, Application, Resume)
    │   ├── schemas/              # Pydantic request / response schemas
    │   ├── services/             # Application state machine & eligibility rules
    │   └── api/v1/endpoints/     # REST API routes (auth, jobs, applications, resumes, settings)
    └── jobs/sources/             # Multi-source scrapers (Adzuna, RemoteOK, ATS feeds)
```

---

## ⚙️ Configuration (`.env`)

Configure your credentials in `.env` at the root directory:

```env
# ── Database ──────────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://jobhunter:your_password@localhost:5432/jobhunter
DATABASE_URL_SYNC=postgresql://jobhunter:your_password@localhost:5432/jobhunter

# ── AI Provider ───────────────────────────────────────────────────────────
# Options: "gemini" (1,500 req/day free), "local" (free rule-based), "claude"
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-1.5-flash

# ── Job Scraping Sources ──────────────────────────────────────────────────
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
ADZUNA_COUNTRY=in                     # in=India, us=USA, gb=UK

# ── Auto-Apply Engine Rules ───────────────────────────────────────────────
AUTO_APPLY_ENABLED=false
AUTO_APPLY_MODE=safe                  # "safe" (review before submit) or "auto"
AUTO_APPLY_THRESHOLD=90               # Minimum match score % (0-100)
AUTO_APPLY_MAX_PER_DAY=10             # Daily submission limit
AUTO_APPLY_DELAY_MIN_SEC=30           # Minimum delay between submits
AUTO_APPLY_DELAY_MAX_SEC=120          # Maximum delay between submits
AUTO_APPLY_TEST_MODE=true             # True = Dry run (never clicks final submit)
```

---

## 🎨 Frontend Features

1. **Dashboard (`/`)**:
   - Total Jobs Discovered counter.
   - Applications Today counter.
   - Match Success Rate %.
   - Bot status toggle (Active / Paused).
   - 7-Day interactive activity chart using Recharts.
   - Latest 5 Discovered Jobs with color-coded match scores.

2. **Job Discovery (`/jobs`)**:
   - Search by keyword chips (e.g., Python, React, FastAPI).
   - Filters: Location, Remote Only, Minimum Match Score slider.
   - "Discover Now" real-time trigger.
   - Responsive cards displaying company, location, salary range, required skills tags, and "Add to Queue".

3. **Application Queue (`/applications`)**:
   - Status filters: `All`, `Queued`, `Preparing`, `Ready`, `Submitted`, `Failed`, `Cancelled`.
   - Actions: `Prepare`, `Submit`, `Retry`, `Cancel`.
   - Interactive Slide-in Drawer: View full job description, AI-generated cover letter, and generated ATS form answers.

4. **Resume Manager (`/resumes`)**:
   - Drag & drop PDF/DOCX file upload zone.
   - Active resume indicator (gold star badge).
   - Extracted candidate skills preview tags.

5. **Settings & Preferences (`/settings`)**:
   - Candidate Profile form: First/Last name, Phone, Current Title, Company, Location, LinkedIn, Portfolio.
   - Auto-Apply Bot Configuration: Autonomous applying switch, Safe Mode vs Autopilot selector, threshold slider, daily rate limit, delay range, test mode dry-run switch.
   - AI Engine telemetry: Active LLM status (Google Gemini), API key status, fallback engine status.

---

## 🔌 API Endpoints Reference

| Module | Method | Endpoint | Description |
|---|---|---|---|
| **Auth** | POST | `/api/v1/auth/register` | Register new user account |
| **Auth** | POST | `/api/v1/auth/login` | Login and receive JWT access token |
| **Auth** | GET | `/api/v1/auth/me` | Fetch authenticated candidate profile |
| **Auth** | PUT | `/api/v1/auth/me` | Update candidate profile & contact links |
| **Jobs** | POST | `/api/v1/jobs/discover` | Run multi-source job discovery |
| **Jobs** | GET | `/api/v1/jobs` | Retrieve discovered jobs list |
| **Jobs** | GET | `/api/v1/jobs/stats` | Aggregate discovery stats |
| **Applications** | POST | `/api/v1/applications/` | Add discovered job to application queue |
| **Applications** | GET | `/api/v1/applications/queue` | Fetch queue filtered by status |
| **Applications** | POST | `/api/v1/applications/{id}/prepare` | Trigger AI cover letter & Q&A generation |
| **Applications** | GET | `/api/v1/applications/{id}/review` | Fetch review packet before submission |
| **Applications** | POST | `/api/v1/applications/{id}/submit` | Execute browser submission |
| **Applications** | POST | `/api/v1/applications/test` | Execute safe dry-run simulation |
| **Resumes** | GET | `/api/v1/resumes` | List user resumes |
| **Resumes** | POST | `/api/v1/resumes` | Create resume record |
| **Resumes** | POST | `/api/v1/resumes/{id}/upload` | Upload PDF/DOCX binary file |
| **Settings** | GET | `/api/v1/settings/auto-apply` | Get auto-apply bot configuration |
| **Settings** | PUT | `/api/v1/settings/auto-apply` | Update auto-apply thresholds & rules |

---

## 🛡️ Safety & Anti-Detection

- **Safe Mode Default**: The system prepares answers and cover letters first, pausing for 1-click candidate review before final submission.
- **Dry Run Test Mode**: `AUTO_APPLY_TEST_MODE=true` ensures the browser engine fills and validates forms without ever clicking the final submission button.
- **Human Delay Simulation**: Configurable random delay intervals between applications to prevent bot rate limiting.
#   J o b _ H u n t e r  
 