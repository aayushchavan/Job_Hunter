# AI Job Hunter (Job-Apply-Bot)
## Complete Technical Architecture & System Documentation

---

### Executive Overview

**AI Job Hunter** is a full-stack, enterprise-grade autonomous and semi-autonomous job application platform. It automatically discovers job opportunities across 12+ public and API sources, normalizes and deduplicates listings, evaluates candidate eligibility against configurable rules, performs semantic match scoring with LLMs (Google Gemini / Anthropic Claude / local keyword heuristics), and executes automated form filling and submissions via headless/headed Playwright browser automation with integrated stealth and safety controls.

```mermaid
graph TD
    subgraph Client ["Frontend Client (Next.js 16 + React 19)"]
        UI_Dash["Dashboard & Analytics"]
        UI_Jobs["Job Discovery & Filters"]
        UI_Apps["Application Queue & Review"]
        UI_Res["Resume & ATS Analyzer"]
        UI_Set["Automation Settings"]
    end

    subgraph API ["FastAPI Asynchronous Gateway"]
        Auth_MW["JWT Security & Auth"]
        EP_Jobs["/api/v1/jobs"]
        EP_Apps["/api/v1/applications"]
        EP_Res["/api/v1/resumes"]
        EP_Set["/api/v1/settings"]
    end

    subgraph CoreServices ["Backend Application Services"]
        JobService["JobDiscoveryService"]
        EligService["EligibilityService"]
        ResumeService["ResumeService"]
        AppService["ApplicationService (FSM)"]
        AIService["AIProvider (Gemini / Claude / Local)"]
        BrowserService["BrowserEngine (Playwright + Stealth)"]
    end

    subgraph DataStore ["Database Layer (Supabase / PostgreSQL 15+)"]
        DB_Users[(users)]
        DB_Resumes[(resumes)]
        DB_Jobs[(jobs & job_sources)]
        DB_Apps[(applications & attempts)]
        DB_Rules[(eligibility & settings)]
    end

    Client -->|REST / JSON + Bearer JWT| API
    API --> CoreServices
    CoreServices --> DataStore
    JobService -->|Scrape / Ingest| ExternalSources["12+ External Job Boards"]
    BrowserService -->|Automate / Submit| ATS_Portals["Greenhouse, Lever, Workday, Custom ATS"]
```

---

### 1. Technology Stack Specification

| Subsystem | Primary Technology | Version / Tooling | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Python | `>= 3.10` | High-concurrency asynchronous API and scraper workers |
| **API Framework** | FastAPI | `0.115.0` | Asynchronous web framework with OpenAPI / Swagger generation |
| **Async ASGI Server**| Uvicorn | `0.31.0` | High-performance ASGI production server |
| **Database ORM** | SQLAlchemy | `2.0.36` (Asyncio) | Type-safe declarative ORM with async session management |
| **Async DB Driver** | asyncpg | `0.30.0` | Native asynchronous PostgreSQL binary protocol driver |
| **Schema Migrations**| Alembic | `1.13.3` | Version-controlled declarative database migrations |
| **Database Engine** | PostgreSQL / Supabase | `15+` | Relational store with GIN trigram, JSONB, and Vector capabilities |
| **Validation Layer**| Pydantic V2 | `2.9.2` | Data validation, deserialization, and BaseSettings parsing |
| **Browser Engine** | Playwright | `1.48.0` | Headless Chromium automation with `playwright-stealth` |
| **AI Providers** | Google Gemini / Claude | `google-generativeai >= 0.8` | Semantic resume analysis, match scoring, cover letter writing |
| **Frontend Framework**| Next.js | `16.4.0` (App Router) | React Server Components, server actions, and edge rendering |
| **UI Library** | React | `19.3.0` | Concurrent mode interactive UI components |
| **Styling** | Tailwind CSS | `v4` | Glassmorphic dark-mode utility styling |
| **Client State** | Zustand + TanStack Query| `Zustand 5` / `React Query 5`| Global auth store and cached server query management |

---

### 2. Complete Monorepo Directory Architecture

```
Job-apply-bot/
├── run.py                          # Unified launcher (starts backend & frontend concurrently)
├── start.bat                       # Windows Batch 1-click launcher
├── start.ps1                       # PowerShell launcher
├── package.json                    # Root npm scripts ("npm start", "npm run dev")
├── .env / .env.example             # Central configuration (DB, AI keys, JWT secrets)
│
├── backend/                        # Python FastAPI Backend
│   ├── run.py                      # Standalone backend runner
│   ├── requirements.txt            # Python backend dependencies
│   ├── alembic.ini                 # Alembic migration configuration
│   ├── supabase_schema.sql         # Production-ready PostgreSQL schema for Supabase
│   │
│   ├── alembic/
│   │   ├── env.py                  # Dual sync/async Alembic environment configuration
│   │   └── versions/
│   │       └── 0001_initial_schema.py # Initial database migration
│   │
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory, CORS, exception handlers
│   │   ├── core/                   # Core infrastructure
│   │   │   ├── config.py           # Pydantic BaseSettings loading from root .env
│   │   │   ├── database.py         # Async SQLAlchemy engine, sessionmaker, Supabase pooler support
│   │   │   └── security.py         # Passlib bcrypt hashing, JWT access/refresh token generation
│   │   ├── models/                 # SQLAlchemy 2.0 ORM Models
│   │   │   ├── base.py             # Mixins: UUIDPrimaryKeyMixin, TimestampMixin, cross-DB UUID
│   │   │   ├── user.py             # User profile, contact, work auth, links, EEO disclosures
│   │   │   ├── resume.py           # Resume documents, parsed text, AI score, feedback
│   │   │   ├── job.py              # Jobs, source metadata, fingerprints, ATS tokens
│   │   │   ├── eligibility.py      # Hard-stop candidate filtering criteria
│   │   │   └── application.py      # Finite State Machine, retry attempts, cached answers, quotas
│   │   ├── schemas/                # Pydantic V2 Request & Response DTOs
│   │   │   ├── user.py             # User register/login/profile schemas
│   │   │   ├── job.py              # Job filter, discovery request/response, stats
│   │   │   ├── resume.py           # Resume upload, parse results, AI score DTOs
│   │   │   └── application.py      # Application queue items, review payload, attempt logs
│   │   ├── services/               # Core Business Logic Layer
│   │   │   ├── application_service.py # Application lifecycle state machine & queue runner
│   │   │   ├── eligibility_service.py # Pre-screening engine (evaluates rules before AI calls)
│   │   │   └── resume_service.py   # PDF/DOCX parsing (pypdf/docx), AI skill extraction & scoring
│   │   ├── ai/                     # Modular Multi-Provider AI Architecture
│   │   │   ├── base.py             # Abstract BaseAIProvider contract
│   │   │   ├── factory.py          # AI Provider Factory (gemini | claude | local)
│   │   │   ├── gemini_provider.py  # Google Gemini 1.5 Flash (Free tier 1,500 req/day)
│   │   │   ├── claude_provider.py  # Anthropic Claude 3.5 Sonnet provider
│   │   │   └── local_provider.py   # Deterministic keyword/TF-IDF matcher (Zero-cost fallback)
│   │   ├── browser/                # Playwright Automation Subsystem
│   │   │   ├── browser_engine.py   # Headless/headed Chromium launcher with stealth masking
│   │   │   ├── form_detector.py    # ATS detector (Greenhouse, Lever, Workday, custom forms)
│   │   │   └── form_filler.py      # Form filler, resume uploader, and test-mode safety blocker
│   │   ├── utils/
│   │   │   └── db_types.py         # Custom SQLAlchemy cross-dialect types (ArrayOfText, JsonBlob)
│   │   └── api/v1/endpoints/       # REST API Endpoints
│   │       ├── auth.py             # /auth/register, /auth/login, /auth/me, /auth/refresh
│   │       ├── jobs.py             # /jobs/discover, /jobs/list, /jobs/{id}, /jobs/stats
│   │       ├── resumes.py          # /resumes/upload, /resumes/{id}/analyze, /resumes/list
│   │       ├── applications.py     # /applications/queue, /applications/{id}/submit, logs
│   │       └── settings.py         # /settings/auto-apply, /settings/eligibility
│   │
│   └── jobs/                       # Job Scraping Subsystem
│       ├── service.py              # Orchestrator querying all enabled sources in parallel
│       ├── normalizer.py           # Field normalizer, salary parser, SHA-256 fingerprinting
│       └── sources/                # 12+ Specialized Source Fetchers
│           ├── base.py             # BaseJobSource abstract class
│           ├── registry.py         # Dynamic source discovery & registry
│           ├── adzuna.py           # Adzuna Developer API
│           ├── remoteok.py         # RemoteOK API
│           ├── weworkremotely.py   # WeWorkRemotely RSS feed
│           ├── himalayas.py        # Himalayas Jobs API
│           ├── arbeitnow.py        # Arbeitnow API (Visa sponsorship tracking)
│           ├── jobicy.py           # Jobicy Remote Jobs feed
│           ├── jobspresso.py       # Jobspresso feed
│           ├── remotive.py         # Remotive Jobs API
│           ├── themuse.py          # The Muse API
│           ├── workingnomads.py    # Working Nomads feed
│           ├── hackernews.py       # "Who is Hiring?" monthly thread scraper
│           └── linkedin.py         # Public guest job search scraper
│
└── frontend/                       # Next.js 16 + React 19 Frontend
    ├── package.json                # Frontend dependencies (@tanstack/react-query, recharts, radix-ui)
    ├── next.config.ts              # Next.js build and proxy configuration
    ├── tsconfig.json               # TypeScript compiler config
    │
    ├── app/                        # Next.js App Router
    │   ├── layout.tsx              # Root HTML layout with fonts and metadata
    │   ├── globals.css             # Glassmorphism dark-theme design system & animations
    │   ├── providers.tsx           # React Query Client & Toast notification wrappers
    │   ├── login/page.tsx          # User login page
    │   ├── register/page.tsx       # User registration page
    │   │
    │   └── (dashboard)/            # Protected Authenticated App Layout
    │       ├── layout.tsx          # Sidebar layout shell with authentication guards
    │       ├── page.tsx            # Main KPI dashboard with daily statistics & charts
    │       ├── jobs/page.tsx       # Searchable job feed, filters, and match scores
    │       ├── applications/page.tsx # Kanban/pipeline tracker for applications & attempts
    │       ├── resumes/page.tsx    # Resume manager, ATS score breakdown & skill tags
    │       └── settings/page.tsx   # Auto-apply thresholds, daily limits & safety toggles
    │
    ├── components/
    │   ├── layout/Sidebar.tsx      # Collapsible navigation sidebar
    │   └── ui/ToastProvider.tsx    # Toast notification system
    │
    ├── lib/
    │   ├── api.ts                  # Axios client with automatic JWT header & refresh
    │   └── utils.ts                # Date formatting, score badge colors, class mergers
    │
    └── store/
        └── authStore.ts            # Zustand store syncing user token with localStorage
```

---

### 3. Database Schema & Data Models

The database comprises **10 normalized relational tables** supporting UUID primary keys, timezone-aware timestamps, GIN indexing for array and full-text searches, and foreign key cascades.

```mermaid
erDiagram
    users ||--o{ resumes : owns
    users ||--o{ applications : submits
    users ||--o| eligibility_criteria : defines
    users ||--o| auto_apply_settings : configures
    users ||--o{ application_daily_stats : tracks

    job_sources ||--o{ jobs : discovers
    jobs ||--o{ applications : receives

    resumes ||--o{ applications : attaches
    applications ||--o{ application_attempts : logs
    applications ||--o{ application_answers : caches

    users {
        uuid id PK
        string email UK
        string hashed_password
        string first_name
        string last_name
        string current_title
        string current_company
        int years_of_experience
        string work_authorization
        boolean requires_sponsorship
        int desired_salary_min
        string salary_currency
    }

    resumes {
        uuid id PK
        uuid user_id FK
        string name
        string file_path
        text parsed_text
        int score
        text_array extracted_skills
        text_array domain_tags
        jsonb rating_feedback
    }

    jobs {
        uuid id PK
        uuid source_id FK
        string source_job_id
        string title
        string company_name
        text description
        string location
        boolean is_remote
        text_array required_skills
        int salary_min
        int salary_max
        string canonical_url
        string fingerprint UK
        int match_score
    }

    applications {
        uuid id PK
        uuid user_id FK
        uuid job_id FK
        uuid resume_id FK
        string status
        int match_score
        int attempt_count
        int max_attempts
        boolean requires_user_input
        boolean is_test_run
        jsonb detected_fields
        jsonb filled_fields
    }

    application_attempts {
        uuid id PK
        uuid application_id FK
        int attempt_number
        string status
        boolean resume_uploaded
        boolean would_submit
        string error_type
        text error_message
        jsonb step_log
    }

    application_answers {
        uuid id PK
        uuid application_id FK
        text question_text
        text answer
        string source
        numeric confidence
    }
```

#### Detailed Table Specifications

1. **`users`**: Master candidate profile. Stores credentials (`hashed_password` via bcrypt), contact info, links (LinkedIn, GitHub, Portfolio), employment eligibility (citizenship/visa, sponsorship needs, notice period), desired compensation, and standard demographic disclosures (gender, disability, veteran status).
2. **`resumes`**: User resume documents. Retains physical file metadata, raw extracted plain text, domain classification tags (`backend`, `ml`, `fullstack`), extracted skills array, and AI rating scores with multi-dimensional feedback (structure, keywords, readability).
3. **`job_sources`**: Ingestion source registry. Tracks supported platforms (Adzuna, RemoteOK, Greenhouse, Lever, etc.), API base endpoints, and active/inactive health flags.
4. **`jobs`**: Normalized job directory. Enforces deduplication via `(source_job_id, source_id)` and a unique SHA-256 `fingerprint`. Houses structured requirements, salary bands, work modes (`remote`, `hybrid`, `onsite`), ATS tokens (`greenhouse_job_id`, `lever_posting_id`), and raw JSON payloads.
5. **`eligibility_criteria`**: Hard pre-screening filter rules linked `1:1` to a user. Configures allowed/excluded job titles, minimum education, graduation year cutoffs, maximum experience limits, restricted domains, and excluded companies.
6. **`applications`**: Core application entity enforcing the Finite State Machine. Couples candidate, job, and targeted resume. Records current status, matching justifications, submission methods, and captured form fields.
7. **`application_attempts`**: Audit trail for each execution pass. Logs execution timestamps, field counts, uploaded resume verification, error stack traces, and complete step-by-step browser interaction logs (`step_log`).
8. **`application_answers`**: Knowledge bank of question-and-answer pairs generated during applications. Prevents repetitive LLM calls for recurring questions (e.g. *"Why do you want to work here?"*, *"Years of experience with Docker?"*).
9. **`auto_apply_settings`**: Per-user automation policy. Controls operational mode (`safe` requiring approval vs. `auto` fully autonomous), minimum match score threshold (e.g. `90%`), daily quotas, retry allowances, and the safety flag `is_test_mode`.
10. **`application_daily_stats`**: Per-day tracking counters (`applications_started`, `applications_submitted`, `applications_failed`, `applications_rejected`) to enforce daily throttle limits and generate dashboard activity charts.

---

### 4. Job Ingestion & Deduplication Pipeline

The ingestion system collects listings from diverse sources, transforms unstructured payloads into a standardized schema, and eliminates duplicates across platforms.

```mermaid
sequenceDiagram
    participant Scheduler as JobDiscoveryService
    participant Sources as Scraper Workers (12+)
    participant Normalizer as JobNormalizer
    participant DB as PostgreSQL (jobs)

    Scheduler->>Sources: Query active feeds concurrently (asyncio.gather)
    Sources-->>Scheduler: Return raw job payloads
    loop For each job item
        Scheduler->>Normalizer: normalize(raw_payload)
        Normalizer->>Normalizer: Extract location, clean HTML, parse salary
        Normalizer->>Normalizer: Extract technical skills (Regex + dictionary)
        Normalizer->>Normalizer: Compute SHA-256 fingerprint
        Normalizer-->>Scheduler: Return NormalizedJob
        Scheduler->>DB: Upsert with ON CONFLICT (source_job_id, source_id)
    end
```

#### Deduplication Strategy
* **Primary Key Constraint:** `UniqueConstraint("source_job_id", "source_id")` prevents re-ingesting the exact same ID from the same source.
* **Cross-Source Fingerprinting:** A 64-character SHA-256 hash is computed across normalized strings:
  $$\text{fingerprint} = \text{SHA256}(\text{source\_name} + \text{clean\_company} + \text{clean\_title} + \text{canonical\_url})$$
  This flags cross-posted listings appearing on multiple job boards simultaneously.

---

### 5. Multi-Provider AI & Scoring Engine

The AI subsystem is decoupled through the abstract interface [BaseAIProvider](file:///d:/Job-apply-bot/backend/app/ai/base.py) and instantiated dynamically via [AIFactory](file:///d:/Job-apply-bot/backend/app/ai/factory.py).

```
                      ┌──────────────────────┐
                      │    AIFactory.get()   │
                      └──────────┬───────────┘
                                 │ Reads AI_PROVIDER from .env
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  GeminiProvider  │   │  ClaudeProvider  │   │  LocalProvider   │
│ (1.5 / 3.5 Flash)│   │  (3.5 Sonnet)    │   │ (Zero API Cost)  │
│ Free 1,500 req/d │   │ Precision Score  │   │ Regex + TF-IDF   │
└──────────────────┘   └──────────────────┘   └──────────────────┘
```

#### Core Capabilities:
1. **Semantic Match Scoring (0–100):** Compares candidate's skills, experience depth, and career level against the job requirements. Returns an integer score and detailed bullet points justifying the rating.
2. **Resume ATS Optimization:** Evaluates uploaded PDF/DOCX resumes against industry standards, returning structural scores, formatting feedback, and detected skill deficiencies.
3. **Tailored Cover Letter Generation:** Synthesizes candidate's real project achievements with the employer's specific mission and tech stack without fabricating experience.
4. **Context-Aware Question Answering:** Answers employer application questionnaires using only verified information from the candidate's profile and resume.

---

### 6. Application State Machine (FSM)

Applications progress through a strict **Finite State Machine** governed by `VALID_TRANSITIONS` in [application.py](file:///d:/Job-apply-bot/backend/app/models/application.py). Invalid state transitions raise immediate exceptions.

```mermaid
stateDiagram-v2
    [*] --> DISCOVERED

    DISCOVERED --> ELIGIBLE : Pass Hard Criteria
    DISCOVERED --> REJECTED : Fail Criteria
    DISCOVERED --> DUPLICATE : Already Processed

    ELIGIBLE --> MATCHED : Score >= Threshold
    ELIGIBLE --> REJECTED : Score < Threshold

    MATCHED --> QUEUED : Ready for Processing
    MATCHED --> WITHDRAWN : Cancelled by User

    QUEUED --> PREPARING : Worker Picks Up

    PREPARING --> REVIEW : Safe Mode (Wait User)
    PREPARING --> SUBMITTING : Auto Mode (Direct)
    PREPARING --> USER_INPUT_REQUIRED : Unknown Question
    PREPARING --> CAPTCHA_REQUIRED : Challenge Detected
    PREPARING --> FAILED : Error

    REVIEW --> SUBMITTING : User Approves
    REVIEW --> WITHDRAWN : User Discards

    USER_INPUT_REQUIRED --> QUEUED : User Provides Info
    CAPTCHA_REQUIRED --> QUEUED : Solved

    SUBMITTING --> SUBMITTED : Success
    SUBMITTING --> FAILED : Submission Error

    FAILED --> QUEUED : Retry (Attempts < Max)
    FAILED --> WITHDRAWN : Retries Exhausted

    SUBMITTED --> INTERVIEW : Follow-up
    INTERVIEW --> OFFER : Selected
    SUBMITTED --> WITHDRAWN : Candidate Withdrew
```

---

### 7. Playwright Browser Automation & Safety Engine

The automation subsystem interacts directly with web-based job application portals using Playwright.

```mermaid
flowchart TD
    Start["Queue Worker Picks Application"] --> Launch["Launch Chromium (Playwright + Stealth)"]
    Launch --> Navigate["Navigate to application_url"]
    Navigate --> Detect["FormDetector: Analyze DOM & ATS Type"]
    
    Detect --> CheckATS{"ATS Identified?"}
    CheckATS -->|Greenhouse| FillGH["Greenhouse Adapter"]
    CheckATS -->|Lever| FillLever["Lever Adapter"]
    CheckATS -->|Workday / Custom| FillGeneric["Generic Heuristic Adapter"]

    FillGH --> Populate["FormFiller: Populate Inputs with Typing Delays"]
    FillLever --> Populate
    FillGeneric --> Populate

    Populate --> Upload["Upload Resume Document"]
    Upload --> SafetyCheck{"Is AUTO_APPLY_TEST_MODE True?"}
    
    SafetyCheck -->|YES (Safety Active)| ScreenShot["Capture Full-Page Screenshot & Halt Before Submit"]
    SafetyCheck -->|NO (Live Mode)| FinalSubmit["Click Submit Button & Verify Confirmation"]
    
    ScreenShot --> SaveAttempt["Record Attempt as COMPLETED (Test)"]
    FinalSubmit --> SaveAttemptLive["Record Attempt & Mark SUBMITTED"]
```

#### Key Safety Guardrails:
* **`AUTO_APPLY_TEST_MODE = true`**: When active, the bot navigates, fills out every form field, uploads the resume, validates inputs, but **NEVER clicks the final Submit button**. Instead, it captures a high-resolution screenshot to `./uploads/screenshots/` for manual inspection.
* **Human-like Timing Delays:** Implements jittered keystroke delays (50–150ms per key) and inter-action pauses (30–120 seconds between applications) to avoid bot detection and IP rate limiting.
* **Stealth Plugin:** Overrides `navigator.webdriver`, mocks WebGL renderers, and injects standard browser fingerprint headers.

---

### 8. REST API Specification (Endpoints Overview)

All endpoints reside under `/api/v1/` and enforce JSON schemas validated via Pydantic.

#### Authentication (`/api/v1/auth`)
* `POST /register`: Creates candidate account with hashed password.
* `POST /login`: Validates credentials; returns JWT access and refresh tokens.
* `POST /refresh`: Issues a refreshed access token.
* `GET /me`: Returns the authenticated user profile and contact settings.
* `PATCH /me`: Updates career headline, links, salary criteria, and work authorization.

#### Jobs & Discovery (`/api/v1/jobs`)
* `POST /discover`: Triggers asynchronous scraping across all configured sources.
* `GET /`: Paginated list of discovered jobs with keyword, source, remote, and score filters.
* `GET /{id}`: Detailed view of a single job including full requirements and ATS tokens.
* `GET /stats`: Aggregated statistics on discovered jobs, remote percentages, and active sources.
* `GET /sources`: Status list of all 12+ ingestion scrapers.

#### Resumes & ATS Scoring (`/api/v1/resumes`)
* `POST /upload`: Multipart upload (PDF or DOCX); parses text and extracts skills.
* `GET /`: Lists all resumes owned by the candidate with active tags.
* `GET /{id}`: Detailed parsed content and AI evaluation score.
* `POST /{id}/analyze`: Triggers on-demand AI ATS scoring against target domains.
* `DELETE /{id}`: Deletes resume and cascades to associated files.

#### Applications & Automation Queue (`/api/v1/applications`)
* `GET /queue`: Returns applications awaiting submission or pending manual review.
* `POST /{job_id}/apply`: Initializes an application cycle for a targeted job.
* `POST /{id}/submit`: Approves and triggers automated browser submission.
* `POST /{id}/withdraw`: Terminal state cancellation.
* `GET /{id}/attempts`: Complete audit trail and step logs for previous attempts.

#### Settings & Policies (`/api/v1/settings`)
* `GET /auto-apply`: Retrieves user-specific automation quotas, modes, and thresholds.
* `PUT /auto-apply`: Modifies auto-apply rules (e.g. adjust threshold from 90 to 85).
* `GET /eligibility`: Retrieves hard pre-screening criteria.
* `PUT /eligibility`: Updates forbidden companies, allowed roles, and minimum salary.

---

### 9. Frontend Architecture (Next.js 16 + React 19)

The client application utilizes Next.js 16 App Router with React 19 and Tailwind CSS.

* **Dashboard Overview (`/`)**: Displays live KPI metrics (Applications Submitted Today, Current Daily Limit, Average Match Score, Pending Reviews) and visual Recharts graphs.
* **Job Board (`/jobs`)**: Real-time searchable job feed with dynamic match score badges, remote filter toggles, salary filters, and quick-apply drawers.
* **Application Tracker (`/applications`)**: Pipeline tracking view displaying application progress across the 16 state machine stages with inline error logs and attempt history modals.
* **Resume Manager (`/resumes`)**: Drag-and-drop document upload interface with interactive ATS score gauge, domain tag assignments, skill cloud visualizations, and targeted improvement suggestions.
* **Bot Settings (`/settings`)**: Interactive control center for tuning the auto-apply engine: toggle between **Safe Mode** (review before submit) and **Auto Mode**, configure daily submission quotas, adjust minimum match score thresholds, and manage hard eligibility rules.

---

### 10. Environment Configuration Reference (`.env`)

```ini
# ── Database Connection ──────────────────────────────────────────────────────────
# Supabase Pooler (Port 6543) or Direct PostgreSQL (Port 5432)
DATABASE_URL=postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?ssl=require
DATABASE_URL_SYNC=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require

# ── Security Keys ────────────────────────────────────────────────────────────────
SECRET_KEY=generate-32-byte-random-hex-string
ENCRYPTION_KEY=generate-fernet-compatible-key
JWT_SECRET=generate-secure-jwt-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200
REFRESH_TOKEN_EXPIRE_DAYS=90

# ── AI Provider ──────────────────────────────────────────────────────────────────
# Options: "gemini" (free 1,500 req/day), "local" (free rule-based), "claude"
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# ── Job Scraping API Keys (Optional) ─────────────────────────────────────────────
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
ADZUNA_COUNTRY=in

# ── Automation Safety Guardrails ─────────────────────────────────────────────────
AUTO_APPLY_ENABLED=false
AUTO_APPLY_MODE=safe                # "safe" (requires user approval) | "auto"
AUTO_APPLY_THRESHOLD=90             # Minimum match score required to apply (0-100)
AUTO_APPLY_MAX_PER_DAY=10           # Maximum applications per 24 hours
AUTO_APPLY_DELAY_MIN_SEC=30         # Minimum delay between applications
AUTO_APPLY_DELAY_MAX_SEC=120        # Maximum delay between applications
AUTO_APPLY_TEST_MODE=true           # When true: Fills forms but NEVER clicks submit!
```
