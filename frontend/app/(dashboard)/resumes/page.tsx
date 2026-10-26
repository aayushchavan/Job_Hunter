"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { resumesApi } from "@/lib/api";
import { useToast } from "@/components/ui/ToastProvider";
import {
  FileText,
  Upload,
  Trash2,
  Star,
  StarOff,
  Loader2,
  Plus,
  CheckCircle,
  Sparkles,
  Zap,
  Search,
  Briefcase,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Award,
  Check,
  Lightbulb,
  X,
  Target,
  ArrowRight,
  UserCheck,
  AlertTriangle,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Info,
  Sliders,
  RefreshCw,
  MapPin,
  Download,
  Copy,
  Printer,
  FileDown,
  FileCheck,
  Code2,
  Server,
  Layout,
  Database,
  Cloud,
  Cpu,
  Layers,
  TrendingUp,
} from "lucide-react";
import { formatDate } from "@/lib/utils";

interface RatingFeedback {
  summary?: string;
  ats_score?: number;
  strengths?: string[];
  weaknesses?: string[];
  suggestions?: string[];
  experience_years?: number;
}

interface Resume {
  id: string;
  name: string;
  is_primary?: boolean;
  is_default?: boolean;
  file_path?: string;
  file_name?: string;
  file_size_bytes?: number;
  created_at: string;
  skills?: string[];
  score?: number;
  extracted_skills?: string[];
  extracted_roles?: string[];
  rating_feedback?: RatingFeedback;
}

interface ChecklistField {
  key: string;
  label: string;
  category: string;
  required: boolean;
  importance: "critical" | "optional";
  value: any;
  status: "filled" | "missing";
  source?: string;
  reason: string;
}

interface RequirementsChecklist {
  all_required_met: boolean;
  total_required: number;
  filled_required: number;
  missing_required_fields: string[];
  completion_percentage: number;
  fields: ChecklistField[];
  notice: string;
}

interface AutoPilotModalState {
  type: "autoPilot" | "findJobs";
  resumeId: string;
  resumeName: string;
  status: "running" | "done" | "error";
  data?: any;
  errorMessage?: string;
}

interface RequirementsModalState {
  resumeId: string;
  resumeName: string;
  checklist?: RequirementsChecklist;
  yearsOfExperience?: number;
  isLoading?: boolean;
}

interface CategoryScore {
  key: string;
  label: string;
  score: number;
  status: "strong" | "moderate" | "weak" | "critical";
  findings: string;
  recommendation: string;
}

interface CriticalAlert {
  type: "critical" | "warning" | "error" | "info";
  title: string;
  detail: string;
  fix: string;
}

interface RewriteItem {
  section: string;
  original: string;
  improved: string;
  rationale: string;
}

interface RoadmapItem {
  timeframe: string;
  priority: string;
  task: string;
}

interface TechItem {
  keyword: string;
  name: string;
  tier: string;
  demand: string;
  modern_equivalent: string;
  status: string;
}

interface TechDomain {
  key: string;
  label: string;
  icon?: string;
  score: number;
  status: "strong" | "moderate" | "needs_upgrade";
  detected: TechItem[];
  trends_2026: string[];
  upgrade_advice: string;
}

interface MissingTechItem {
  name: string;
  domain: string;
  demand: string;
}

interface LegacyWarningItem {
  current: string;
  improved: string;
  reason: string;
}

interface TechnologyAnalysis {
  modern_stack_score: number;
  total_detected_count: number;
  domains: TechDomain[];
  all_detected_names: string[];
  missing_high_impact: MissingTechItem[];
  legacy_warnings: LegacyWarningItem[];
}

interface AuditReportData {
  resume_id: string;
  resume_name: string;
  candidate_name: string;
  overall_ats_score: number;
  overall_quality_score: number;
  category_scores: CategoryScore[];
  critical_alerts: CriticalAlert[];
  detected_skills: string[];
  technology_analysis?: TechnologyAnalysis;
  rewrites: RewriteItem[];
  roadmap: RoadmapItem[];
  markdown_report: string;
}

interface AuditReportModalState {
  resumeId: string;
  resumeName: string;
  isLoading: boolean;
  data?: AuditReportData;
}

const getDomainIcon = (key: string) => {
  switch (key) {
    case "languages":
      return <Code2 size={16} color="#818cf8" />;
    case "backend_api":
      return <Server size={16} color="#38bdf8" />;
    case "frontend_ui":
      return <Layout size={16} color="#a78bfa" />;
    case "databases_caching":
      return <Database size={16} color="#34d399" />;
    case "devops_cloud":
      return <Cloud size={16} color="#fbbf24" />;
    case "ai_intelligent_systems":
      return <Cpu size={16} color="#f472b6" />;
    default:
      return <Layers size={16} color="#818cf8" />;
  }
};

export default function ResumesPage() {
  const [dragging, setDragging] = useState(false);
  const [newName, setNewName] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [uploadingFor, setUploadingFor] = useState<string | null>(null);
  const [expandedFeedback, setExpandedFeedback] = useState<Record<string, boolean>>({});
  const [modalState, setModalState] = useState<AutoPilotModalState | null>(null);
  const [requirementsModal, setRequirementsModal] = useState<RequirementsModalState | null>(null);
  const [auditReportModal, setAuditReportModal] = useState<AuditReportModalState | null>(null);
  const [auditActiveTab, setAuditActiveTab] = useState<"overview" | "tech" | "alerts" | "rewrites" | "roadmap" | "markdown">("overview");
  const [globalExperienceCriteria, setGlobalExperienceCriteria] = useState<number>(3);
  const [targetLocation, setTargetLocation] = useState<string>("Remote");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Load resumes
  const { data, isLoading } = useQuery({
    queryKey: ["resumes"],
    queryFn: () => resumesApi.list().then((r) => r.data),
  });

  const resumes: Resume[] = Array.isArray(data) ? data : data?.resumes ?? [];

  // Update experience criteria when primary resume loads
  useEffect(() => {
    if (resumes.length > 0) {
      const primary = resumes.find((r) => r.is_primary || r.is_default) || resumes[0];
      if (primary?.rating_feedback?.experience_years) {
        setGlobalExperienceCriteria(primary.rating_feedback.experience_years);
      }
    }
  }, [resumes]);

  const createMutation = useMutation({
    mutationFn: (name: string) => resumesApi.create({ name }),
    onSuccess: () => {
      toast("Resume record created!", "success");
      setNewName("");
      setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
    onError: () => toast("Failed to create resume", "error"),
  });

  const uploadMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => resumesApi.upload(id, file),
    onSuccess: (res) => {
      const resumeData = res.data;
      if (resumeData?.score) {
        toast(`Resume parsed & rated: ${resumeData.score}/100! 🎯`, "success");
      } else {
        toast("File uploaded & profile autofilled! 📄", "success");
      }
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      setUploadingFor(null);
    },
    onError: () => toast("Upload failed. Check file type (PDF/DOCX)", "error"),
  });

  const analyzeMutation = useMutation({
    mutationFn: (id: string) => resumesApi.analyze(id),
    onSuccess: (res) => {
      const score = res.data?.score;
      toast(`AI Analysis complete! Score: ${score ?? "Evaluated"}/100 🚀`, "success");
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
    onError: () => toast("Analysis failed. Please try again.", "error"),
  });

  const autofillMutation = useMutation({
    mutationFn: ({ id, overwrite }: { id: string; overwrite: boolean }) =>
      resumesApi.autofill(id, overwrite),
    onSuccess: (res) => {
      const updatedCount = res.data?.updated_fields?.length || 0;
      toast(`Autofilled ${updatedCount} profile fields from resume! ✨`, "success");
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      if (res.data?.years_of_experience) {
        setGlobalExperienceCriteria(res.data.years_of_experience);
      }
      if (requirementsModal && requirementsModal.resumeId === res.data?.checklist?.fields?.[0]?.source) {
        setRequirementsModal((prev) =>
          prev ? { ...prev, checklist: res.data.checklist, yearsOfExperience: res.data.years_of_experience } : null
        );
      } else if (requirementsModal) {
        setRequirementsModal((prev) =>
          prev ? { ...prev, checklist: res.data.checklist, yearsOfExperience: res.data.years_of_experience } : null
        );
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || "Autofill failed";
      toast(msg, "error");
    },
  });

  const autoPilotMutation = useMutation({
    mutationFn: ({ id, expYears, location }: { id: string; expYears?: number; location?: string }) =>
      resumesApi.autoPilot(id, expYears, location),
    onSuccess: (res) => {
      setModalState((prev) =>
        prev
          ? {
              ...prev,
              status: "done",
              data: res.data,
            }
          : null
      );
      toast("Auto-Pilot completed successfully! 🚀", "success");
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || "Auto-pilot encountered an error";
      setModalState((prev) =>
        prev
          ? {
              ...prev,
              status: "error",
              errorMessage: msg,
            }
          : null
      );
      toast(msg, "error");
    },
  });

  const findJobsMutation = useMutation({
    mutationFn: ({ id, expYears, location }: { id: string; expYears?: number; location?: string }) =>
      resumesApi.findJobs(id, 15, expYears, location),
    onSuccess: (res) => {
      setModalState((prev) =>
        prev
          ? {
              ...prev,
              status: "done",
              data: res.data,
            }
          : null
      );
      toast(
        `Found ${res.data?.jobs?.length || 0} matching jobs (${targetLocation || "Any Location"}, ${globalExperienceCriteria} yrs exp)!`,
        "success"
      );
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || "Failed to search jobs";
      setModalState((prev) =>
        prev
          ? {
              ...prev,
              status: "error",
              errorMessage: msg,
            }
          : null
      );
      toast(msg, "error");
    },
  });

  const setPrimaryMutation = useMutation({
    mutationFn: (id: string) => resumesApi.update(id, { is_primary: true, is_default: true }),
    onSuccess: () => {
      toast("Active resume updated ✅", "success");
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
    onError: () => toast("Failed to update", "error"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => resumesApi.delete(id),
    onSuccess: () => {
      toast("Resume deleted", "warning");
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
    onError: () => toast("Failed to delete", "error"),
  });

  const handleFileUpload = (id: string, file: File) => {
    if (!file.name.match(/\.(pdf|docx?)$/i)) {
      toast("Only PDF or DOCX files allowed", "error");
      return;
    }
    uploadMutation.mutate({ id, file });
  };

  const handleDrop = (e: React.DragEvent, resumeId: string) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(resumeId, file);
  };

  const toggleFeedback = (id: string) => {
    setExpandedFeedback((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleRunAutoPilot = (resume: Resume) => {
    setModalState({
      type: "autoPilot",
      resumeId: resume.id,
      resumeName: resume.name,
      status: "running",
    });
    autoPilotMutation.mutate({ id: resume.id, expYears: globalExperienceCriteria, location: targetLocation });
  };

  const handleFindJobs = (resume: Resume) => {
    setModalState({
      type: "findJobs",
      resumeId: resume.id,
      resumeName: resume.name,
      status: "running",
    });
    findJobsMutation.mutate({ id: resume.id, expYears: globalExperienceCriteria, location: targetLocation });
  };

  const handleOpenRequirements = async (resume: Resume) => {
    setRequirementsModal({
      resumeId: resume.id,
      resumeName: resume.name,
      isLoading: true,
    });
    try {
      const res = await resumesApi.requirements(resume.id);
      setRequirementsModal({
        resumeId: resume.id,
        resumeName: resume.name,
        checklist: res.data?.checklist,
        yearsOfExperience: res.data?.years_of_experience ?? globalExperienceCriteria,
        isLoading: false,
      });
      if (res.data?.years_of_experience) {
        setGlobalExperienceCriteria(res.data.years_of_experience);
      }
    } catch (err) {
      toast("Could not load requirements checklist", "error");
      setRequirementsModal(null);
    }
  };

  const handleOpenAuditReport = async (resume: Resume) => {
    setAuditReportModal({
      resumeId: resume.id,
      resumeName: resume.name,
      isLoading: true,
    });
    setAuditActiveTab("overview");
    try {
      const res = await resumesApi.getAuditReport(resume.id);
      setAuditReportModal({
        resumeId: resume.id,
        resumeName: resume.name,
        isLoading: false,
        data: res.data,
      });
    } catch (err: any) {
      toast("Could not load ATS audit report", "error");
      setAuditReportModal(null);
    }
  };

  const handleDownloadAuditReport = async (format: "markdown" | "text" = "markdown") => {
    if (!auditReportModal?.data) return;
    try {
      const res = await resumesApi.downloadAuditReport(auditReportModal.resumeId, format);
      const blob = new Blob([res.data], { type: format === "markdown" ? "text/markdown" : "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const cleanName = auditReportModal.resumeName.replace(/[^\w\-_\.]/g, "_");
      link.download = `${cleanName}_ATS_Audit_Report.${format === "markdown" ? "md" : "txt"}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast(`Report downloaded as .${format === "markdown" ? "md" : "txt"}! 📄`, "success");
    } catch (err) {
      if (auditReportModal.data.markdown_report) {
        const blob = new Blob([auditReportModal.data.markdown_report], { type: "text/markdown" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        const cleanName = auditReportModal.resumeName.replace(/[^\w\-_\.]/g, "_");
        link.download = `${cleanName}_ATS_Audit_Report.md`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        toast("Report downloaded! 📄", "success");
      } else {
        toast("Download failed", "error");
      }
    }
  };

  const handleCopyReportMarkdown = () => {
    if (auditReportModal?.data?.markdown_report) {
      navigator.clipboard.writeText(auditReportModal.data.markdown_report);
      toast("Full ATS Audit Report copied to clipboard! 📋", "success");
    }
  };

  const handlePrintAuditReport = () => {
    window.print();
  };

  // Seniority badge based on experience criteria
  const getSeniorityLabel = (years: number) => {
    if (years <= 1) return { label: "Entry-Level / Junior (0-1 yrs)", color: "#38bdf8", bg: "rgba(56,189,248,0.15)" };
    if (years <= 4) return { label: "Mid-Level Professional (2-4 yrs)", color: "#818cf8", bg: "rgba(129,140,248,0.15)" };
    if (years <= 7) return { label: "Senior Engineer (5-7 yrs)", color: "#34d399", bg: "rgba(52,211,153,0.15)" };
    return { label: "Staff / Lead / Principal (8+ yrs)", color: "#fbbf24", bg: "rgba(251,191,36,0.15)" };
  };

  const seniority = getSeniorityLabel(globalExperienceCriteria);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", position: "relative" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1 style={{ fontSize: "24px", fontWeight: 800, color: "white", marginBottom: "4px" }}>
              AI Resume Parser & Auto-Apply
            </h1>
            <span
              style={{
                fontSize: "11px",
                padding: "2px 8px",
                borderRadius: "12px",
                background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.2))",
                border: "1px solid rgba(99,102,241,0.4)",
                color: "#a5b4fc",
                fontWeight: 600,
              }}
            >
              5-Step Auto-Pilot
            </span>
          </div>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Read resume files (PDF/DOCX), autofill profile details, check required application fields, set experience criteria, rate quality, and apply automatically.
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => setShowForm(!showForm)}
          id="add-resume-btn"
        >
          <Plus size={16} />
          New Resume
        </button>
      </div>

      {/* Global Criteria Bar: Years of Experience & Target Location */}
      <div
        className="glass-card"
        style={{
          padding: "20px 24px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
          border: "1px solid rgba(99,102,241,0.25)",
          background: "linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(13,13,26,0.85) 100%)",
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
          {/* Experience Criteria Info */}
          <div style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "rgba(99,102,241,0.18)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#818cf8",
              }}
            >
              <Sliders size={20} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "14px", fontWeight: 700, color: "white" }}>
                  Years of Experience Criteria
                </span>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    padding: "2px 8px",
                    borderRadius: "6px",
                    color: seniority.color,
                    background: seniority.bg,
                  }}
                >
                  {seniority.label}
                </span>
              </div>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "2px 0 0" }}>
                Used to filter and score job requirements. Higher-requirement jobs are flagged to optimize match quality.
              </p>
            </div>
          </div>

          {/* Experience Stepper */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>
              Experience:
            </span>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                background: "rgba(255,255,255,0.06)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                overflow: "hidden",
              }}
            >
              <button
                onClick={() => setGlobalExperienceCriteria((prev) => Math.max(0, prev - 1))}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "white",
                  padding: "8px 12px",
                  cursor: "pointer",
                  fontWeight: 700,
                  fontSize: "14px",
                }}
                title="Decrease years of experience criteria"
              >
                -
              </button>
              <div
                style={{
                  padding: "8px 16px",
                  fontSize: "13px",
                  fontWeight: 800,
                  color: "#c7d2fe",
                  background: "rgba(99,102,241,0.15)",
                  minWidth: "75px",
                  textAlign: "center",
                }}
              >
                {globalExperienceCriteria} {globalExperienceCriteria === 1 ? "Year" : "Years"}
              </div>
              <button
                onClick={() => setGlobalExperienceCriteria((prev) => Math.min(25, prev + 1))}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "white",
                  padding: "8px 12px",
                  cursor: "pointer",
                  fontWeight: 700,
                  fontSize: "14px",
                }}
                title="Increase years of experience criteria"
              >
                +
              </button>
            </div>
          </div>
        </div>

        {/* Target Location Search & Presets */}
        <div
          style={{
            paddingTop: "14px",
            borderTop: "1px solid rgba(255,255,255,0.06)",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: "1 1 320px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(99,102,241,0.3)",
                borderRadius: "8px",
                padding: "6px 12px",
                width: "100%",
                maxWidth: "380px",
              }}
            >
              <MapPin size={15} color="#818cf8" style={{ flexShrink: 0 }} />
              <input
                type="text"
                value={targetLocation}
                onChange={(e) => setTargetLocation(e.target.value)}
                placeholder="Target location (e.g. Remote, India, Mumbai, London)..."
                style={{
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  color: "white",
                  fontSize: "13px",
                  width: "100%",
                }}
                id="resume-target-location-input"
              />
              {targetLocation && (
                <button
                  onClick={() => setTargetLocation("")}
                  style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: 0 }}
                  title="Clear location filter"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          {/* Quick preset chips */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "11px", color: "var(--text-muted)", marginRight: "4px" }}>Quick Presets:</span>
            {["Remote", "India", "United States", "Bangalore", "Mumbai", "Worldwide"].map((loc) => {
              const isSelected =
                (loc === "Worldwide" && targetLocation === "") ||
                targetLocation.toLowerCase() === loc.toLowerCase();
              return (
                <button
                  key={loc}
                  onClick={() => setTargetLocation(loc === "Worldwide" ? "" : loc)}
                  style={{
                    fontSize: "11px",
                    fontWeight: isSelected ? 700 : 500,
                    padding: "3px 10px",
                    borderRadius: "14px",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    border: isSelected ? "1px solid #6366f1" : "1px solid rgba(255,255,255,0.08)",
                    background: isSelected ? "rgba(99,102,241,0.25)" : "rgba(255,255,255,0.03)",
                    color: isSelected ? "#c7d2fe" : "var(--text-muted)",
                  }}
                >
                  {loc}
                </button>
              );
            })}
          </div>

          {/* Global Internet Engines Active Notice */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "8px",
              paddingTop: "12px",
              borderTop: "1px solid rgba(255,255,255,0.06)",
              fontSize: "12px",
              color: "#a5b4fc",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "#10b981", boxShadow: "0 0 6px #10b981" }} />
              <strong style={{ color: "white" }}>Global Internet Search:</strong>
              <span>Auto-Pilot & Find Jobs scan across LinkedIn, Hacker News, RemoteOK, WWR, Jobspresso, Working Nomads, Remotive, Arbeitnow, Himalayas, The Muse, Jobicy, and Adzuna simultaneously.</span>
            </div>
            <span style={{ fontSize: "11px", color: "#6ee7b7", background: "rgba(16,185,129,0.15)", padding: "2px 8px", borderRadius: "10px", border: "1px solid rgba(16,185,129,0.3)" }}>
              12 Global Job Engines Active
            </span>
          </div>
        </div>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="glass-card" style={{ padding: "20px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 600, color: "white", marginBottom: "14px" }}>
            Create Resume Record
          </h3>
          <div style={{ display: "flex", gap: "12px" }}>
            <input
              className="input-field"
              placeholder="Resume name (e.g. Full Stack Developer Resume 2026)"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && newName.trim() && createMutation.mutate(newName.trim())}
              style={{ flex: 1 }}
              id="resume-name-input"
            />
            <button
              className="btn-primary"
              onClick={() => newName.trim() && createMutation.mutate(newName.trim())}
              disabled={createMutation.isPending || !newName.trim()}
            >
              {createMutation.isPending ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
              Create
            </button>
            <button className="btn-secondary" onClick={() => setShowForm(false)}>
              Cancel
            </button>
          </div>
          <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>
            After creating, upload a PDF or DOCX file to automatically read details, rate, and match jobs.
          </p>
        </div>
      )}

      {/* Resumes Grid */}
      {isLoading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(480px, 1fr))", gap: "20px" }}>
          {[1, 2].map((i) => (
            <div key={i} className="skeleton" style={{ height: "260px", borderRadius: "16px" }} />
          ))}
        </div>
      ) : resumes.length === 0 ? (
        <div className="glass-card" style={{ textAlign: "center", padding: "60px 32px" }}>
          <FileText size={48} style={{ margin: "0 auto 16px", opacity: 0.2 }} />
          <h3 style={{ fontSize: "18px", fontWeight: 700, color: "white", marginBottom: "8px" }}>
            No resumes uploaded yet
          </h3>
          <p style={{ color: "var(--text-muted)", fontSize: "14px", marginBottom: "20px" }}>
            Upload your resume to get an instant AI rating, discover high-matching jobs, and activate auto-apply.
          </p>
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={15} />
            Add Your First Resume
          </button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(480px, 1fr))", gap: "20px" }}>
          {resumes.map((resume) => {
            const isPrimary = !!(resume.is_primary || resume.is_default);
            const hasFile = !!(resume.file_name || resume.file_path);
            const score = resume.score;
            const skills = resume.extracted_skills || resume.skills || [];
            const roles = resume.extracted_roles || [];
            const feedback = resume.rating_feedback;
            const isExpanded = !!expandedFeedback[resume.id];
            const isAnalyzing = analyzeMutation.isPending && analyzeMutation.variables === resume.id;
            const isAutofilling = autofillMutation.isPending && autofillMutation.variables?.id === resume.id;

            return (
              <div
                key={resume.id}
                className="glass-card"
                style={{
                  padding: "24px",
                  borderRadius: "16px",
                  border: isPrimary ? "1px solid rgba(99,102,241,0.5)" : "1px solid var(--border)",
                  background: isPrimary
                    ? "linear-gradient(180deg, rgba(99,102,241,0.08) 0%, rgba(13,13,26,0.9) 100%)"
                    : "rgba(255,255,255,0.03)",
                  position: "relative",
                  display: "flex",
                  flexDirection: "column",
                  gap: "18px",
                  transition: "all 0.2s ease-in-out",
                }}
              >
                {/* Header Row */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
                  <div style={{ display: "flex", gap: "14px", alignItems: "flex-start", minWidth: 0 }}>
                    <div
                      style={{
                        width: "44px",
                        height: "44px",
                        borderRadius: "12px",
                        background: isPrimary ? "rgba(99,102,241,0.2)" : "rgba(255,255,255,0.07)",
                        border: isPrimary ? "1px solid rgba(99,102,241,0.4)" : "1px solid var(--border)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <FileText size={22} color={isPrimary ? "#818cf8" : "var(--text-muted)"} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <h3 style={{ fontSize: "16px", fontWeight: 700, color: "white", wordBreak: "break-word" }}>
                          {resume.name}
                        </h3>
                        {isPrimary && (
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              background: "rgba(99,102,241,0.25)",
                              border: "1px solid rgba(99,102,241,0.4)",
                              borderRadius: "6px",
                              padding: "2px 8px",
                              fontSize: "11px",
                              fontWeight: 600,
                              color: "#c7d2fe",
                            }}
                          >
                            <CheckCircle size={11} /> Primary
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                        Added {formatDate(resume.created_at)}
                        {resume.file_name && ` • ${resume.file_name}`}
                      </div>
                    </div>
                  </div>

                  {/* Top Score Pill if already rated */}
                  {score !== undefined && score !== null && (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "flex-end",
                        flexShrink: 0,
                      }}
                    >
                      <div
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          padding: "4px 12px",
                          borderRadius: "20px",
                          background:
                            score >= 80
                              ? "linear-gradient(135deg, rgba(16,185,129,0.25), rgba(5,150,105,0.3))"
                              : score >= 60
                              ? "linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.3))"
                              : "linear-gradient(135deg, rgba(245,158,11,0.25), rgba(217,119,6,0.3))",
                          border: `1px solid ${
                            score >= 80
                              ? "rgba(16,185,129,0.5)"
                              : score >= 60
                              ? "rgba(99,102,241,0.5)"
                              : "rgba(245,158,11,0.5)"
                          }`,
                          color: score >= 80 ? "#6ee7b7" : score >= 60 ? "#a5b4fc" : "#fcd34d",
                          fontWeight: 800,
                          fontSize: "15px",
                        }}
                      >
                        <Award size={15} />
                        {score}/100
                      </div>
                      {feedback?.ats_score && (
                        <span style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "3px" }}>
                          ATS Score: {feedback.ats_score}%
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Score & AI Analysis Section */}
                {hasFile && score !== undefined && score !== null ? (
                  <div
                    style={{
                      background: "rgba(0,0,0,0.25)",
                      borderRadius: "12px",
                      padding: "16px",
                      border: "1px solid rgba(255,255,255,0.05)",
                    }}
                  >
                    {/* Summary */}
                    {feedback?.summary && (
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: "12px" }}>
                        {feedback.summary}
                      </p>
                    )}

                    {/* Target Roles */}
                    {roles.length > 0 && (
                      <div style={{ marginBottom: "12px" }}>
                        <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                          <Target size={12} color="#6366f1" /> TARGET ROLES DETECTED
                        </div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                          {roles.map((role) => (
                            <span
                              key={role}
                              style={{
                                fontSize: "11px",
                                fontWeight: 500,
                                padding: "3px 9px",
                                background: "rgba(99,102,241,0.12)",
                                border: "1px solid rgba(99,102,241,0.3)",
                                borderRadius: "6px",
                                color: "#c7d2fe",
                              }}
                            >
                              🎯 {role}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Skills */}
                    {skills.length > 0 && (
                      <div style={{ marginBottom: "10px" }}>
                        <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", marginBottom: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                          <Briefcase size={12} color="#10b981" /> EXTRACTED SKILLS ({skills.length})
                        </div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
                          {skills.slice(0, 10).map((skill) => (
                            <span
                              key={skill}
                              style={{
                                fontSize: "11px",
                                padding: "2px 8px",
                                background: "rgba(255,255,255,0.05)",
                                border: "1px solid var(--border)",
                                borderRadius: "4px",
                                color: "var(--text-secondary)",
                              }}
                            >
                              {skill}
                            </span>
                          ))}
                          {skills.length > 10 && (
                            <span style={{ fontSize: "11px", color: "var(--text-muted)", padding: "2px 4px" }}>
                              +{skills.length - 10} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Toggle Detailed Feedback */}
                    <button
                      onClick={() => toggleFeedback(resume.id)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#818cf8",
                        fontSize: "12px",
                        fontWeight: 600,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        padding: 0,
                        marginTop: "8px",
                      }}
                    >
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      {isExpanded ? "Hide Strengths & Suggestions" : "View Strengths & Improvement Advice"}
                    </button>

                    {/* Expanded Feedback Panel */}
                    {isExpanded && feedback && (
                      <div
                        style={{
                          marginTop: "12px",
                          paddingTop: "12px",
                          borderTop: "1px solid rgba(255,255,255,0.07)",
                          display: "flex",
                          flexDirection: "column",
                          gap: "10px",
                        }}
                      >
                        {feedback.strengths && feedback.strengths.length > 0 && (
                          <div>
                            <div style={{ fontSize: "11px", fontWeight: 600, color: "#10b981", marginBottom: "4px", display: "flex", alignItems: "center", gap: "4px" }}>
                              <Check size={12} /> Key Strengths
                            </div>
                            <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "12px", color: "var(--text-secondary)" }}>
                              {feedback.strengths.map((s, idx) => (
                                <li key={idx} style={{ marginBottom: "3px" }}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {feedback.suggestions && feedback.suggestions.length > 0 && (
                          <div>
                            <div style={{ fontSize: "11px", fontWeight: 600, color: "#f59e0b", marginBottom: "4px", display: "flex", alignItems: "center", gap: "4px" }}>
                              <Lightbulb size={12} /> Actionable Tips to Boost Callbacks
                            </div>
                            <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "12px", color: "var(--text-secondary)" }}>
                              {feedback.suggestions.map((s, idx) => (
                                <li key={idx} style={{ marginBottom: "3px" }}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : hasFile ? (
                  /* Has file but not analyzed yet */
                  <div
                    style={{
                      background: "rgba(99,102,241,0.06)",
                      border: "1px dashed rgba(99,102,241,0.3)",
                      borderRadius: "12px",
                      padding: "16px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "12px",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "13px", fontWeight: 600, color: "white" }}>
                        File uploaded & ready
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                        Extract details, score ATS compatibility, and match jobs
                      </div>
                    </div>
                    <button
                      className="btn-primary"
                      onClick={() => analyzeMutation.mutate(resume.id)}
                      disabled={isAnalyzing}
                      style={{ fontSize: "12px", padding: "6px 14px" }}
                    >
                      {isAnalyzing ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                      {isAnalyzing ? "Rating..." : "Analyze with AI"}
                    </button>
                  </div>
                ) : null}

                {/* Upload or Replace Drop Zone */}
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => handleDrop(e, resume.id)}
                  onClick={() => {
                    setUploadingFor(resume.id);
                    fileInputRef.current?.click();
                  }}
                  style={{
                    border: `2px dashed ${dragging && uploadingFor === resume.id ? "#6366f1" : "var(--border)"}`,
                    borderRadius: "10px",
                    padding: hasFile ? "10px" : "18px",
                    textAlign: "center",
                    cursor: "pointer",
                    background: dragging && uploadingFor === resume.id ? "rgba(99,102,241,0.08)" : "transparent",
                    transition: "all 0.2s",
                  }}
                >
                  {uploadMutation.isPending && uploadingFor === resume.id ? (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", fontSize: "13px", color: "#6366f1" }}>
                      <Loader2 size={15} className="animate-spin" />
                      Reading Document & Autofilling Profile...
                    </div>
                  ) : (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", fontSize: "12px", color: "var(--text-muted)" }}>
                      <Upload size={14} />
                      {hasFile ? "Replace File (drag new PDF/DOCX)" : "Upload PDF or DOCX — Click or Drag"}
                    </div>
                  )}
                </div>

                {/* Primary Action Buttons */}
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {hasFile && (
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                      {/* One-Click Auto-Pilot */}
                      <button
                        onClick={() => handleRunAutoPilot(resume)}
                        disabled={autoPilotMutation.isPending}
                        style={{
                          background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
                          color: "white",
                          border: "none",
                          borderRadius: "8px",
                          padding: "10px 14px",
                          fontSize: "13px",
                          fontWeight: 700,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "6px",
                          boxShadow: "0 4px 14px rgba(99,102,241,0.35)",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <Zap size={15} />
                        Run Auto-Pilot
                      </button>

                      {/* Find Matching Jobs */}
                      <button
                        onClick={() => handleFindJobs(resume)}
                        disabled={findJobsMutation.isPending}
                        className="btn-secondary"
                        style={{
                          fontSize: "13px",
                          fontWeight: 600,
                          padding: "10px 14px",
                          justifyContent: "center",
                        }}
                      >
                        <Search size={14} />
                        Find Jobs
                      </button>
                    </div>
                  )}

                  {/* Requirements Checklist & Autofill Button */}
                  {hasFile && (
                    <button
                      className="btn-secondary"
                      onClick={() => handleOpenRequirements(resume)}
                      style={{
                        fontSize: "12px",
                        fontWeight: 600,
                        padding: "8px 12px",
                        justifyContent: "center",
                        background: "rgba(99,102,241,0.08)",
                        border: "1px solid rgba(99,102,241,0.25)",
                        color: "#c7d2fe",
                      }}
                    >
                      <UserCheck size={14} color="#818cf8" />
                      Check Application Requirements & Autofill Details
                    </button>
                  )}

                  {/* ATS Resume Audit Report & Download Button */}
                  {hasFile && (
                    <button
                      className="btn-secondary"
                      onClick={() => handleOpenAuditReport(resume)}
                      style={{
                        fontSize: "12px",
                        fontWeight: 600,
                        padding: "9px 14px",
                        justifyContent: "space-between",
                        background: "linear-gradient(135deg, rgba(16,185,129,0.12) 0%, rgba(99,102,241,0.12) 100%)",
                        border: "1px solid rgba(16,185,129,0.35)",
                        color: "#6ee7b7",
                        display: "flex",
                        alignItems: "center",
                        cursor: "pointer",
                      }}
                      id={`view-ats-audit-report-${resume.id}`}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
                        <FileCheck size={15} color="#34d399" />
                        <span style={{ fontWeight: 700 }}>ATS Resume Audit Report</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "6px",
                            background: "rgba(16,185,129,0.2)",
                            color: "#a7f3d0",
                            border: "1px solid rgba(16,185,129,0.4)",
                          }}
                        >
                          {resume.score ? `Score: ${resume.score}/100` : "View Audit"}
                        </span>
                        <FileDown size={14} color="#a7f3d0" />
                      </div>
                    </button>
                  )}

                  {/* Secondary Management Controls */}
                  <div style={{ display: "flex", gap: "8px", alignItems: "center", marginTop: "4px" }}>
                    {!isPrimary ? (
                      <button
                        className="btn-secondary"
                        onClick={() => setPrimaryMutation.mutate(resume.id)}
                        disabled={setPrimaryMutation.isPending}
                        style={{ fontSize: "12px", padding: "6px 12px", flex: 1, justifyContent: "center" }}
                      >
                        <Star size={13} />
                        Set as Active
                      </button>
                    ) : (
                      <div
                        style={{
                          flex: 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "6px",
                          fontSize: "12px",
                          color: "#818cf8",
                          fontWeight: 500,
                          padding: "6px 12px",
                        }}
                      >
                        <StarOff size={13} /> Primary Active Resume
                      </div>
                    )}

                    {hasFile && (
                      <button
                        className="btn-secondary"
                        onClick={() => analyzeMutation.mutate(resume.id)}
                        disabled={isAnalyzing}
                        title="Re-rate and extract skills"
                        style={{ fontSize: "12px", padding: "6px 10px" }}
                      >
                        {isAnalyzing ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                      </button>
                    )}

                    <button
                      className="btn-danger"
                      onClick={() => deleteMutation.mutate(resume.id)}
                      disabled={deleteMutation.isPending}
                      style={{ fontSize: "12px", padding: "6px 10px" }}
                      title="Delete resume record"
                    >
                      {deleteMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.doc,.docx"
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file && uploadingFor) {
            handleFileUpload(uploadingFor, file);
          }
          e.target.value = "";
        }}
        id="resume-file-input"
      />

      {/* Requirements & Autofill Modal */}
      {requirementsModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.78)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px",
          }}
        >
          <div
            className="glass-card"
            style={{
              width: "100%",
              maxWidth: "760px",
              maxHeight: "88vh",
              overflowY: "auto",
              padding: "28px",
              borderRadius: "20px",
              border: "1px solid rgba(99,102,241,0.35)",
              background: "#0c0d1b",
              boxShadow: "0 25px 50px rgba(0,0,0,0.7)",
              display: "flex",
              flexDirection: "column",
              gap: "20px",
            }}
          >
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div
                  style={{
                    width: "42px",
                    height: "42px",
                    borderRadius: "12px",
                    background: "rgba(99,102,241,0.2)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#818cf8",
                  }}
                >
                  <ShieldCheck size={22} />
                </div>
                <div>
                  <h2 style={{ fontSize: "18px", fontWeight: 800, color: "white" }}>
                    Application Requirements & Autofill Details
                  </h2>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    {requirementsModal.resumeName} • Tells which fields are REQUIRED vs OPTIONAL for automatic job applications.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setRequirementsModal(null)}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "none",
                  borderRadius: "8px",
                  padding: "6px",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Loading */}
            {requirementsModal.isLoading ? (
              <div style={{ textAlign: "center", padding: "40px" }}>
                <Loader2 size={36} className="animate-spin" style={{ margin: "0 auto 12px", color: "#6366f1" }} />
                <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
                  Analyzing resume details against ATS application requirements...
                </p>
              </div>
            ) : requirementsModal.checklist ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                {/* Status Notice Banner */}
                <div
                  style={{
                    padding: "16px 20px",
                    borderRadius: "14px",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "14px",
                    background: requirementsModal.checklist.all_required_met
                      ? "linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(5,150,105,0.1) 100%)"
                      : "linear-gradient(135deg, rgba(245,158,11,0.15) 0%, rgba(217,119,6,0.1) 100%)",
                    border: `1px solid ${
                      requirementsModal.checklist.all_required_met
                        ? "rgba(16,185,129,0.35)"
                        : "rgba(245,158,11,0.35)"
                    }`,
                  }}
                >
                  <div style={{ marginTop: "2px" }}>
                    {requirementsModal.checklist.all_required_met ? (
                      <CheckCircle2 size={22} color="#10b981" />
                    ) : (
                      <AlertTriangle size={22} color="#f59e0b" />
                    )}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                      <span
                        style={{
                          fontSize: "14px",
                          fontWeight: 700,
                          color: requirementsModal.checklist.all_required_met ? "#6ee7b7" : "#fcd34d",
                        }}
                      >
                        {requirementsModal.checklist.all_required_met
                          ? "All Required Application Fields Ready!"
                          : `Action Required: Missing ${requirementsModal.checklist.missing_required_fields.length} Required Field(s)`}
                      </span>
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: 800,
                          padding: "2px 8px",
                          borderRadius: "10px",
                          background: requirementsModal.checklist.all_required_met
                            ? "rgba(16,185,129,0.2)"
                            : "rgba(245,158,11,0.2)",
                          color: requirementsModal.checklist.all_required_met ? "#6ee7b7" : "#fcd34d",
                        }}
                      >
                        {requirementsModal.checklist.completion_percentage}% Application Ready
                      </span>
                    </div>
                    <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: "4px 0 0", lineHeight: 1.5 }}>
                      {requirementsModal.checklist.notice}
                    </p>
                  </div>
                </div>

                {/* Autofill Trigger Action */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "14px 18px",
                    background: "rgba(99,102,241,0.08)",
                    border: "1px solid rgba(99,102,241,0.2)",
                    borderRadius: "12px",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: "white" }}>
                      Autofill Profile from this Resume
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      Extracts name, contact, job title, years of experience, and skills into your candidate profile.
                    </div>
                  </div>
                  <button
                    className="btn-primary"
                    onClick={() =>
                      autofillMutation.mutate({
                        id: requirementsModal.resumeId,
                        overwrite: true,
                      })
                    }
                    disabled={autofillMutation.isPending}
                    style={{ fontSize: "12px", padding: "8px 16px" }}
                  >
                    {autofillMutation.isPending ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <RefreshCw size={13} />
                    )}
                    Autofill Profile Now
                  </button>
                </div>

                {/* Fields Table / Checklist */}
                <div>
                  <h4 style={{ fontSize: "13px", fontWeight: 700, color: "white", marginBottom: "10px" }}>
                    Application Fields Specification (Required vs Optional)
                  </h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {requirementsModal.checklist.fields.map((f) => {
                      const isReq = f.required;
                      const isFilled = f.status === "filled";

                      return (
                        <div
                          key={f.key}
                          style={{
                            background: "rgba(255,255,255,0.02)",
                            border: `1px solid ${
                              isReq && !isFilled
                                ? "rgba(239,68,68,0.4)"
                                : isFilled
                                ? "rgba(16,185,129,0.2)"
                                : "var(--border)"
                            }`,
                            borderRadius: "10px",
                            padding: "12px 16px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: "14px",
                          }}
                        >
                          <div style={{ minWidth: 0, flex: 1 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                              <span style={{ fontSize: "13px", fontWeight: 700, color: "white" }}>
                                {f.label}
                              </span>
                              {isReq ? (
                                <span
                                  style={{
                                    fontSize: "10px",
                                    fontWeight: 700,
                                    padding: "2px 6px",
                                    borderRadius: "4px",
                                    background: "rgba(239,68,68,0.2)",
                                    border: "1px solid rgba(239,68,68,0.35)",
                                    color: "#fca5a5",
                                  }}
                                >
                                  REQUIRED *
                                </span>
                              ) : (
                                <span
                                  style={{
                                    fontSize: "10px",
                                    fontWeight: 500,
                                    padding: "2px 6px",
                                    borderRadius: "4px",
                                    background: "rgba(255,255,255,0.06)",
                                    color: "var(--text-muted)",
                                  }}
                                >
                                  OPTIONAL
                                </span>
                              )}
                              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                                • {f.category}
                              </span>
                            </div>

                            <p style={{ fontSize: "11px", color: "var(--text-secondary)", margin: "3px 0 0" }}>
                              {f.reason}
                            </p>

                            {/* Value Display */}
                            <div style={{ marginTop: "4px", fontSize: "12px" }}>
                              {isFilled ? (
                                <span style={{ color: "#c7d2fe", wordBreak: "break-all" }}>
                                  {Array.isArray(f.value) ? f.value.slice(0, 5).join(", ") + (f.value.length > 5 ? ` (+${f.value.length - 5} more)` : "") : String(f.value)}
                                </span>
                              ) : (
                                <span style={{ color: isReq ? "#ef4444" : "var(--text-muted)", fontStyle: "italic" }}>
                                  {isReq ? "Not provided — required for application submission" : "Not provided (optional)"}
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Status Badge */}
                          <div style={{ flexShrink: 0 }}>
                            {isFilled ? (
                              <span
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "4px",
                                  fontSize: "11px",
                                  fontWeight: 600,
                                  color: "#6ee7b7",
                                  background: "rgba(16,185,129,0.15)",
                                  padding: "4px 8px",
                                  borderRadius: "6px",
                                }}
                              >
                                <Check size={12} /> Filled
                              </span>
                            ) : (
                              <span
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "4px",
                                  fontSize: "11px",
                                  fontWeight: 600,
                                  color: isReq ? "#fca5a5" : "var(--text-muted)",
                                  background: isReq ? "rgba(239,68,68,0.15)" : "rgba(255,255,255,0.04)",
                                  padding: "4px 8px",
                                  borderRadius: "6px",
                                }}
                              >
                                {isReq ? <AlertCircle size={12} /> : null}
                                {isReq ? "Missing" : "Empty"}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Footer */}
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
                  <button
                    className="btn-primary"
                    onClick={() => {
                      const resume = resumes.find((r) => r.id === requirementsModal.resumeId);
                      setRequirementsModal(null);
                      if (resume) handleRunAutoPilot(resume);
                    }}
                  >
                    <Zap size={15} />
                    Proceed to Auto-Pilot
                  </button>
                  <button className="btn-secondary" onClick={() => setRequirementsModal(null)}>
                    Close
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* ATS Resume Audit Report Modal */}
      {auditReportModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(3, 7, 18, 0.85)",
            backdropFilter: "blur(10px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setAuditReportModal(null);
          }}
        >
          <div
            className="glass-card"
            style={{
              width: "100%",
              maxWidth: "960px",
              maxHeight: "90vh",
              overflowY: "auto",
              padding: "28px",
              borderRadius: "22px",
              border: "1px solid rgba(16, 185, 129, 0.35)",
              background: "linear-gradient(165deg, #0b0f19 0%, #0d1224 50%, #070913 100%)",
              boxShadow: "0 25px 60px rgba(0,0,0,0.85), 0 0 40px rgba(16,185,129,0.12)",
              display: "flex",
              flexDirection: "column",
              gap: "20px",
            }}
          >
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", flexWrap: "wrap", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "18px" }}>
              <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "14px",
                    background: "linear-gradient(135deg, rgba(16,185,129,0.25), rgba(99,102,241,0.25))",
                    border: "1px solid rgba(16,185,129,0.45)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#34d399",
                    boxShadow: "0 0 20px rgba(16,185,129,0.2)",
                  }}
                >
                  <FileCheck size={26} />
                </div>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <h2 style={{ fontSize: "20px", fontWeight: 800, color: "white", margin: 0 }}>
                      ATS Resume Audit & Strategic Improvement Report
                    </h2>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: "10px",
                        background: "rgba(16,185,129,0.18)",
                        color: "#6ee7b7",
                        border: "1px solid rgba(16,185,129,0.35)",
                      }}
                    >
                      AI Powered
                    </span>
                  </div>
                  <p style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "4px" }}>
                    Candidate: <strong style={{ color: "white" }}>{auditReportModal.data?.candidate_name || "Applicant"}</strong> • File: <code style={{ color: "#a5b4fc" }}>{auditReportModal.resumeName}</code>
                  </p>
                </div>
              </div>

              {/* Action Buttons Toolbar */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <button
                  onClick={() => handleDownloadAuditReport("markdown")}
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    padding: "7px 12px",
                    borderRadius: "8px",
                    background: "rgba(16,185,129,0.18)",
                    border: "1px solid rgba(16,185,129,0.4)",
                    color: "#6ee7b7",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                    transition: "all 0.15s ease",
                  }}
                  title="Download report in Markdown format"
                >
                  <FileDown size={14} />
                  Download .md
                </button>
                <button
                  onClick={() => handleDownloadAuditReport("text")}
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    padding: "7px 12px",
                    borderRadius: "8px",
                    background: "rgba(99,102,241,0.18)",
                    border: "1px solid rgba(99,102,241,0.4)",
                    color: "#a5b4fc",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                    transition: "all 0.15s ease",
                  }}
                  title="Download report in Plain Text format"
                >
                  <Download size={14} />
                  Download .txt
                </button>
                <button
                  onClick={handleCopyReportMarkdown}
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    padding: "7px 12px",
                    borderRadius: "8px",
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid var(--border)",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                  }}
                  title="Copy full markdown report to clipboard"
                >
                  <Copy size={14} />
                  Copy
                </button>
                <button
                  onClick={handlePrintAuditReport}
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    padding: "7px 12px",
                    borderRadius: "8px",
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid var(--border)",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                  }}
                  title="Print or Save as PDF"
                >
                  <Printer size={14} />
                  PDF / Print
                </button>
                <button
                  onClick={() => setAuditReportModal(null)}
                  style={{
                    background: "rgba(255,255,255,0.07)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    padding: "7px",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            {auditReportModal.isLoading ? (
              <div style={{ textAlign: "center", padding: "60px 20px" }}>
                <Loader2 size={38} className="animate-spin" color="#34d399" style={{ margin: "0 auto 16px" }} />
                <h3 style={{ fontSize: "17px", fontWeight: 700, color: "white" }}>
                  Generating Comprehensive ATS Audit & Deep Diagnostic...
                </h3>
                <p style={{ color: "var(--text-muted)", fontSize: "13px", maxWidth: "500px", margin: "8px auto 0" }}>
                  Evaluating ATS parser readability, font ligature anomalies, keyword density, quantified metric ratios, and Google X-Y-Z bullet points.
                </p>
              </div>
            ) : auditReportModal.data ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                {/* Score Banner */}
                <div
                  style={{
                    background: "linear-gradient(135deg, rgba(16,185,129,0.12) 0%, rgba(99,102,241,0.12) 100%)",
                    border: "1px solid rgba(16,185,129,0.3)",
                    borderRadius: "16px",
                    padding: "18px 22px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: "16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
                    <div
                      style={{
                        width: "64px",
                        height: "64px",
                        borderRadius: "50%",
                        background:
                          auditReportModal.data.overall_ats_score >= 80
                            ? "linear-gradient(135deg, #059669, #10b981)"
                            : auditReportModal.data.overall_ats_score >= 65
                            ? "linear-gradient(135deg, #d97706, #f59e0b)"
                            : "linear-gradient(135deg, #dc2626, #ef4444)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "white",
                        fontWeight: 900,
                        fontSize: "20px",
                        boxShadow: "0 8px 20px rgba(0,0,0,0.4)",
                        flexShrink: 0,
                      }}
                    >
                      {auditReportModal.data.overall_ats_score}
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "1px", color: "var(--text-muted)", fontWeight: 700 }}>
                        Realistic ATS Pass Score
                      </div>
                      <div style={{ fontSize: "18px", fontWeight: 800, color: "white" }}>
                        {auditReportModal.data.overall_ats_score >= 80
                          ? "High ATS Pass Rate (Top 15%)"
                          : auditReportModal.data.overall_ats_score >= 65
                          ? "Moderate ATS Pass Rate — Fixable Flaws"
                          : "High Risk of ATS Rejection — Critical Updates Needed"}
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                        Resume Quality Index: <strong style={{ color: "#a5b4fc" }}>{auditReportModal.data.overall_quality_score}/100</strong> • Extracted Keywords: <strong style={{ color: "#6ee7b7" }}>{auditReportModal.data.detected_skills?.length || 0} skills</strong>
                      </div>
                    </div>
                  </div>

                  {auditReportModal.data.critical_alerts?.length > 0 && (
                    <div
                      style={{
                        padding: "8px 14px",
                        background: "rgba(239,68,68,0.15)",
                        border: "1px solid rgba(239,68,68,0.4)",
                        borderRadius: "10px",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        color: "#fca5a5",
                        fontSize: "12px",
                        fontWeight: 600,
                      }}
                    >
                      <AlertTriangle size={16} color="#ef4444" />
                      <span>{auditReportModal.data.critical_alerts.length} Critical Parser Blockers Detected</span>
                    </div>
                  )}
                </div>

                {/* Tabs */}
                <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid var(--border)", paddingBottom: "8px", overflowX: "auto" }}>
                  {[
                    { id: "overview", label: "📊 Score & Dimensions" },
                    {
                      id: "tech",
                      label: `💻 Tech Stack & Latest Tech (${
                        auditReportModal.data.technology_analysis?.total_detected_count ??
                        auditReportModal.data.detected_skills?.length ??
                        0
                      })`,
                    },
                    { id: "alerts", label: `⚠️ Parser Blockers (${auditReportModal.data.critical_alerts?.length || 0})` },
                    { id: "rewrites", label: "✨ Google X-Y-Z Rewrites" },
                    { id: "roadmap", label: "🎯 Priority Roadmap" },
                    { id: "markdown", label: "📄 Raw Full Report" },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setAuditActiveTab(tab.id as any)}
                      style={{
                        padding: "8px 16px",
                        borderRadius: "8px",
                        border: "none",
                        background: auditActiveTab === tab.id ? "rgba(99,102,241,0.25)" : "transparent",
                        color: auditActiveTab === tab.id ? "#c7d2fe" : "var(--text-muted)",
                        fontWeight: auditActiveTab === tab.id ? 700 : 500,
                        fontSize: "13px",
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                        borderBottom: auditActiveTab === tab.id ? "2px solid #6366f1" : "2px solid transparent",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab: Overview (Category Dimensions) */}
                {auditActiveTab === "overview" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "14px" }}>
                      {auditReportModal.data.category_scores?.map((cat) => {
                        const statusColors: Record<string, { bg: string; border: string; text: string }> = {
                          strong: { bg: "rgba(16,185,129,0.15)", border: "rgba(16,185,129,0.35)", text: "#6ee7b7" },
                          moderate: { bg: "rgba(245,158,11,0.15)", border: "rgba(245,158,11,0.35)", text: "#fcd34d" },
                          weak: { bg: "rgba(239,68,68,0.15)", border: "rgba(239,68,68,0.35)", text: "#fca5a5" },
                          critical: { bg: "rgba(220,38,38,0.25)", border: "rgba(220,38,38,0.5)", text: "#f87171" },
                        };
                        const col = statusColors[cat.status] || statusColors.moderate;

                        return (
                          <div
                            key={cat.key}
                            style={{
                              background: "rgba(255,255,255,0.03)",
                              border: "1px solid var(--border)",
                              borderRadius: "14px",
                              padding: "16px",
                              display: "flex",
                              flexDirection: "column",
                              gap: "10px",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                              <div>
                                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "white", margin: 0 }}>
                                  {cat.label}
                                </h4>
                              </div>
                              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                <span
                                  style={{
                                    fontSize: "11px",
                                    fontWeight: 700,
                                    padding: "2px 8px",
                                    borderRadius: "6px",
                                    background: col.bg,
                                    border: `1px solid ${col.border}`,
                                    color: col.text,
                                    textTransform: "capitalize",
                                  }}
                                >
                                  {cat.status}
                                </span>
                                <span style={{ fontSize: "13px", fontWeight: 800, color: "white" }}>
                                  {cat.score}/100
                                </span>
                              </div>
                            </div>

                            {/* Progress bar */}
                            <div style={{ height: "6px", background: "rgba(255,255,255,0.08)", borderRadius: "3px", overflow: "hidden" }}>
                              <div
                                style={{
                                  height: "100%",
                                  width: `${cat.score}%`,
                                  background:
                                    cat.score >= 80 ? "#10b981" : cat.score >= 60 ? "#6366f1" : cat.score >= 40 ? "#f59e0b" : "#ef4444",
                                  borderRadius: "3px",
                                  transition: "width 0.4s ease",
                                }}
                              />
                            </div>

                            <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                              <strong style={{ color: "var(--text-muted)" }}>Finding: </strong>
                              {cat.findings}
                            </div>

                            <div
                              style={{
                                fontSize: "12px",
                                color: "#c7d2fe",
                                background: "rgba(99,102,241,0.08)",
                                border: "1px solid rgba(99,102,241,0.2)",
                                padding: "8px 10px",
                                borderRadius: "8px",
                                lineHeight: 1.4,
                                marginTop: "auto",
                              }}
                            >
                              <strong style={{ color: "#a5b4fc" }}>Recommendation: </strong>
                              {cat.recommendation}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Tab: Tech Stack & Latest Tech */}
                {auditActiveTab === "tech" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    {/* Modern Stack Adoption Header Banner */}
                    <div
                      style={{
                        background: "linear-gradient(135deg, rgba(99,102,241,0.18) 0%, rgba(139,92,246,0.12) 50%, rgba(16,185,129,0.08) 100%)",
                        border: "1px solid rgba(99,102,241,0.35)",
                        borderRadius: "16px",
                        padding: "20px 24px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        flexWrap: "wrap",
                        gap: "18px",
                      }}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxWidth: "600px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span
                            style={{
                              display: "inline-block",
                              width: "8px",
                              height: "8px",
                              borderRadius: "50%",
                              background: "#10b981",
                              boxShadow: "0 0 8px #10b981",
                            }}
                          />
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: 800,
                              letterSpacing: "0.5px",
                              textTransform: "uppercase",
                              color: "#6ee7b7",
                            }}
                          >
                            2026 SOTA Technology Intelligence
                          </span>
                          <span
                            style={{
                              fontSize: "11px",
                              background: "rgba(255,255,255,0.08)",
                              padding: "2px 8px",
                              borderRadius: "12px",
                              color: "#c7d2fe",
                              fontWeight: 600,
                            }}
                          >
                            Live Market Benchmark
                          </span>
                        </div>
                        <h3 style={{ fontSize: "18px", fontWeight: 800, color: "white", margin: 0 }}>
                          Modern Technology Stack & Architecture Audit
                        </h3>
                        <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                          Evaluates candidate resume against 2026 state-of-the-art engineering standards across 6 core domains: Programming Languages, Microservices & APIs, Client Systems, Distributed Caching & Databases, Cloud Native CI/CD, and Generative AI.
                        </p>
                      </div>

                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "16px",
                          background: "rgba(0,0,0,0.35)",
                          border: "1px solid rgba(255,255,255,0.1)",
                          padding: "14px 20px",
                          borderRadius: "14px",
                        }}
                      >
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                            Stack Adoption Score
                          </div>
                          <div
                            style={{
                              fontSize: "12px",
                              fontWeight: 700,
                              color:
                                (auditReportModal.data.technology_analysis?.modern_stack_score || 0) >= 85
                                  ? "#6ee7b7"
                                  : (auditReportModal.data.technology_analysis?.modern_stack_score || 0) >= 70
                                  ? "#93c5fd"
                                  : "#fcd34d",
                            }}
                          >
                            {(auditReportModal.data.technology_analysis?.modern_stack_score || 0) >= 85
                              ? "Cutting-Edge SOTA 2026"
                              : (auditReportModal.data.technology_analysis?.modern_stack_score || 0) >= 70
                              ? "Industry Production-Ready"
                              : "Transitional Stack"}
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                            {auditReportModal.data.technology_analysis?.total_detected_count || 0} Verified Techs
                          </div>
                        </div>

                        <div
                          style={{
                            width: "56px",
                            height: "56px",
                            borderRadius: "50%",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: "20px",
                            fontWeight: 900,
                            color: "white",
                            background:
                              (auditReportModal.data.technology_analysis?.modern_stack_score || 0) >= 85
                                ? "conic-gradient(#10b981 0% 85%, rgba(255,255,255,0.1) 85% 100%)"
                                : (auditReportModal.data.technology_analysis?.modern_stack_score || 0) >= 70
                                ? "conic-gradient(#6366f1 0% 75%, rgba(255,255,255,0.1) 75% 100%)"
                                : "conic-gradient(#f59e0b 0% 50%, rgba(255,255,255,0.1) 50% 100%)",
                            boxShadow: "0 0 16px rgba(99,102,241,0.3)",
                          }}
                        >
                          <div
                            style={{
                              width: "46px",
                              height: "46px",
                              borderRadius: "50%",
                              background: "#0c0e17",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                            }}
                          >
                            {auditReportModal.data.technology_analysis?.modern_stack_score || 75}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 2026 High-Impact Missing Technologies (Gaps) */}
                    {auditReportModal.data.technology_analysis?.missing_high_impact &&
                      auditReportModal.data.technology_analysis.missing_high_impact.length > 0 && (
                        <div
                          style={{
                            background: "rgba(245,158,11,0.06)",
                            border: "1px solid rgba(245,158,11,0.25)",
                            borderRadius: "14px",
                            padding: "16px 20px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "12px",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <TrendingUp size={16} color="#fbbf24" />
                              <h4 style={{ fontSize: "14px", fontWeight: 700, color: "white", margin: 0 }}>
                                High-Impact 2026 Skills Missing in Profile (Top Recruiter Search Volume)
                              </h4>
                            </div>
                            <span style={{ fontSize: "11px", color: "#fcd34d", fontWeight: 600 }}>
                              Adding 2-3 of these to projects increases ATS interview conversion by 45%+
                            </span>
                          </div>

                          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                            {auditReportModal.data.technology_analysis.missing_high_impact.map((m, idx) => (
                              <div
                                key={idx}
                                style={{
                                  background: "rgba(0,0,0,0.3)",
                                  border: "1px solid rgba(245,158,11,0.3)",
                                  borderRadius: "10px",
                                  padding: "6px 12px",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "8px",
                                }}
                              >
                                <span style={{ fontSize: "12px", fontWeight: 700, color: "#fde68a" }}>
                                  + {m.name}
                                </span>
                                <span
                                  style={{
                                    fontSize: "10px",
                                    padding: "2px 6px",
                                    borderRadius: "4px",
                                    background: "rgba(245,158,11,0.2)",
                                    color: "#fcd34d",
                                    fontWeight: 700,
                                  }}
                                >
                                  {m.demand} Demand
                                </span>
                                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                                  ({m.domain})
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                    {/* 6-Domain Architectural Assessment Grid */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
                      {auditReportModal.data.technology_analysis?.domains?.map((dom) => {
                        const statusColors: Record<string, { bg: string; border: string; text: string }> = {
                          strong: { bg: "rgba(16,185,129,0.15)", border: "rgba(16,185,129,0.35)", text: "#6ee7b7" },
                          moderate: { bg: "rgba(245,158,11,0.15)", border: "rgba(245,158,11,0.35)", text: "#fcd34d" },
                          needs_upgrade: { bg: "rgba(239,68,68,0.15)", border: "rgba(239,68,68,0.35)", text: "#fca5a5" },
                        };
                        const col = statusColors[dom.status] || statusColors.moderate;

                        return (
                          <div
                            key={dom.key}
                            style={{
                              background: "rgba(255,255,255,0.03)",
                              border: "1px solid var(--border)",
                              borderRadius: "14px",
                              padding: "18px",
                              display: "flex",
                              flexDirection: "column",
                              gap: "12px",
                            }}
                          >
                            {/* Card Header */}
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                {getDomainIcon(dom.key)}
                                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "white", margin: 0 }}>
                                  {dom.label}
                                </h4>
                              </div>
                              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                <span
                                  style={{
                                    fontSize: "11px",
                                    fontWeight: 700,
                                    padding: "2px 8px",
                                    borderRadius: "6px",
                                    background: col.bg,
                                    border: `1px solid ${col.border}`,
                                    color: col.text,
                                    textTransform: "capitalize",
                                  }}
                                >
                                  {dom.status.replace("_", " ")}
                                </span>
                                <span style={{ fontSize: "13px", fontWeight: 800, color: "white" }}>
                                  {dom.score}%
                                </span>
                              </div>
                            </div>

                            {/* Progress bar */}
                            <div style={{ height: "5px", background: "rgba(255,255,255,0.08)", borderRadius: "3px", overflow: "hidden" }}>
                              <div
                                style={{
                                  height: "100%",
                                  width: `${dom.score}%`,
                                  background:
                                    dom.score >= 75 ? "#10b981" : dom.score >= 40 ? "#6366f1" : "#ef4444",
                                  borderRadius: "3px",
                                  transition: "width 0.4s ease",
                                }}
                              />
                            </div>

                            {/* Detected in Resume */}
                            <div>
                              <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "6px" }}>
                                Verified in Candidate Resume:
                              </div>
                              {dom.detected && dom.detected.length > 0 ? (
                                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                                  {dom.detected.map((item, idx) => (
                                    <span
                                      key={idx}
                                      style={{
                                        fontSize: "11px",
                                        fontWeight: 600,
                                        padding: "3px 8px",
                                        borderRadius: "6px",
                                        background: "rgba(99,102,241,0.15)",
                                        border: "1px solid rgba(99,102,241,0.3)",
                                        color: "#c7d2fe",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        gap: "4px",
                                      }}
                                    >
                                      <CheckCircle2 size={11} color="#818cf8" />
                                      {item.name}
                                      <span style={{ fontSize: "10px", color: "#a5b4fc", fontWeight: 700 }}>
                                        {item.demand}
                                      </span>
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                                  No explicit technologies detected in this domain.
                                </div>
                              )}
                            </div>

                            {/* 2026 SOTA Benchmarks */}
                            {dom.trends_2026 && dom.trends_2026.length > 0 && (
                              <div
                                style={{
                                  background: "rgba(0,0,0,0.25)",
                                  border: "1px solid rgba(255,255,255,0.06)",
                                  borderRadius: "8px",
                                  padding: "10px",
                                }}
                              >
                                <div style={{ fontSize: "11px", fontWeight: 700, color: "#a5b4fc", display: "flex", alignItems: "center", gap: "4px", marginBottom: "6px" }}>
                                  <Sparkles size={11} color="#818cf8" style={{ flexShrink: 0 }} /> 2026 SOTA Tech Benchmark:
                                </div>
                                <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "11px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                                  {dom.trends_2026.slice(0, 3).map((trend, tidx) => (
                                    <li key={tidx}>{trend}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Upgrade Advice */}
                            <div
                              style={{
                                fontSize: "11px",
                                color: "#93c5fd",
                                background: "rgba(59,130,246,0.08)",
                                border: "1px solid rgba(59,130,246,0.2)",
                                padding: "8px 10px",
                                borderRadius: "8px",
                                lineHeight: 1.4,
                                marginTop: "auto",
                              }}
                            >
                              <strong style={{ color: "#bfdbfe" }}>Architecture Upgrade: </strong>
                              {dom.upgrade_advice}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Legacy / Dated Phrasing Warnings */}
                    {auditReportModal.data.technology_analysis?.legacy_warnings &&
                      auditReportModal.data.technology_analysis.legacy_warnings.length > 0 && (
                        <div
                          style={{
                            background: "rgba(255,255,255,0.03)",
                            border: "1px solid var(--border)",
                            borderRadius: "14px",
                            padding: "18px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "12px",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <AlertCircle size={16} color="#f59e0b" />
                            <h4 style={{ fontSize: "14px", fontWeight: 700, color: "white", margin: 0 }}>
                              Modern Phrasing Upgrades (Eliminate Junior / Legacy Tone)
                            </h4>
                          </div>

                          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                            {auditReportModal.data.technology_analysis.legacy_warnings.map((lw, idx) => (
                              <div
                                key={idx}
                                style={{
                                  display: "grid",
                                  gridTemplateColumns: "1fr 1fr",
                                  gap: "12px",
                                  background: "rgba(0,0,0,0.3)",
                                  border: "1px solid rgba(255,255,255,0.08)",
                                  borderRadius: "10px",
                                  padding: "12px",
                                }}
                              >
                                <div>
                                  <div style={{ fontSize: "10px", fontWeight: 700, color: "#fca5a5", textTransform: "uppercase", marginBottom: "4px" }}>
                                    Dated Expression
                                  </div>
                                  <code style={{ fontSize: "12px", color: "#fca5a5", background: "rgba(239,68,68,0.15)", padding: "2px 6px", borderRadius: "4px" }}>
                                    {lw.current}
                                  </code>
                                  <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}>
                                    {lw.reason}
                                  </div>
                                </div>

                                <div>
                                  <div style={{ fontSize: "10px", fontWeight: 700, color: "#6ee7b7", textTransform: "uppercase", marginBottom: "4px" }}>
                                    2026 SOTA Alternative
                                  </div>
                                  <div style={{ fontSize: "12px", fontWeight: 600, color: "white" }}>
                                    {lw.improved}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                  </div>
                )}

                {/* Tab: Critical Alerts */}
                {auditActiveTab === "alerts" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                    {auditReportModal.data.critical_alerts?.length === 0 ? (
                      <div
                        style={{
                          padding: "24px",
                          textAlign: "center",
                          background: "rgba(16,185,129,0.08)",
                          border: "1px solid rgba(16,185,129,0.3)",
                          borderRadius: "12px",
                          color: "#6ee7b7",
                        }}
                      >
                        <CheckCircle size={28} style={{ margin: "0 auto 8px" }} />
                        <h4 style={{ fontSize: "16px", fontWeight: 700, margin: 0 }}>No Critical Parser Blockers Found!</h4>
                        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
                          Your resume formatting passed all standard automated parser heuristics without breaking tags.
                        </p>
                      </div>
                    ) : (
                      auditReportModal.data.critical_alerts?.map((alert, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: alert.type === "critical" ? "rgba(239,68,68,0.08)" : "rgba(245,158,11,0.08)",
                            border: `1px solid ${alert.type === "critical" ? "rgba(239,68,68,0.35)" : "rgba(245,158,11,0.35)"}`,
                            borderRadius: "14px",
                            padding: "18px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "8px",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                            <AlertTriangle size={18} color={alert.type === "critical" ? "#ef4444" : "#f59e0b"} />
                            <h4 style={{ fontSize: "15px", fontWeight: 700, color: "white", margin: 0 }}>
                              {alert.title}
                            </h4>
                            <span
                              style={{
                                fontSize: "10px",
                                fontWeight: 800,
                                textTransform: "uppercase",
                                padding: "2px 8px",
                                borderRadius: "6px",
                                background: alert.type === "critical" ? "rgba(239,68,68,0.25)" : "rgba(245,158,11,0.25)",
                                color: alert.type === "critical" ? "#fca5a5" : "#fcd34d",
                              }}
                            >
                              {alert.type}
                            </span>
                          </div>

                          <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                            {alert.detail}
                          </p>

                          <div
                            style={{
                              marginTop: "4px",
                              padding: "10px 14px",
                              borderRadius: "8px",
                              background: "rgba(0,0,0,0.3)",
                              border: "1px solid rgba(255,255,255,0.08)",
                              fontSize: "12px",
                              color: "#6ee7b7",
                              display: "flex",
                              alignItems: "flex-start",
                              gap: "8px",
                            }}
                          >
                            <strong style={{ color: "#34d399", whiteSpace: "nowrap" }}>How to fix:</strong>
                            <span>{alert.fix}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Tab: Rewrites */}
                {auditActiveTab === "rewrites" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                    <div
                      style={{
                        padding: "12px 16px",
                        background: "rgba(99,102,241,0.08)",
                        border: "1px solid rgba(99,102,241,0.25)",
                        borderRadius: "10px",
                        fontSize: "13px",
                        color: "#c7d2fe",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                      }}
                    >
                      <Sparkles size={18} color="#818cf8" style={{ flexShrink: 0 }} />
                      <span>
                        <strong>Google X-Y-Z Formula:</strong> "Accomplished [X] as measured by [Y] by doing [Z]". Upgrade passive job duties into quantifiable engineering impact.
                      </span>
                    </div>

                    {auditReportModal.data.rewrites?.map((rw, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: "rgba(255,255,255,0.03)",
                          border: "1px solid var(--border)",
                          borderRadius: "14px",
                          padding: "18px",
                          display: "flex",
                          flexDirection: "column",
                          gap: "12px",
                        }}
                      >
                        <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#a5b4fc", margin: 0 }}>
                          {rw.section}
                        </h4>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                          {/* Before */}
                          <div
                            style={{
                              background: "rgba(239,68,68,0.07)",
                              border: "1px solid rgba(239,68,68,0.25)",
                              borderRadius: "10px",
                              padding: "12px",
                            }}
                          >
                            <div style={{ fontSize: "11px", fontWeight: 700, color: "#fca5a5", textTransform: "uppercase", marginBottom: "6px" }}>
                              Current / Original
                            </div>
                            <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                              {rw.original}
                            </p>
                          </div>

                          {/* After */}
                          <div
                            style={{
                              background: "rgba(16,185,129,0.08)",
                              border: "1px solid rgba(16,185,129,0.3)",
                              borderRadius: "10px",
                              padding: "12px",
                            }}
                          >
                            <div style={{ fontSize: "11px", fontWeight: 700, color: "#6ee7b7", textTransform: "uppercase", marginBottom: "6px" }}>
                              Optimized (Google X-Y-Z)
                            </div>
                            <p style={{ fontSize: "12px", color: "white", lineHeight: 1.5, margin: 0, fontWeight: 500 }}>
                              {rw.improved}
                            </p>
                          </div>
                        </div>

                        <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
                          💡 <strong>Why this works:</strong> {rw.rationale}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Tab: Roadmap */}
                {auditActiveTab === "roadmap" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    {auditReportModal.data.roadmap?.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: "rgba(255,255,255,0.03)",
                          border: "1px solid var(--border)",
                          borderRadius: "12px",
                          padding: "14px 18px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "16px",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: 700,
                              padding: "3px 9px",
                              borderRadius: "6px",
                              background:
                                item.priority === "High"
                                  ? "rgba(239,68,68,0.2)"
                                  : "rgba(99,102,241,0.2)",
                              border: `1px solid ${
                                item.priority === "High" ? "rgba(239,68,68,0.4)" : "rgba(99,102,241,0.4)"
                              }`,
                              color: item.priority === "High" ? "#fca5a5" : "#c7d2fe",
                              textTransform: "uppercase",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {item.priority} Priority
                          </span>
                          <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>
                            {item.timeframe}
                          </span>
                        </div>
                        <div style={{ fontSize: "13px", color: "white", fontWeight: 500, flex: 1, minWidth: "220px" }}>
                          {item.task}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Tab: Markdown Report */}
                {auditActiveTab === "markdown" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                        Full Markdown Report — Perfect for sharing, offline reading, or importing into your portfolio.
                      </span>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                          onClick={handleCopyReportMarkdown}
                          className="btn-secondary"
                          style={{ fontSize: "12px", padding: "5px 10px" }}
                        >
                          <Copy size={13} /> Copy All
                        </button>
                        <button
                          onClick={() => handleDownloadAuditReport("markdown")}
                          className="btn-primary"
                          style={{ fontSize: "12px", padding: "5px 12px" }}
                        >
                          <Download size={13} /> Download .md
                        </button>
                      </div>
                    </div>
                    <pre
                      style={{
                        background: "#080a12",
                        border: "1px solid var(--border)",
                        borderRadius: "12px",
                        padding: "18px",
                        fontSize: "12px",
                        color: "#e2e8f0",
                        fontFamily: "monospace",
                        whiteSpace: "pre-wrap",
                        maxHeight: "450px",
                        overflowY: "auto",
                        lineHeight: 1.6,
                      }}
                    >
                      {auditReportModal.data.markdown_report}
                    </pre>
                  </div>
                )}
              </div>
            ) : null}

            {/* Modal Footer */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderTop: "1px solid rgba(255,255,255,0.08)",
                paddingTop: "16px",
                flexWrap: "wrap",
                gap: "12px",
              }}
            >
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  className="btn-primary"
                  onClick={() => handleDownloadAuditReport("markdown")}
                  disabled={!auditReportModal.data}
                  style={{ fontSize: "13px", padding: "8px 16px" }}
                >
                  <FileDown size={15} />
                  Download Full Report (.md)
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => handleDownloadAuditReport("text")}
                  disabled={!auditReportModal.data}
                  style={{ fontSize: "13px", padding: "8px 14px" }}
                >
                  <Download size={14} />
                  Download Plain Text (.txt)
                </button>
              </div>

              <button className="btn-secondary" onClick={() => setAuditReportModal(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Auto-Pilot / Job Match Modal */}
      {modalState && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px",
          }}
        >
          <div
            className="glass-card"
            style={{
              width: "100%",
              maxWidth: "680px",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "28px",
              borderRadius: "20px",
              border: "1px solid rgba(99,102,241,0.3)",
              background: "#0c0d1b",
              boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
              display: "flex",
              flexDirection: "column",
              gap: "20px",
            }}
          >
            {/* Modal Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "38px",
                    height: "38px",
                    borderRadius: "10px",
                    background: "rgba(99,102,241,0.2)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#818cf8",
                  }}
                >
                  {modalState.type === "autoPilot" ? <Zap size={20} /> : <Search size={20} />}
                </div>
                <div>
                  <h2 style={{ fontSize: "18px", fontWeight: 800, color: "white" }}>
                    {modalState.type === "autoPilot" ? "1-Click Auto-Pilot Execution" : "Discovered Matching Jobs"}
                  </h2>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", marginTop: "2px" }}>
                    <span>Targeted for {modalState.resumeName}</span>
                    <span>•</span>
                    <span>{globalExperienceCriteria} Yrs Exp</span>
                    <span>•</span>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "3px", color: "#818cf8" }}>
                      <MapPin size={11} /> {targetLocation || "Any / Remote"}
                    </span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setModalState(null)}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "none",
                  borderRadius: "8px",
                  padding: "6px",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Loading State */}
            {modalState.status === "running" && (
              <div style={{ textAlign: "center", padding: "40px 20px" }}>
                <Loader2 size={40} className="animate-spin" style={{ margin: "0 auto 16px", color: "#6366f1" }} />
                <h3 style={{ fontSize: "16px", fontWeight: 700, color: "white", marginBottom: "8px" }}>
                  {modalState.type === "autoPilot"
                    ? "Running Auto-Pilot Pipeline..."
                    : "Searching & Scoring Jobs..."}
                </h3>
                <div style={{ fontSize: "13px", color: "var(--text-secondary)", maxWidth: "420px", margin: "0 auto", lineHeight: 1.6 }}>
                  {modalState.type === "autoPilot" ? (
                    <div style={{ textAlign: "left", display: "flex", flexDirection: "column", gap: "6px", marginTop: "12px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#6ee7b7" }}>
                        <CheckCircle size={14} /> 1. Reading & parsing resume document
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#6ee7b7" }}>
                        <CheckCircle size={14} /> 2. Autofilling candidate profile & checking required fields
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#a5b4fc" }}>
                        <Loader2 size={14} className="animate-spin" /> 3. Rating quality & ATS compatibility
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)" }}>
                        <Clock size={14} /> 4. Discovering jobs matching {targetLocation ? `'${targetLocation}'` : 'roles'} & {globalExperienceCriteria} yrs criteria
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)" }}>
                        <Clock size={14} /> 5. Applying automatically & queueing applications
                      </div>
                    </div>
                  ) : (
                    `Querying live job sources (${targetLocation || "Any Location"}) and matching candidates with ${globalExperienceCriteria} years of experience criteria...`
                  )}
                </div>
              </div>
            )}

            {/* Error State */}
            {modalState.status === "error" && (
              <div style={{ padding: "20px", textAlign: "center" }}>
                <div style={{ color: "#ef4444", fontSize: "14px", marginBottom: "16px" }}>
                  {modalState.errorMessage || "Operation failed. Please try again."}
                </div>
                <button className="btn-secondary" onClick={() => setModalState(null)}>
                  Close
                </button>
              </div>
            )}

            {/* Done State */}
            {modalState.status === "done" && modalState.data && (
              <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                {/* Auto-Pilot Summary Box */}
                {modalState.type === "autoPilot" && (
                  <div
                    style={{
                      background: "linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(16,185,129,0.1) 100%)",
                      border: "1px solid rgba(99,102,241,0.3)",
                      borderRadius: "14px",
                      padding: "16px 20px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px", flexWrap: "wrap", gap: "6px" }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "white" }}>
                        Pipeline Execution Complete
                      </span>
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                        {modalState.data.resume?.score && (
                          <span
                            style={{
                              fontSize: "12px",
                              fontWeight: 800,
                              padding: "3px 10px",
                              borderRadius: "12px",
                              background: "rgba(16,185,129,0.2)",
                              color: "#6ee7b7",
                              border: "1px solid rgba(16,185,129,0.3)",
                            }}
                          >
                            Score: {modalState.data.resume.score}/100
                          </span>
                        )}
                        <span
                          style={{
                            fontSize: "12px",
                            fontWeight: 700,
                            padding: "3px 10px",
                            borderRadius: "12px",
                            background: "rgba(99,102,241,0.2)",
                            color: "#c7d2fe",
                          }}
                        >
                          Criteria: {modalState.data.discovery?.experience_criteria_years ?? globalExperienceCriteria} Yrs
                        </span>
                        <span
                          style={{
                            fontSize: "12px",
                            fontWeight: 700,
                            padding: "3px 10px",
                            borderRadius: "12px",
                            background: "rgba(129,140,248,0.2)",
                            color: "#c7d2fe",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <MapPin size={11} /> {modalState.data.discovery?.location_used ?? targetLocation ?? "Remote"}
                        </span>
                      </div>
                    </div>
                    <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                      {modalState.data.summary_message}
                    </p>
                  </div>
                )}

                {/* Applications Queued Section */}
                {modalState.type === "autoPilot" && modalState.data.applications_queued && modalState.data.applications_queued.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "13px", fontWeight: 700, color: "#10b981", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <CheckCircle size={14} /> APPLICATIONS CREATED ({modalState.data.applications_queued.length})
                    </h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {modalState.data.applications_queued.map((app: any) => (
                        <div
                          key={app.application_id}
                          style={{
                            background: "rgba(255,255,255,0.03)",
                            border: "1px solid rgba(16,185,129,0.25)",
                            borderRadius: "10px",
                            padding: "10px 14px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                          }}
                        >
                          <div>
                            <div style={{ fontSize: "13px", fontWeight: 700, color: "white" }}>
                              {app.job_title}
                            </div>
                            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                              {app.company_name}
                            </div>
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", justifyContent: "flex-end" }}>
                            <span
                              style={{
                                fontSize: "12px",
                                fontWeight: 700,
                                color: "#6ee7b7",
                                background: "rgba(16,185,129,0.15)",
                                padding: "2px 8px",
                                borderRadius: "6px",
                              }}
                            >
                              {app.match_score}% Match
                            </span>
                            <span
                              style={{
                                fontSize: "11px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                background: "rgba(99,102,241,0.2)",
                                color: "#c7d2fe",
                              }}
                            >
                              {app.status}
                            </span>
                            {(app.application_url || app.url || app.job_url) && (
                              <a
                                href={app.application_url || app.url || app.job_url}
                                target="_blank"
                                rel="noreferrer"
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "4px",
                                  fontSize: "11px",
                                  fontWeight: 600,
                                  padding: "3px 8px",
                                  borderRadius: "6px",
                                  background: "rgba(99,102,241,0.2)",
                                  border: "1px solid rgba(99,102,241,0.4)",
                                  color: "#c7d2fe",
                                  textDecoration: "none",
                                }}
                              >
                                <ExternalLink size={11} /> Company Site
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Matched Jobs List */}
                {((modalState.type === "autoPilot" && modalState.data.matched_jobs) ||
                  (modalState.type === "findJobs" && modalState.data.jobs)) && (
                  <div>
                    <h4 style={{ fontSize: "13px", fontWeight: 700, color: "white", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Briefcase size={14} color="#6366f1" /> TOP MATCHING JOBS
                    </h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "260px", overflowY: "auto" }}>
                      {(modalState.type === "autoPilot" ? modalState.data.matched_jobs : modalState.data.jobs).map((job: any) => {
                        const jobApplyUrl = job.application_url || job.canonical_url || job.url;
                        return (
                          <div
                            key={job.job_id}
                            style={{
                              background: "rgba(255,255,255,0.03)",
                              border: "1px solid var(--border)",
                              borderRadius: "10px",
                              padding: "12px 14px",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                            }}
                          >
                            <div style={{ minWidth: 0, paddingRight: "12px" }}>
                              <div style={{ fontSize: "13px", fontWeight: 700, color: "white", wordBreak: "break-word" }}>
                                {job.title}
                              </div>
                              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                                {job.company_name} {job.location ? `• ${job.location}` : ""} {job.is_remote ? "(Remote)" : ""}
                              </div>
                              {job.experience_criteria && (
                                <div style={{ fontSize: "11px", color: job.experience_criteria.status === "below_minimum" ? "#fca5a5" : "#6ee7b7", marginTop: "2px" }}>
                                  Experience Criteria: {job.experience_criteria.explanation}
                                </div>
                              )}
                              {job.matched_skills && job.matched_skills.length > 0 && (
                                <div style={{ fontSize: "11px", color: "#818cf8", marginTop: "2px" }}>
                                  Matched: {job.matched_skills.slice(0, 3).join(", ")}
                                </div>
                              )}
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
                              <span
                                style={{
                                  fontSize: "12px",
                                  fontWeight: 800,
                                  padding: "3px 9px",
                                  borderRadius: "8px",
                                  background:
                                    job.match_score >= 80
                                      ? "rgba(16,185,129,0.2)"
                                      : job.match_score >= 60
                                      ? "rgba(99,102,241,0.2)"
                                      : "rgba(245,158,11,0.2)",
                                  color: job.match_score >= 80 ? "#6ee7b7" : job.match_score >= 60 ? "#a5b4fc" : "#fcd34d",
                                }}
                              >
                                {job.match_score}%
                              </span>
                              {jobApplyUrl && (
                                <a
                                  href={jobApplyUrl}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "4px",
                                    fontSize: "11px",
                                    fontWeight: 600,
                                    padding: "3px 8px",
                                    borderRadius: "6px",
                                    background: "rgba(99,102,241,0.2)",
                                    border: "1px solid rgba(99,102,241,0.4)",
                                    color: "#c7d2fe",
                                    textDecoration: "none",
                                  }}
                                >
                                  <ExternalLink size={11} /> Company Site
                                </a>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Modal Footer Actions */}
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
                  <Link
                    href="/applications"
                    className="btn-primary"
                    style={{ fontSize: "13px", padding: "8px 16px", textDecoration: "none" }}
                    onClick={() => setModalState(null)}
                  >
                    Go to Applications Queue <ArrowRight size={14} />
                  </Link>
                  <button className="btn-secondary" onClick={() => setModalState(null)}>
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
