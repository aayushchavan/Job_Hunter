"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationsApi } from "@/lib/api";
import { useToast } from "@/components/ui/ToastProvider";
import {
  SendHorizontal,
  RefreshCw,
  X,
  Play,
  Upload,
  Eye,
  Loader2,
  ChevronRight,
  Building2,
  Clock,
  ExternalLink,
  Globe,
  Copy,
  Check,
  FileText,
  Sparkles,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { getMatchColor, getStatusColor, formatRelativeTime, formatDate } from "@/lib/utils";

type StatusFilter = "all" | "queued" | "preparing" | "ready" | "submitted" | "failed" | "cancelled";

interface Application {
  id: string;
  job_id?: string;
  job_title?: string;
  company?: string;
  company_name?: string;
  status: string;
  match_score?: number;
  created_at: string;
  updated_at?: string;
  job_url?: string;
  application_url?: string;
}

interface ReviewAnswerItem {
  id?: string;
  question_text?: string;
  question?: string;
  question_type?: string;
  options?: string[];
  answer?: string;
  source?: string;
  confidence?: number;
  requires_user_input?: boolean;
}

interface ReviewData {
  application_id?: string;
  job_id?: string;
  company_name?: string;
  job_title?: string;
  match_score?: number;
  resume_name?: string;
  application_method?: string;
  application_url?: string;
  job_url?: string;
  status?: string;
  cover_letter?: string;
  job_description?: string;
  answers?: ReviewAnswerItem[] | Record<string, string>;
  warnings?: string[];
  detected_fields?: Record<string, any>;
  filled_fields?: Record<string, any>;
  can_submit_automatically?: boolean;
  is_test_run?: boolean;
}

const STATUS_TABS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "queued", label: "Queued" },
  { key: "preparing", label: "Preparing" },
  { key: "ready", label: "Ready" },
  { key: "submitted", label: "Submitted" },
  { key: "failed", label: "Failed" },
  { key: "cancelled", label: "Cancelled" },
];

export default function ApplicationsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [reviewData, setReviewData] = useState<ReviewData | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [copiedLetter, setCopiedLetter] = useState(false);
  const [copiedAnswers, setCopiedAnswers] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["applications", statusFilter],
    queryFn: () =>
      applicationsApi
        .queue({ status: statusFilter === "all" ? undefined : statusFilter, limit: 50 })
        .then((r) => r.data),
    refetchInterval: 10000,
  });

  const { data: statsData } = useQuery({
    queryKey: ["app-stats"],
    queryFn: () => applicationsApi.stats().then((r) => r.data),
  });

  const prepareMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.prepare(id),
    onSuccess: () => {
      toast("Preparation started! AI is working... 🤖", "info");
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || "Failed to prepare application";
      toast(msg, "error");
    },
  });

  const submitMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.submit(id),
    onSuccess: () => {
      toast("Application submitted! ✅", "success");
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: () => toast("Failed to submit application", "error"),
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.retry(id),
    onSuccess: () => {
      toast("Retrying application...", "info");
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: () => toast("Retry failed", "error"),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.cancel(id),
    onSuccess: () => {
      toast("Application cancelled", "warning");
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || "Cancel failed";
      toast(msg, "error");
    },
  });

  const openReview = async (app: Application) => {
    setSelectedApp(app);
    setReviewLoading(true);
    try {
      const res = await applicationsApi.review(app.id);
      setReviewData(res.data);
    } catch (err) {
      console.error("Failed to load review details:", err);
      setReviewData({
        application_id: app.id,
        job_id: app.job_id,
        company_name: app.company_name || app.company,
        job_title: app.job_title,
        application_url: app.application_url || app.job_url,
        job_url: app.application_url || app.job_url,
        status: app.status,
      });
    } finally {
      setReviewLoading(false);
    }
  };

  const copyToClipboard = (text: string, type: "letter" | "answers") => {
    navigator.clipboard.writeText(text);
    if (type === "letter") {
      setCopiedLetter(true);
      setTimeout(() => setCopiedLetter(false), 2000);
    } else {
      setCopiedAnswers(true);
      setTimeout(() => setCopiedAnswers(false), 2000);
    }
    toast("Copied to clipboard! 📋", "success");
  };

  const apps: Application[] = Array.isArray(data) ? data : data?.applications ?? data?.queue ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "white", marginBottom: "4px" }}>
            Application Queue
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Manage and track all your job applications
          </p>
        </div>
        <button
          className="btn-secondary"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["applications"] })}
          style={{ fontSize: "13px" }}
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Stats Bar */}
      {statsData && (
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          {[
            { key: "queued", label: "Queued", color: "#94a3b8" },
            { key: "preparing", label: "Preparing", color: "#60a5fa" },
            { key: "ready", label: "Ready", color: "#a78bfa" },
            { key: "submitted", label: "Submitted", color: "#34d399" },
            { key: "failed", label: "Failed", color: "#f87171" },
          ].map(({ key, label, color }) => (
            <div
              key={key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                borderRadius: "8px",
                background: `${color}10`,
                border: `1px solid ${color}20`,
              }}
            >
              <span style={{ fontSize: "16px", fontWeight: 800, color }}>{(statsData as Record<string, number>)[key] ?? 0}</span>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>{label}</span>
            </div>
          ))}
        </div>
      )}

      {/* Status Tabs */}
      <div
        style={{
          display: "flex",
          gap: "4px",
          background: "rgba(255,255,255,0.04)",
          padding: "4px",
          borderRadius: "10px",
          width: "fit-content",
        }}
      >
        {STATUS_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setStatusFilter(key)}
            style={{
              padding: "7px 14px",
              borderRadius: "7px",
              border: "none",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "12px",
              transition: "all 0.2s",
              background: statusFilter === key ? "linear-gradient(135deg, #6366f1, #8b5cf6)" : "transparent",
              color: statusFilter === key ? "white" : "var(--text-muted)",
              fontFamily: "inherit",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Applications List */}
      {isLoading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="skeleton" style={{ height: "80px", borderRadius: "12px" }} />
          ))}
        </div>
      ) : apps.length === 0 ? (
        <div className="glass-card" style={{ textAlign: "center", padding: "60px 32px" }}>
          <SendHorizontal size={48} style={{ margin: "0 auto 16px", opacity: 0.2 }} />
          <h3 style={{ fontSize: "18px", fontWeight: 700, color: "white", marginBottom: "8px" }}>No applications found</h3>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Discover jobs and add them to your queue to get started
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {apps.map((app) => {
            const norm = (app.status || "").toLowerCase();
            const canPrepare = norm === "queued" || norm === "discovered" || norm === "matched";
            const canSubmit = norm === "ready" || norm === "review";
            const canRetry = norm === "failed";
            const canCancel = ["queued", "preparing", "ready", "review", "discovered", "matched"].includes(norm);

            return (
            <div
              key={app.id}
              className="glass-card"
              style={{ padding: "16px 20px", display: "flex", alignItems: "center", gap: "16px" }}
            >
              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                  <span style={{ fontSize: "15px", fontWeight: 700, color: "white" }}>
                    {app.job_title ?? "Job Application"}
                  </span>
                  <span className={`badge ${getStatusColor(app.status)}`}>
                    {app.status}
                  </span>
                  {app.match_score !== undefined && (
                    <span className={`badge ${getMatchColor(app.match_score)}`}>
                      {Math.round(app.match_score)}% match
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", gap: "14px", color: "var(--text-muted)", fontSize: "12px" }}>
                  {(app.company_name || app.company) && (
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <Building2 size={11} /> {app.company_name || app.company}
                    </span>
                  )}
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Clock size={11} /> {formatDate(app.created_at)}
                  </span>
                  <span style={{ color: "var(--text-muted)" }}>Updated {formatRelativeTime(app.updated_at || app.created_at)}</span>
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: "8px", flexShrink: 0, alignItems: "center" }}>
                {/* External Job / Company Website */}
                {(app.application_url || app.job_url) && (
                  <a
                    href={app.application_url || app.job_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary"
                    style={{ fontSize: "12px", padding: "6px 12px", display: "inline-flex", alignItems: "center", gap: "5px" }}
                    title="Open Company Apply Website"
                  >
                    <ExternalLink size={13} />
                    Company Site
                  </a>
                )}

                {/* Review */}
                <button
                  className="btn-secondary"
                  onClick={() => openReview(app)}
                  style={{ fontSize: "12px", padding: "6px 12px" }}
                  title="View AI review & Auto-Apply details"
                >
                  <Eye size={13} />
                  Review
                </button>

                {/* Prepare */}
                {canPrepare && (
                  <button
                    className="btn-secondary"
                    onClick={() => prepareMutation.mutate(app.id)}
                    disabled={prepareMutation.isPending}
                    style={{ fontSize: "12px", padding: "6px 12px" }}
                    title="Prepare with AI"
                  >
                    {prepareMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                    Prepare
                  </button>
                )}

                {/* Submit */}
                {canSubmit && (
                  <button
                    className="btn-primary"
                    onClick={() => submitMutation.mutate(app.id)}
                    disabled={submitMutation.isPending}
                    style={{ fontSize: "12px", padding: "6px 14px" }}
                  >
                    {submitMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
                    Submit
                  </button>
                )}

                {/* Retry */}
                {canRetry && (
                  <button
                    className="btn-secondary"
                    onClick={() => retryMutation.mutate(app.id)}
                    disabled={retryMutation.isPending}
                    style={{ fontSize: "12px", padding: "6px 12px" }}
                  >
                    <RefreshCw size={13} />
                    Retry
                  </button>
                )}

                {/* Cancel */}
                {canCancel && (
                  <button
                    className="btn-danger"
                    onClick={() => cancelMutation.mutate(app.id)}
                    disabled={cancelMutation.isPending}
                    style={{ fontSize: "12px", padding: "6px 12px" }}
                  >
                    <X size={13} />
                  </button>
                )}

                <button
                  onClick={() => openReview(app)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
            );
          })}
        </div>
      )}

      {/* Review Drawer / Modal */}
      {selectedApp && (() => {
        const applyUrl =
          selectedApp.application_url ||
          selectedApp.job_url ||
          reviewData?.application_url ||
          reviewData?.job_url;

        const normStatus = (selectedApp.status || "").toLowerCase();
        const canPrepareModal = normStatus === "queued" || normStatus === "discovered" || normStatus === "matched" || normStatus === "failed";
        const canSubmitModal = normStatus === "ready" || normStatus === "review";
        const canRetryModal = normStatus === "failed";

        // Parse answers from either array or dictionary
        const answersList: { question: string; answer: string; source?: string }[] = Array.isArray(reviewData?.answers)
          ? reviewData.answers.map((a: any) => ({
              question: a.question_text || a.question || "Application Question",
              answer: a.answer || (a.requires_user_input ? "Requires user input" : "Answer generated"),
              source: a.source,
            }))
          : reviewData?.answers
          ? Object.entries(reviewData.answers).map(([q, a]) => ({
              question: q,
              answer: typeof a === "string" ? a : JSON.stringify(a),
              source: "AI",
            }))
          : [];

        return (
          <div className="modal-overlay" onClick={() => setSelectedApp(null)}>
            <div
              className="glass-card"
              onClick={(e) => e.stopPropagation()}
              style={{
                width: "100%",
                maxWidth: "680px",
                maxHeight: "85vh",
                overflowY: "auto",
                padding: "28px",
                margin: "20px",
                display: "flex",
                flexDirection: "column",
                gap: "20px",
              }}
            >
              {/* Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                    <h2 style={{ fontSize: "20px", fontWeight: 800, color: "white", margin: 0 }}>
                      Application Review & Auto-Apply
                    </h2>
                    <span className={`badge ${getStatusColor(selectedApp.status)}`}>
                      {selectedApp.status.toUpperCase()}
                    </span>
                    {selectedApp.match_score !== undefined && (
                      <span className={`badge ${getMatchColor(selectedApp.match_score)}`}>
                        {Math.round(selectedApp.match_score)}% Match
                      </span>
                    )}
                  </div>
                  <p style={{ color: "var(--text-muted)", fontSize: "13px", margin: 0 }}>
                    {selectedApp.job_title} at <strong style={{ color: "#c7d2fe" }}>{selectedApp.company_name || selectedApp.company || "Company"}</strong>
                  </p>
                </div>
                <button
                  onClick={() => setSelectedApp(null)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
                >
                  <X size={20} />
                </button>
              </div>

              {/* 🌐 Company Apply Website Banner */}
              {applyUrl ? (
                <div
                  style={{
                    background: "linear-gradient(135deg, rgba(99,102,241,0.16) 0%, rgba(16,185,129,0.1) 100%)",
                    border: "1px solid rgba(99,102,241,0.35)",
                    borderRadius: "14px",
                    padding: "16px 20px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: "14px",
                  }}
                >
                  <div style={{ flex: 1, minWidth: "260px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "#818cf8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Globe size={13} /> Official Company Job Application Website
                    </div>
                    <div style={{ fontSize: "13px", color: "white", fontWeight: 600, wordBreak: "break-all" }}>
                      {applyUrl}
                    </div>
                  </div>
                  <a
                    href={applyUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-primary"
                    style={{ fontSize: "13px", padding: "8px 18px", display: "inline-flex", alignItems: "center", gap: "6px", whiteSpace: "nowrap" }}
                  >
                    <ExternalLink size={14} /> Open Company Site
                  </a>
                </div>
              ) : (
                <div style={{ padding: "12px 16px", borderRadius: "10px", background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)", fontSize: "12px", color: "var(--text-muted)" }}>
                  Company application link is routed directly through the automated ATS pipeline.
                </div>
              )}

              {/* ⚡ Auto-Apply Execution Controls */}
              <div
                style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid var(--border)",
                  borderRadius: "14px",
                  padding: "16px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: "14px",
                }}
              >
                <div>
                  <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "2px" }}>
                    Pipeline Automation Status
                  </div>
                  <div style={{ fontSize: "13px", color: "white", fontWeight: 600 }}>
                    {canSubmitModal ? (
                      <span style={{ color: "#6ee7b7" }}>Form details ready — click Submit to apply!</span>
                    ) : canPrepareModal ? (
                      <span style={{ color: "#93c5fd" }}>Ready to auto-fill fields & generate AI answers</span>
                    ) : normStatus === "submitted" ? (
                      <span style={{ color: "#34d399" }}>Application successfully submitted!</span>
                    ) : (
                      <span>Current status: {selectedApp.status}</span>
                    )}
                  </div>
                </div>

                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  {canPrepareModal && (
                    <button
                      className="btn-primary"
                      onClick={() => prepareMutation.mutate(selectedApp.id)}
                      disabled={prepareMutation.isPending}
                      style={{ fontSize: "13px", padding: "8px 16px" }}
                    >
                      {prepareMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                      Auto-Fill & Prepare with AI
                    </button>
                  )}

                  {canSubmitModal && (
                    <button
                      className="btn-primary"
                      onClick={() => submitMutation.mutate(selectedApp.id)}
                      disabled={submitMutation.isPending}
                      style={{ fontSize: "13px", padding: "8px 18px", background: "linear-gradient(135deg, #10b981 0%, #059669 100%)" }}
                    >
                      {submitMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                      Submit Application Now
                    </button>
                  )}

                  {canRetryModal && (
                    <button
                      className="btn-secondary"
                      onClick={() => retryMutation.mutate(selectedApp.id)}
                      disabled={retryMutation.isPending}
                      style={{ fontSize: "13px", padding: "8px 14px" }}
                    >
                      <RefreshCw size={14} /> Retry Application
                    </button>
                  )}
                </div>
              </div>

              {/* Review Body */}
              {reviewLoading ? (
                <div style={{ textAlign: "center", padding: "40px 20px" }}>
                  <Loader2 size={32} className="animate-spin" style={{ margin: "0 auto 12px", color: "#818cf8" }} />
                  <p style={{ fontSize: "14px", color: "var(--text-muted)", margin: 0 }}>
                    Loading AI review data and answers...
                  </p>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                  {/* AI Cover Letter */}
                  {reviewData?.cover_letter && (
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0, display: "flex", alignItems: "center", gap: "6px" }}>
                          <FileText size={13} color="#818cf8" /> AI Targeted Cover Letter
                        </h3>
                        <button
                          className="btn-secondary"
                          onClick={() => copyToClipboard(reviewData.cover_letter || "", "letter")}
                          style={{ fontSize: "11px", padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: "4px" }}
                        >
                          {copiedLetter ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                          {copiedLetter ? "Copied!" : "Copy Letter"}
                        </button>
                      </div>
                      <div
                        style={{
                          background: "rgba(99,102,241,0.06)",
                          border: "1px solid rgba(99,102,241,0.2)",
                          borderRadius: "12px",
                          padding: "16px",
                          fontSize: "13px",
                          color: "var(--text-primary)",
                          lineHeight: 1.7,
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {reviewData.cover_letter}
                      </div>
                    </div>
                  )}

                  {/* AI Answers / Custom Questions */}
                  {answersList.length > 0 && (
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <h3 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0, display: "flex", alignItems: "center", gap: "6px" }}>
                          <Sparkles size={13} color="#34d399" /> AI Form Responses ({answersList.length})
                        </h3>
                        <button
                          className="btn-secondary"
                          onClick={() => {
                            const fullText = answersList.map((a) => `Q: ${a.question}\nA: ${a.answer}`).join("\n\n");
                            copyToClipboard(fullText, "answers");
                          }}
                          style={{ fontSize: "11px", padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: "4px" }}
                        >
                          {copiedAnswers ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                          {copiedAnswers ? "Copied All!" : "Copy All Responses"}
                        </button>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                        {answersList.map((item, idx) => (
                          <div
                            key={idx}
                            style={{
                              background: "rgba(255,255,255,0.03)",
                              border: "1px solid var(--border)",
                              borderRadius: "10px",
                              padding: "12px 14px",
                            }}
                          >
                            <div style={{ fontSize: "12px", fontWeight: 700, color: "#cbd5e1", marginBottom: "4px" }}>
                              {item.question}
                            </div>
                            <div style={{ fontSize: "13px", color: "white", lineHeight: 1.5 }}>
                              {item.answer}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* If no cover letter and no answers yet */}
                  {!reviewData?.cover_letter && answersList.length === 0 && (
                    <div
                      style={{
                        textAlign: "center",
                        padding: "32px 20px",
                        background: "rgba(255,255,255,0.02)",
                        border: "1px dashed var(--border)",
                        borderRadius: "14px",
                      }}
                    >
                      <Sparkles size={28} color="#818cf8" style={{ margin: "0 auto 10px" }} />
                      <h4 style={{ fontSize: "15px", fontWeight: 700, color: "white", marginBottom: "6px" }}>
                        Application Ready for Preparation
                      </h4>
                      <p style={{ fontSize: "13px", color: "var(--text-muted)", maxWidth: "460px", margin: "0 auto 16px", lineHeight: 1.5 }}>
                        Click below to launch automated form detection, generate tailored AI answers, and prepare this application for submission. Or visit the company website to apply directly.
                      </p>
                      <div style={{ display: "flex", gap: "10px", justifyContent: "center", flexWrap: "wrap" }}>
                        <button
                          className="btn-primary"
                          onClick={() => prepareMutation.mutate(selectedApp.id)}
                          disabled={prepareMutation.isPending}
                        >
                          {prepareMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                          Auto-Fill & Prepare with AI
                        </button>
                        {applyUrl && (
                          <a href={applyUrl} target="_blank" rel="noreferrer" className="btn-secondary">
                            <ExternalLink size={14} /> Apply on Company Website
                          </a>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Modal Footer */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  borderTop: "1px solid rgba(255,255,255,0.08)",
                  paddingTop: "16px",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                {applyUrl ? (
                  <a
                    href={applyUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary"
                    style={{ fontSize: "13px", padding: "7px 14px" }}
                  >
                    <ExternalLink size={13} /> Open Company Website
                  </a>
                ) : <span />}

                <button className="btn-secondary" onClick={() => setSelectedApp(null)} style={{ fontSize: "13px" }}>
                  Close
                </button>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
