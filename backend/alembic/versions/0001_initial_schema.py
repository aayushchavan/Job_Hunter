"""
Alembic migration: 0001_initial_schema

Creates all tables from scratch:
  - users
  - resumes
  - job_sources
  - jobs
  - eligibility_criteria
  - applications
  - application_attempts
  - application_answers
  - auto_apply_settings
  - application_daily_stats

Reversible: down() drops all tables in dependency order.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _is_pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _array_col(name: str):
    """Text array column — ARRAY on PostgreSQL, JSON on SQLite."""
    if _is_pg():
        return sa.Column(name, postgresql.ARRAY(sa.Text()), nullable=True)
    return sa.Column(name, sa.JSON(), nullable=True)


def _json_col(name: str):
    """JSON blob — JSONB on PostgreSQL, JSON on SQLite."""
    if _is_pg():
        return sa.Column(name, postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    return sa.Column(name, sa.JSON(), nullable=True)


def _uuid_col(name: str, **kwargs):
    """UUID column — native UUID on PostgreSQL, CHAR(36) on SQLite."""
    if _is_pg():
        return sa.Column(name, postgresql.UUID(as_uuid=True), **kwargs)
    return sa.Column(name, sa.CHAR(36), **kwargs)


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        _uuid_col("id", primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("zip_code", sa.String(20), nullable=True),
        sa.Column("current_title", sa.String(150), nullable=True),
        sa.Column("current_company", sa.String(150), nullable=True),
        sa.Column("years_of_experience", sa.Integer(), nullable=True),
        sa.Column("headline", sa.String(255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("github_url", sa.String(500), nullable=True),
        sa.Column("portfolio_url", sa.String(500), nullable=True),
        sa.Column("website_url", sa.String(500), nullable=True),
        sa.Column("work_authorization", sa.String(100), nullable=True),
        sa.Column("requires_sponsorship", sa.Boolean(), nullable=True),
        sa.Column("willing_to_relocate", sa.Boolean(), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), nullable=True),
        sa.Column("desired_salary_min", sa.Integer(), nullable=True),
        sa.Column("desired_salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True, server_default="INR"),
        sa.Column("gender", sa.String(50), nullable=True),
        sa.Column("disability_status", sa.String(100), nullable=True),
        sa.Column("veteran_status", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── resumes ────────────────────────────────────────────────────────────────
    op.create_table(
        "resumes",
        _uuid_col("id", primary_key=True),
        _uuid_col("user_id", nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _array_col("domain_tags"),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("parsed_text", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        _array_col("extracted_skills"),
        _array_col("extracted_roles"),
        _json_col("rating_feedback"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_resumes_id", "resumes", ["id"])
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    # ── job_sources ────────────────────────────────────────────────────────────
    op.create_table(
        "job_sources",
        _uuid_col("id", primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", name="uq_job_sources_name"),
    )
    op.create_index("ix_job_sources_id", "job_sources", ["id"])

    # ── jobs ───────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        _uuid_col("id", primary_key=True),
        _uuid_col("source_id", nullable=True),
        sa.Column("source_job_id", sa.String(500), nullable=True),
        sa.Column("source_name", sa.String(100), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("company_name", sa.String(300), nullable=False),
        sa.Column("company_domain", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("location", sa.String(300), nullable=True),
        sa.Column("is_remote", sa.Boolean(), nullable=True),
        sa.Column("is_hybrid", sa.Boolean(), nullable=True),
        sa.Column("work_mode", sa.String(20), nullable=True),
        sa.Column("employment_type", sa.String(100), nullable=True),
        sa.Column("experience_min_years", sa.Integer(), nullable=True),
        sa.Column("experience_max_years", sa.Integer(), nullable=True),
        sa.Column("education_required", sa.String(200), nullable=True),
        sa.Column("graduation_year_required", sa.Integer(), nullable=True),
        sa.Column("domain", sa.String(200), nullable=True),
        _array_col("required_skills"),
        _array_col("preferred_skills"),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True),
        sa.Column("application_url", sa.String(1000), nullable=True),
        sa.Column("canonical_url", sa.String(1000), nullable=True),
        sa.Column("application_method", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("can_submit_automatically", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("greenhouse_job_id", sa.String(200), nullable=True),
        sa.Column("greenhouse_board_token", sa.String(200), nullable=True),
        sa.Column("lever_posting_id", sa.String(200), nullable=True),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("match_explanation", sa.Text(), nullable=True),
        sa.Column("is_eligible", sa.Boolean(), nullable=True),
        sa.Column("eligibility_checked_at", sa.String(50), nullable=True),
        _array_col("ineligibility_reasons"),
        sa.Column("fingerprint", sa.String(64), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),
        _json_col("raw_data"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["job_sources.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("source_job_id", "source_id", name="uq_job_source"),
    )
    op.create_index("ix_jobs_id", "jobs", ["id"])
    op.create_index("ix_jobs_source_id", "jobs", ["source_id"])
    op.create_index("ix_jobs_source_job_id", "jobs", ["source_job_id"])
    op.create_index("ix_jobs_source_name", "jobs", ["source_name"])
    op.create_index("ix_jobs_company_name", "jobs", ["company_name"])
    op.create_index("ix_jobs_canonical_url", "jobs", ["canonical_url"])
    op.create_index("ix_jobs_fingerprint", "jobs", ["fingerprint"], unique=True)
    op.create_index("ix_jobs_source_name_job_id", "jobs", ["source_name", "source_job_id"])

    # ── eligibility_criteria ───────────────────────────────────────────────────
    op.create_table(
        "eligibility_criteria",
        _uuid_col("id", primary_key=True),
        _uuid_col("user_id", nullable=False),
        _array_col("allowed_roles"),
        _array_col("excluded_roles"),
        sa.Column("max_experience_years", sa.Integer(), nullable=True),
        sa.Column("min_education", sa.String(100), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        _array_col("allowed_domains"),
        _array_col("excluded_domains"),
        _array_col("allowed_locations"),
        sa.Column("allow_remote", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("min_salary", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True, server_default="INR"),
        _array_col("allowed_employment_types"),
        _array_col("excluded_companies"),
        _array_col("required_skills"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_eligibility_user"),
    )
    op.create_index("ix_eligibility_criteria_id", "eligibility_criteria", ["id"])

    # ── applications ───────────────────────────────────────────────────────────
    op.create_table(
        "applications",
        _uuid_col("id", primary_key=True),
        _uuid_col("user_id", nullable=False),
        _uuid_col("job_id", nullable=False),
        _uuid_col("resume_id", nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="DISCOVERED"),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("is_eligible", sa.Boolean(), nullable=True),
        _array_col("ineligibility_reasons"),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("match_explanation", sa.Text(), nullable=True),
        sa.Column("match_threshold_used", sa.Integer(), nullable=True),
        sa.Column("application_method", sa.String(100), nullable=True),
        sa.Column("can_submit_automatically", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("application_url", sa.String(1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_id", sa.String(500), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("last_error", sa.Text(), nullable=True),
        _array_col("warnings"),
        sa.Column("requires_user_input", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_input_question", sa.Text(), nullable=True),
        sa.Column("auto_apply_mode", sa.String(20), nullable=True),
        sa.Column("is_test_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("detected_fields", sa.JSON(), nullable=True),
        sa.Column("filled_fields", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),
    )
    op.create_index("ix_applications_id", "applications", ["id"])
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    # ── application_attempts ───────────────────────────────────────────────────
    op.create_table(
        "application_attempts",
        _uuid_col("id", primary_key=True),
        _uuid_col("application_id", nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="STARTED"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fields_detected", sa.Integer(), nullable=True),
        sa.Column("fields_filled", sa.Integer(), nullable=True),
        sa.Column("questions_detected", sa.Integer(), nullable=True),
        sa.Column("questions_answered", sa.Integer(), nullable=True),
        sa.Column("resume_uploaded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("form_validated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("would_submit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_type", sa.String(200), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_stacktrace", sa.Text(), nullable=True),
        sa.Column("step_log", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_application_attempts_id", "application_attempts", ["id"])
    op.create_index("ix_application_attempts_application_id", "application_attempts", ["application_id"])

    # ── application_answers ────────────────────────────────────────────────────
    op.create_table(
        "application_answers",
        _uuid_col("id", primary_key=True),
        _uuid_col("application_id", nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(50), nullable=True),
        _array_col("options"),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False, server_default="claude"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("requires_user_input", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_application_answers_id", "application_answers", ["id"])
    op.create_index("ix_application_answers_application_id", "application_answers", ["application_id"])

    # ── auto_apply_settings ────────────────────────────────────────────────────
    op.create_table(
        "auto_apply_settings",
        _uuid_col("id", primary_key=True),
        _uuid_col("user_id", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mode", sa.String(20), nullable=False, server_default="safe"),
        sa.Column("min_match_score", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("max_applications_per_day", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("delay_min_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("delay_max_seconds", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        _array_col("allowed_roles"),
        _array_col("excluded_domains"),
        _array_col("allowed_locations"),
        sa.Column("min_salary", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True, server_default="INR"),
        sa.Column("require_approval_before_submit", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_test_mode", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_auto_apply_settings_user"),
    )
    op.create_index("ix_auto_apply_settings_id", "auto_apply_settings", ["id"])

    # ── application_daily_stats ────────────────────────────────────────────────
    op.create_table(
        "application_daily_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        _uuid_col("user_id", nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("applications_started", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applications_submitted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applications_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applications_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applications_requiring_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "stat_date", name="uq_daily_stats_user_date"),
    )
    op.create_index("ix_application_daily_stats_user_id", "application_daily_stats", ["user_id"])
    op.create_index("ix_application_daily_stats_stat_date", "application_daily_stats", ["stat_date"])


def downgrade() -> None:
    op.drop_table("application_daily_stats")
    op.drop_table("auto_apply_settings")
    op.drop_table("application_answers")
    op.drop_table("application_attempts")
    op.drop_table("applications")
    op.drop_table("eligibility_criteria")
    op.drop_table("jobs")
    op.drop_table("job_sources")
    op.drop_table("resumes")
    op.drop_table("users")
