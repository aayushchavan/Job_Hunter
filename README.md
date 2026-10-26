<div align="center">

# 🤖 AI Job Hunter (Job-Apply-Bot)

### *Autonomous Multi-Source Job Discovery, Semantic AI Matching & ATS Auto-Apply Bot*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.4-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://supabase.com)
[![Playwright](https://img.shields.io/badge/Playwright-Stealth-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![Gemini](https://img.shields.io/badge/AI-Google_Gemini-8E75C4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br/>

**AI Job Hunter** is an end-to-end fullstack platform that finds jobs across 12+ public and API sources, evaluates candidate eligibility, calculates semantic match scores against your resume using LLMs (Gemini / Claude / local heuristics), and automates form filling on applicant tracking systems (Greenhouse, Lever, Workday) with built-in safety controls.

[Features](#-key-features) • [Quick Start](#-quick-start) • [Architecture](#-system-architecture) • [Database & Supabase](#-database-setup-supabase) • [Configuration](#-configuration-env) • [API Reference](#-api-endpoints)

</div>

---

## ✨ Key Features

| Capability | Highlights |
| :--- | :--- |
| 📡 **Multi-Source Job Aggregation** | Live scrapers and APIs for **12+ sources**: Adzuna, RemoteOK, WeWorkRemotely, Himalayas, Arbeitnow, Jobicy, Jobspresso, Remotive, The Muse, Working Nomads, Hacker News "Who is Hiring", and LinkedIn. |
| 🧠 **Multi-Engine AI Matching** | Pluggable AI engine supporting **Google Gemini 1.5 Flash** (1,500 free requests/day), **Claude 3.5 Sonnet**, or a **Zero-Cost Local Heuristic Engine** (TF-IDF / regex). |
| 📄 **ATS Resume Intelligence** | PDF & DOCX resume parser that evaluates your resume against ATS standards, extracts key skills, and calculates dynamic job compatibility scores (0–100%). |
| 🤖 **Autonomous Browser Automation** | Headless/headed **Playwright** browser engine with `playwright-stealth` anti-detection to fill forms, dropdowns, and file uploads on Greenhouse, Lever, and custom portals. |
| 🛡️ **Safety-First Guardrails** | **Safe Mode** pauses before final submission for 1-click review. **Test Mode (`AUTO_APPLY_TEST_MODE=true`)** fills forms and captures full-page verification screenshots without ever clicking Submit. |
| 📊 **Modern Fullstack Dashboard** | Built with **Next.js 16**, **React 19**, and **Tailwind CSS**. Includes real-time queue tracking, analytics charts, interactive review drawers, and resume management. |

---

## ⚡ Quick Start

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/aayushchavan/Job_Hunter.git
cd Job_Hunter
```

Copy the example environment file and configure your database and API keys:

```bash
cp .env.example .env
```

### 2. Single-Command Launch

Start both the **FastAPI Backend** and the **Next.js Frontend** simultaneously:

#### Windows (PowerShell)
```powershell
.\start.ps1
```

#### Windows (Command Prompt / Batch)
```cmd
start.bat
```

#### Cross-Platform Python
```bash
python run.py
```

#### Node / NPM
```bash
npm start
```

### 3. Open in Browser

* 🌐 **Frontend Web App**: [http://localhost:3000](http://localhost:3000)
* ⚡ **Backend API**: [http://localhost:8000](http://localhost:8000)
* 📖 **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph Frontend ["Next.js 16 Client (React 19 + Tailwind CSS)"]
        UI_Dash["Dashboard & KPIs"]
        UI_Jobs["Job Discovery & Search"]
        UI_Queue["Application Review Pipeline"]
        UI_Resume["ATS Resume Manager"]
    end

    subgraph Backend ["FastAPI Asynchronous Gateway"]
        Auth["JWT Auth & Security"]
        JobSvc["Job Discovery Coordinator"]
        MatchSvc["Eligibility & AI Match Engine"]
        AppSvc["Application State Machine (FSM)"]
        BrowserSvc["Playwright Stealth Engine"]
    end

    subgraph Data ["Database (Supabase / PostgreSQL 15+)"]
        DB[(10 Relational Tables)]
    end

    Frontend -->|REST API + Bearer JWT| Backend
    Backend --> Data
    JobSvc -->|Scrape| ExternalJobs["12+ Job Boards & APIs"]
    BrowserSvc -->|Auto-Apply| ATS["Greenhouse / Lever / Workday"]
```

---

## 🗄️ Database Setup (Supabase)

The project is built on **PostgreSQL** using **SQLAlchemy 2.0 (Async)** and **asyncpg**. It is 100% compatible with **Supabase**.

### Option A: Direct SQL Import (Fastest)
1. Open your [Supabase Dashboard](https://supabase.com/dashboard) → **SQL Editor**.
2. Copy and paste the contents of [`backend/supabase_schema.sql`](backend/supabase_schema.sql).
3. Click **Run**. All 10 tables, GIN trigram indexes, foreign key cascades, and timestamp triggers will be created instantly.

### Option B: Alembic Migrations
```bash
cd backend
python -m alembic upgrade head
```

### Configure Connection String in `.env`
Under **Project Settings** → **Database** → **Connection string (URI)**, copy the URL:

```ini
# Supabase Transaction Pooler (Port 6543 - Recommended)
DATABASE_URL=postgresql+asyncpg://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?ssl=require
DATABASE_URL_SYNC=postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
```

> **Note:** If your password contains special characters (`@`, `#`, `$`, `%`), URL-encode them (e.g. `@` becomes `%40`).

---

## ⚙️ Configuration (`.env`)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | Async PostgreSQL connection string (`asyncpg`) | `postgresql+asyncpg://...` |
| `DATABASE_URL_SYNC` | Sync connection string for Alembic migrations | `postgresql://...` |
| `AI_PROVIDER` | Active AI engine: `gemini` (free tier), `claude`, or `local` | `gemini` |
| `GEMINI_API_KEY` | Google Gemini API key ([Get free key](https://aistudio.google.com/app/apikey)) | — |
| `GEMINI_MODEL` | Gemini model variant | `gemini-1.5-flash` |
| `AUTO_APPLY_ENABLED`| Master toggle for automated job application | `false` |
| `AUTO_APPLY_MODE` | `safe` (wait for 1-click human review) or `auto` (autopilot) | `safe` |
| `AUTO_APPLY_THRESHOLD` | Minimum AI match score required to apply (0–100) | `90` |
| `AUTO_APPLY_MAX_PER_DAY` | Safety rate limit for submissions per 24 hours | `10` |
| `AUTO_APPLY_TEST_MODE`| **Safety Guard**: Fills forms & screenshots, never submits | `true` |

---

## 📂 Project Structure

```
Job-apply-bot/
├── run.py                          # Unified backend + frontend concurrent launcher
├── start.bat / start.ps1           # 1-click launchers for Windows
├── .env.example                    # Environment template
│
├── backend/                        # Python FastAPI Backend
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory & CORS
│   │   ├── core/                   # Database engine, Pydantic settings & JWT auth
│   │   ├── models/                 # SQLAlchemy ORM models (User, Job, Application, Resume)
│   │   ├── schemas/                # Pydantic request / response DTOs
│   │   ├── services/               # State machine, eligibility engine & resume service
│   │   ├── ai/                     # Gemini, Claude, and Local AI providers
│   │   ├── browser/                # Playwright engine, ATS detector & form filler
│   │   └── api/v1/endpoints/       # REST routes (/auth, /jobs, /applications, /resumes)
│   ├── jobs/sources/               # 12+ Specialized job scrapers
│   └── supabase_schema.sql         # Production-ready Supabase schema script
│
└── frontend/                       # Next.js 16 + React 19 Frontend
    ├── app/
    │   ├── (dashboard)/            # Authenticated application shell
    │   │   ├── page.tsx            # Live statistics & analytics chart
    │   │   ├── jobs/page.tsx       # Searchable job feed with match score badges
    │   │   ├── applications/page.tsx # Multi-stage application review queue
    │   │   ├── resumes/page.tsx    # Resume upload & ATS score breakdown
    │   │   └── settings/page.tsx   # Bot automation policies & safety thresholds
    │   ├── login/ & register/      # Glassmorphic authentication routes
    │   └── globals.css             # Dark-theme design tokens & animations
    ├── components/layout/Sidebar.tsx# Navigation sidebar
    └── store/authStore.ts          # Zustand authentication state
```

---

## 🔌 API Endpoints

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/v1/auth/register` | Register candidate account |
| **Auth** | `POST` | `/api/v1/auth/login` | Log in and receive JWT token pair |
| **Auth** | `GET` | `/api/v1/auth/me` | Fetch authenticated user profile |
| **Jobs** | `POST` | `/api/v1/jobs/discover` | Run multi-source scraping job discovery |
| **Jobs** | `GET` | `/api/v1/jobs` | Paginated job list with score & title filters |
| **Jobs** | `GET` | `/api/v1/jobs/stats` | Aggregated discovery analytics |
| **Applications** | `GET` | `/api/v1/applications/queue` | List applications filtered by status |
| **Applications** | `POST` | `/api/v1/applications/{id}/submit`| Execute Playwright browser submission |
| **Applications** | `GET` | `/api/v1/applications/{id}/attempts` | View step logs and error traces |
| **Resumes** | `POST` | `/api/v1/resumes/upload` | Upload & parse PDF/DOCX resume |
| **Resumes** | `POST` | `/api/v1/resumes/{id}/analyze` | Compute AI ATS score & skill extraction |
| **Settings** | `GET` | `/api/v1/settings/auto-apply` | Retrieve current bot automation rules |
| **Settings** | `PUT` | `/api/v1/settings/auto-apply` | Update daily limits & match thresholds |

---

## 🛡️ Anti-Detection & Safety Principles

1. **Dry-Run Test Mode (`AUTO_APPLY_TEST_MODE=true`)**: Activated by default. Navigates pages, fills form inputs, and saves a verification screenshot to `./uploads/screenshots/` without ever clicking the final submit button.
2. **Safe Mode**: Prepares answers, generates tailored cover letters, and queues the application for manual candidate approval.
3. **Randomized Human Jitter**: Employs dynamic typing delays (50–150ms per key) and variable intervals (30–120 seconds) between submissions to prevent IP blocks.
4. **Playwright Stealth**: Strips automated webdriver flags and masks browser fingerprints to navigate ATS portals naturally.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).