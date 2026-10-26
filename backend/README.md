# AI Job Hunter — Backend API Service

FastAPI async backend service powering job discovery, resume analysis, ATS matching, Gemini AI generation, and Playwright browser automation.

---

## 🛠️ Tech Stack

- **Framework**: FastAPI + Uvicorn
- **Database ORM**: Async SQLAlchemy 2.0 + asyncpg
- **Migrations**: Alembic
- **AI Engine**: Google Gemini 1.5 Flash (`google-generativeai`), with deterministic local fallback
- **Browser Automation**: Playwright + playwright-stealth
- **Authentication**: JWT (`python-jose`) + bcrypt (`passlib`)
- **Settings**: Pydantic Settings (`pydantic-settings`)

---

## 🚀 Running the Backend

### 1. Activate Virtual Environment
```powershell
cd backend
.venv\Scripts\Activate.ps1
```

### 2. Apply Migrations
```powershell
alembic upgrade head
```

### 3. Start Server
```powershell
uvicorn app.main:app --reload --port 8000
```

Interactive API documentation will be available at:
- **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🔌 API Routes Structure

- `/api/v1/auth`: User registration, JWT login, candidate profile GET/PUT
- `/api/v1/jobs`: Multi-source job discovery, listing, filtering, and stats
- `/api/v1/applications`: Application queue management, prepare Q&A, review packet, submit, dry-run
- `/api/v1/resumes`: Resume records, PDF/DOCX file upload, skill extraction
- `/api/v1/settings`: Auto-apply bot configuration (threshold, daily limits, safe mode, test mode)
