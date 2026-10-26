-- ==============================================================================
-- AI Job Hunter — Complete Supabase PostgreSQL Schema
-- ==============================================================================
-- You can run this entire script directly in the Supabase SQL Editor:
-- Supabase Dashboard -> SQL Editor -> New Query -> Paste & Run
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. Drop existing tables if re-initializing (Dependency order)
-- DROP TABLE IF EXISTS application_daily_stats CASCADE;
-- DROP TABLE IF EXISTS auto_apply_settings CASCADE;
-- DROP TABLE IF EXISTS application_answers CASCADE;
-- DROP TABLE IF EXISTS application_attempts CASCADE;
-- DROP TABLE IF EXISTS applications CASCADE;
-- DROP TABLE IF EXISTS eligibility_criteria CASCADE;
-- DROP TABLE IF EXISTS jobs CASCADE;
-- DROP TABLE IF EXISTS job_sources CASCADE;
-- DROP TABLE IF EXISTS resumes CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;

-- ==============================================================================
-- Table: users
-- ==============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(30),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    zip_code VARCHAR(20),
    current_title VARCHAR(150),
    current_company VARCHAR(150),
    years_of_experience INTEGER,
    headline VARCHAR(255),
    summary TEXT,
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    portfolio_url VARCHAR(500),
    website_url VARCHAR(500),
    work_authorization VARCHAR(100),
    requires_sponsorship BOOLEAN,
    willing_to_relocate BOOLEAN,
    notice_period_days INTEGER,
    desired_salary_min INTEGER,
    desired_salary_max INTEGER,
    salary_currency VARCHAR(10) DEFAULT 'INR',
    gender VARCHAR(50),
    disability_status VARCHAR(100),
    veteran_status VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- ==============================================================================
-- Table: resumes
-- ==============================================================================
CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    domain_tags TEXT[],
    file_path VARCHAR(500),
    file_name VARCHAR(255),
    file_size_bytes INTEGER,
    mime_type VARCHAR(100),
    parsed_text TEXT,
    score INTEGER,
    extracted_skills TEXT[],
    extracted_roles TEXT[],
    rating_feedback JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_resumes_id ON resumes (id);
CREATE INDEX IF NOT EXISTS ix_resumes_user_id ON resumes (user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_domain_tags ON resumes USING gin (domain_tags);
CREATE INDEX IF NOT EXISTS idx_resumes_extracted_skills ON resumes USING gin (extracted_skills);

-- ==============================================================================
-- Table: job_sources
-- ==============================================================================
CREATE TABLE IF NOT EXISTS job_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    base_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_job_sources_id ON job_sources (id);

-- Seed default job sources
INSERT INTO job_sources (name, base_url, is_active)
VALUES 
    ('adzuna', 'https://api.adzuna.com', true),
    ('greenhouse', 'https://boards-api.greenhouse.io', true),
    ('lever', 'https://api.lever.co', true),
    ('remoteok', 'https://remoteok.com', true),
    ('weworkremotely', 'https://weworkremotely.com', true)
ON CONFLICT (name) DO NOTHING;

-- ==============================================================================
-- Table: jobs
-- ==============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES job_sources(id) ON DELETE SET NULL,
    source_job_id VARCHAR(500),
    source_name VARCHAR(100),
    title VARCHAR(300) NOT NULL,
    company_name VARCHAR(300) NOT NULL,
    company_domain VARCHAR(200),
    description TEXT,
    requirements TEXT,
    location VARCHAR(300),
    is_remote BOOLEAN,
    is_hybrid BOOLEAN,
    work_mode VARCHAR(20) DEFAULT 'unknown',
    employment_type VARCHAR(100),
    experience_min_years INTEGER,
    experience_max_years INTEGER,
    education_required VARCHAR(200),
    graduation_year_required INTEGER,
    domain VARCHAR(200),
    required_skills TEXT[],
    preferred_skills TEXT[],
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency VARCHAR(10),
    application_url VARCHAR(1000),
    canonical_url VARCHAR(1000),
    application_method VARCHAR(50) NOT NULL DEFAULT 'unknown',
    can_submit_automatically BOOLEAN NOT NULL DEFAULT FALSE,
    greenhouse_job_id VARCHAR(200),
    greenhouse_board_token VARCHAR(200),
    lever_posting_id VARCHAR(200),
    match_score INTEGER,
    match_explanation TEXT,
    is_eligible BOOLEAN,
    eligibility_checked_at VARCHAR(50),
    ineligibility_reasons TEXT[],
    fingerprint VARCHAR(64) UNIQUE,
    posted_at TIMESTAMPTZ,
    discovered_at TIMESTAMPTZ,
    raw_data JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_job_source UNIQUE (source_job_id, source_id)
);

CREATE INDEX IF NOT EXISTS ix_jobs_id ON jobs (id);
CREATE INDEX IF NOT EXISTS ix_jobs_source_id ON jobs (source_id);
CREATE INDEX IF NOT EXISTS ix_jobs_source_job_id ON jobs (source_job_id);
CREATE INDEX IF NOT EXISTS ix_jobs_source_name ON jobs (source_name);
CREATE INDEX IF NOT EXISTS ix_jobs_company_name ON jobs (company_name);
CREATE INDEX IF NOT EXISTS ix_jobs_canonical_url ON jobs (canonical_url);
CREATE INDEX IF NOT EXISTS ix_jobs_fingerprint ON jobs (fingerprint);
CREATE INDEX IF NOT EXISTS ix_jobs_posted_at ON jobs (posted_at DESC);
CREATE INDEX IF NOT EXISTS ix_jobs_match_score ON jobs (match_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_required_skills ON jobs USING gin (required_skills);
CREATE INDEX IF NOT EXISTS idx_jobs_preferred_skills ON jobs USING gin (preferred_skills);
CREATE INDEX IF NOT EXISTS idx_jobs_title_trgm ON jobs USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_company_trgm ON jobs USING gin (company_name gin_trgm_ops);

-- ==============================================================================
-- Table: eligibility_criteria
-- ==============================================================================
CREATE TABLE IF NOT EXISTS eligibility_criteria (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    allowed_roles TEXT[],
    excluded_roles TEXT[],
    max_experience_years INTEGER,
    min_education VARCHAR(100),
    graduation_year INTEGER,
    allowed_domains TEXT[],
    excluded_domains TEXT[],
    allowed_locations TEXT[],
    allow_remote BOOLEAN NOT NULL DEFAULT TRUE,
    min_salary INTEGER,
    salary_currency VARCHAR(10) DEFAULT 'INR',
    allowed_employment_types TEXT[],
    excluded_companies TEXT[],
    required_skills TEXT[],
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_eligibility_criteria_id ON eligibility_criteria (id);
CREATE INDEX IF NOT EXISTS ix_eligibility_criteria_user_id ON eligibility_criteria (user_id);

-- ==============================================================================
-- Table: applications
-- ==============================================================================
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'DISCOVERED',
    status_reason TEXT,
    is_eligible BOOLEAN,
    ineligibility_reasons TEXT[],
    match_score INTEGER,
    match_explanation TEXT,
    match_threshold_used INTEGER,
    application_method VARCHAR(100),
    can_submit_automatically BOOLEAN NOT NULL DEFAULT FALSE,
    application_url VARCHAR(1000),
    started_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    confirmation_id VARCHAR(500),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    last_error TEXT,
    warnings TEXT[],
    requires_user_input BOOLEAN NOT NULL DEFAULT FALSE,
    user_input_question TEXT,
    auto_apply_mode VARCHAR(20),
    is_test_run BOOLEAN NOT NULL DEFAULT FALSE,
    detected_fields JSONB,
    filled_fields JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_application_user_job UNIQUE (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS ix_applications_id ON applications (id);
CREATE INDEX IF NOT EXISTS ix_applications_user_id ON applications (user_id);
CREATE INDEX IF NOT EXISTS ix_applications_job_id ON applications (job_id);
CREATE INDEX IF NOT EXISTS ix_applications_status ON applications (status);
CREATE INDEX IF NOT EXISTS ix_applications_user_status ON applications (user_id, status);

-- ==============================================================================
-- Table: application_attempts
-- ==============================================================================
CREATE TABLE IF NOT EXISTS application_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'STARTED',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    fields_detected INTEGER,
    fields_filled INTEGER,
    questions_detected INTEGER,
    questions_answered INTEGER,
    resume_uploaded BOOLEAN NOT NULL DEFAULT FALSE,
    form_validated BOOLEAN NOT NULL DEFAULT FALSE,
    would_submit BOOLEAN NOT NULL DEFAULT FALSE,
    error_type VARCHAR(200),
    error_message TEXT,
    error_stacktrace TEXT,
    step_log JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_application_attempts_id ON application_attempts (id);
CREATE INDEX IF NOT EXISTS ix_application_attempts_application_id ON application_attempts (application_id);

-- ==============================================================================
-- Table: application_answers
-- ==============================================================================
CREATE TABLE IF NOT EXISTS application_answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50),
    options TEXT[],
    answer TEXT,
    source VARCHAR(30) NOT NULL DEFAULT 'claude',
    confidence NUMERIC(4, 3),
    requires_user_input BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_application_answers_id ON application_answers (id);
CREATE INDEX IF NOT EXISTS ix_application_answers_application_id ON application_answers (application_id);

-- ==============================================================================
-- Table: auto_apply_settings
-- ==============================================================================
CREATE TABLE IF NOT EXISTS auto_apply_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mode VARCHAR(20) NOT NULL DEFAULT 'safe',
    min_match_score INTEGER NOT NULL DEFAULT 90,
    max_applications_per_day INTEGER NOT NULL DEFAULT 10,
    delay_min_seconds INTEGER NOT NULL DEFAULT 30,
    delay_max_seconds INTEGER NOT NULL DEFAULT 120,
    max_retries INTEGER NOT NULL DEFAULT 3,
    allowed_roles TEXT[],
    excluded_domains TEXT[],
    allowed_locations TEXT[],
    min_salary INTEGER,
    salary_currency VARCHAR(10) DEFAULT 'INR',
    require_approval_before_submit BOOLEAN NOT NULL DEFAULT TRUE,
    is_test_mode BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_auto_apply_settings_id ON auto_apply_settings (id);
CREATE INDEX IF NOT EXISTS ix_auto_apply_settings_user_id ON auto_apply_settings (user_id);

-- ==============================================================================
-- Table: application_daily_stats
-- ==============================================================================
CREATE TABLE IF NOT EXISTS application_daily_stats (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stat_date DATE NOT NULL,
    applications_started INTEGER NOT NULL DEFAULT 0,
    applications_submitted INTEGER NOT NULL DEFAULT 0,
    applications_failed INTEGER NOT NULL DEFAULT 0,
    applications_rejected INTEGER NOT NULL DEFAULT 0,
    applications_requiring_input INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_stats_user_date UNIQUE (user_id, stat_date)
);

CREATE INDEX IF NOT EXISTS ix_application_daily_stats_user_id ON application_daily_stats (user_id);
CREATE INDEX IF NOT EXISTS ix_application_daily_stats_stat_date ON application_daily_stats (stat_date);

-- ==============================================================================
-- Optional: Auto-update updated_at timestamp trigger function
-- ==============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE column_name = 'updated_at' 
          AND table_schema = 'public'
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS trg_update_timestamp ON %I;
            CREATE TRIGGER trg_update_timestamp
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        ', t, t);
    END LOOP;
END;
$$;
