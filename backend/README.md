# AI Job Hunter — Backend API Service

FastAPI asynchronous backend service powering autonomous job discovery across 12+ sources, resume parsing, ATS scoring, Gemini AI generation, and Playwright browser automation.

---

## 🛠️ Technology Stack

- **Web Framework**: FastAPI 0.115 + Uvicorn (ASGI)
- **Database & ORM**: PostgreSQL / Supabase, SQLAlchemy 2.0 (Asyncio) + `asyncpg`
- **Migrations**: Alembic 1.13
- **AI Engine**: Google Gemini 1.5 Flash (`google-generativeai`), Anthropic Claude 3.5 Sonnet, and offline local heuristic engine
- **Browser Automation**: Playwright 1.48 + `playwright-stealth`
- **Security & Auth**: JWT (`python-jose`) + bcrypt password hashing (`passlib`)
- **Validation**: Pydantic v2 + `pydantic-settings`
- **Resume Parsing**: `pypdf` + `python-docx`

---

## 🚀 Running the Backend

### 1. Activate Virtual Environment
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

### 2. Configure Environment (`.env`)
Ensure `.env` at the root directory contains your database credentials and API keys:
```ini
DATABASE_URL=postgresql+asyncpg://...
DATABASE_URL_SYNC=postgresql://...
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

### 3. Run Database Migrations
```powershell
alembic upgrade head
```
*(Or execute `supabase_schema.sql` directly in your Supabase SQL Editor).*

### 4. Start Development Server
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The interactive API documentation is available at:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📁 Backend Directory Architecture

```
backend/
├── alembic/                        # Database migration scripts
│   ├── env.py                      # Dual sync/async Alembic runner
│   └── versions/
│       └── 0001_initial_schema.py  # Base database tables migration
├── alembic.ini                     # Alembic configuration
├── supabase_schema.sql             # Turnkey PostgreSQL schema for Supabase
├── requirements.txt                # Python backend dependencies
│
├── app/
│   ├── main.py                     # FastAPI entry point, CORS & lifespan hooks
│   ├── core/                       # Core configuration, async database engine & security
│   ├── models/                     # SQLAlchemy 2.0 models (User, Resume, Job, Application)
│   ├── schemas/                    # Pydantic validation request/response schemas
│   ├── services/                   # Application state machine & resume service
│   ├── ai/                         # Pluggable AI engine (Gemini, Claude, Local fallback)
│   ├── browser/                    # Playwright engine, ATS detection & form filler
│   └── api/v1/endpoints/           # REST endpoints (/auth, /jobs, /applications, /resumes, /settings)
│
└── jobs/                           # Multi-source job scraper subsystem
    ├── service.py                  # Job discovery coordinator
    ├── normalizer.py               # Field normalization & SHA-256 fingerprinting
    └── sources/                    # 12+ Specialized job scrapers (RemoteOK, Adzuna, LinkedIn, etc.)
```

---

## 🔌 API Endpoints Summary

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/v1/auth/register` | Register new user account |
| **Auth** | `POST` | `/api/v1/auth/login` | Login and receive JWT access token |
| **Auth** | `GET` | `/api/v1/auth/me` | Fetch authenticated candidate profile |
| **Auth** | `PUT` | `/api/v1/auth/me` | Update candidate profile & contact links |
| **Jobs** | `POST` | `/api/v1/jobs/discover` | Run multi-source job discovery |
| **Jobs** | `GET` | `/api/v1/jobs` | Retrieve discovered jobs list with filters |
| **Jobs** | `GET` | `/api/v1/jobs/stats` | Aggregate discovery stats |
| **Jobs** | `GET` | `/api/v1/jobs/sources` | Status of all 12+ scrapers |
| **Applications** | `POST` | `/api/v1/applications/` | Add discovered job to application queue |
| **Applications** | `GET` | `/api/v1/applications/queue` | Fetch queue filtered by status |
| **Applications** | `GET` | `/api/v1/applications/stats` | Real-time daily application statistics |
| **Applications** | `POST` | `/api/v1/applications/{id}/submit` | Execute browser submission |
| **Applications** | `POST` | `/api/v1/applications/test` | Execute safe dry-run simulation |
| **Resumes** | `GET` | `/api/v1/resumes` | List user resumes |
| **Resumes** | `POST` | `/api/v1/resumes` | Create resume record |
| **Resumes** | `POST` | `/api/v1/resumes/{id}/upload` | Upload PDF/DOCX binary file |
| **Resumes** | `POST` | `/api/v1/resumes/{id}/analyze` | Trigger AI ATS scoring & feedback |
| **Settings** | `GET` | `/api/v1/settings/auto-apply` | Get auto-apply bot configuration |
| **Settings** | `PUT` | `/api/v1/settings/auto-apply` | Update auto-apply thresholds & rules |
