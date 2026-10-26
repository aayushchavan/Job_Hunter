"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { jobsApi, applicationsApi } from "@/lib/api";
import { useToast } from "@/components/ui/ToastProvider";
import {
  Search,
  MapPin,
  Wifi,
  Plus,
  ExternalLink,
  X,
  Loader2,
  Briefcase,
  Building2,
  DollarSign,
  Clock,
  Filter,
  Info,
  Sparkles,
  Compass,
  CheckCircle2,
  AlertCircle,
  SlidersHorizontal,
  Globe,
  Award,
  Target,
} from "lucide-react";
import { getMatchColor, formatRelativeTime } from "@/lib/utils";

interface Job {
  id: string;
  title: string;
  company_name?: string;
  company?: string;
  location?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  match_score?: number;
  discovered_at: string;
  application_url?: string;
  canonical_url?: string;
  experience_min_years?: number;
  experience_max_years?: number;
  job_url?: string;
  description?: string;
  required_skills?: string[];
  work_mode?: string;
  employment_type?: string;
  source_name?: string;
  source?: string;
}

const POPULAR_ROLES = [
  "Full Stack Developer",
  "Frontend React",
  "Python Developer",
  "DevOps Engineer",
  "Data Scientist",
  "Backend Node.js",
  "AI / ML Engineer",
  "Product Manager",
  "Java Developer",
];

const EXPERIENCE_PRESETS = [
  { id: "all", label: "All Experience", desc: "No experience restriction", min: undefined, max: undefined },
  { id: "0-2", label: "Entry (0–2 yrs)", desc: "Freshers, Juniors, Associates", min: 0, max: 2 },
  { id: "2-5", label: "Mid (2–5 yrs)", desc: "Intermediate Developers", min: 2, max: 5 },
  { id: "5-8", label: "Senior (5–8 yrs)", desc: "Senior Engineers", min: 5, max: 8 },
  { id: "8+", label: "Lead / Staff (8+ yrs)", desc: "Principals, Tech Leads, Architects", min: 8, max: undefined },
  { id: "custom", label: "Custom Range ⚙️", desc: "Choose specific min & max years", min: undefined, max: undefined },
];

export default function JobsPage() {
  // Discovery criteria state
  const [keywords, setKeywords] = useState<string[]>(["Python"]);
  const [kwInput, setKwInput] = useState("");
  const [location, setLocation] = useState("India");
  const [remote, setRemote] = useState(false);
  const [resultsCount, setResultsCount] = useState(20);

  // Experience range state for discovery
  const [expPreset, setExpPreset] = useState<string>("all");
  const [customExpMin, setCustomExpMin] = useState<number | "">("");
  const [customExpMax, setCustomExpMax] = useState<number | "">("");

  // Local/Live Database filters (Universal Search)
  const [dbSearch, setDbSearch] = useState("");
  const [selectedWorkMode, setSelectedWorkMode] = useState<string>("all");
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [filterExpLevel, setFilterExpLevel] = useState<string>("all");
  const [minScore, setMinScore] = useState(0);

  const { toast } = useToast();
  const queryClient = useQueryClient();

  const getExpRange = (preset: string, minInput: number | "", maxInput: number | ""): { min?: number; max?: number } => {
    if (preset === "custom") {
      return {
        min: typeof minInput === "number" ? minInput : undefined,
        max: typeof maxInput === "number" ? maxInput : undefined,
      };
    }
    const found = EXPERIENCE_PRESETS.find((p) => p.id === preset);
    return { min: found?.min, max: found?.max };
  };

  const formatExperience = (min?: number, max?: number) => {
    if (min === undefined && max === undefined) return null;
    if (min !== undefined && max !== undefined) {
      if (min === 0 && max <= 2) return `0–${max} yrs (Entry)`;
      return `${min}–${max} yrs exp`;
    }
    if (min !== undefined) {
      return `${min}+ yrs exp`;
    }
    if (max !== undefined) {
      return `Up to ${max} yrs exp`;
    }
    return null;
  };

  const { min: dbExpMin, max: dbExpMax } = getExpRange(filterExpLevel, "", "");

  // Query jobs from database
  const { data: jobsData, isLoading: listLoading } = useQuery({
    queryKey: [
      "jobs",
      {
        min_score: minScore,
        search: dbSearch,
        work_mode: selectedWorkMode,
        expMin: dbExpMin,
        expMax: dbExpMax,
      },
    ],
    queryFn: () =>
      jobsApi
        .list({
          page_size: 50,
          min_score: minScore > 0 ? minScore : undefined,
          search: dbSearch.trim() || undefined,
          work_mode: selectedWorkMode !== "all" ? selectedWorkMode : undefined,
          experience_min_years: dbExpMin,
          experience_max_years: dbExpMax,
        })
        .then((r) => r.data),
  });

  // Extract jobs array safely
  const rawJobs: Job[] = useMemo(() => {
    return jobsData?.items ?? jobsData?.jobs ?? [];
  }, [jobsData]);

  // Client-side fallback filter if backend search was partial + source filtering + experience
  const filteredJobs = useMemo(() => {
    let list = rawJobs;
    if (selectedSource !== "all") {
      list = list.filter((j) => (j.source_name || j.source || "").toLowerCase().includes(selectedSource.toLowerCase()));
    }
    if (filterExpLevel !== "all") {
      const { min: targetMin, max: targetMax } = getExpRange(filterExpLevel, "", "");
      list = list.filter((j) => {
        const jMin = j.experience_min_years;
        const jMax = j.experience_max_years;
        if (jMin === undefined && jMax === undefined) {
          const title = (j.title || "").toLowerCase();
          if (filterExpLevel === "0-2") {
            return title.includes("junior") || title.includes("entry") || title.includes("intern") || title.includes("associate") || title.includes("fresher");
          }
          if (filterExpLevel === "5-8") {
            return title.includes("senior") || title.includes("sr");
          }
          if (filterExpLevel === "8+") {
            return title.includes("lead") || title.includes("principal") || title.includes("staff") || title.includes("architect");
          }
          if (filterExpLevel === "2-5") {
            return !title.includes("senior") && !title.includes("lead") && !title.includes("junior") && !title.includes("intern");
          }
          return true;
        }
        if (targetMin !== undefined && jMax !== undefined && jMax < targetMin) return false;
        if (targetMax !== undefined && jMin !== undefined && jMin > targetMax) return false;
        return true;
      });
    }
    if (!dbSearch.trim()) return list;
    const term = dbSearch.toLowerCase();
    return list.filter((j) => {
      const title = (j.title || "").toLowerCase();
      const comp = (j.company_name || j.company || "").toLowerCase();
      const loc = (j.location || "").toLowerCase();
      const skills = (j.required_skills || []).join(" ").toLowerCase();
      const src = (j.source_name || j.source || "").toLowerCase();
      return (
        title.includes(term) ||
        comp.includes(term) ||
        loc.includes(term) ||
        skills.includes(term) ||
        src.includes(term)
      );
    });
  }, [rawJobs, dbSearch, selectedSource, filterExpLevel]);

  // Discover jobs mutation
  const discoverMutation = useMutation({
    mutationFn: () => {
      if (keywords.length === 0 && !kwInput.trim()) {
        throw new Error("REQUIRED_CRITERIA_MISSING");
      }
      const activeKeywords = keywords.length > 0 ? keywords : [kwInput.trim()];
      const { min: expMin, max: expMax } = getExpRange(expPreset, customExpMin, customExpMax);
      return jobsApi.discover({
        keywords: activeKeywords,
        location: location.trim() || undefined,
        remote,
        results_per_page: resultsCount,
        experience_min_years: expMin,
        experience_max_years: expMax,
      });
    },
    onSuccess: (res) => {
      const stats = res.data?.stats;
      const count = stats?.jobs_new ?? stats?.jobs_fetched ?? res.data?.jobs_saved ?? 0;
      toast(`Discovered ${count} fresh jobs across the internet! 🌐🎯`, "success");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["job-stats"] });
    },
    onError: (err: any) => {
      if (err.message === "REQUIRED_CRITERIA_MISSING") {
        toast("Please enter at least 1 job keyword or select a role!", "warning");
      } else {
        const msg = err.response?.data?.detail ?? "Failed to discover jobs. Check API configuration.";
        toast(msg, "error");
      }
    },
  });

  const applyMutation = useMutation({
    mutationFn: (jobId: string) => applicationsApi.create({ job_id: jobId }),
    onSuccess: () => {
      toast("Added to application queue! ✅", "success");
      queryClient.invalidateQueries({ queryKey: ["app-stats"] });
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to queue application";
      toast(msg, "error");
    },
  });

  const addKeyword = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    if (!keywords.includes(trimmed)) {
      setKeywords([...keywords, trimmed]);
    }
    setKwInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addKeyword(kwInput);
    }
  };

  const removeKeyword = (kw: string) => setKeywords(keywords.filter((k) => k !== kw));

  const formatSalary = (min?: number, max?: number, curr?: string) => {
    if (!min && !max) return null;
    const symbol = curr === "USD" ? "$" : curr === "EUR" ? "€" : "₹";
    const fmt = (n: number) => {
      if (curr === "INR" || !curr) {
        return n >= 100000 ? `${symbol}${(n / 100000).toFixed(1)}L` : `${symbol}${(n / 1000).toFixed(0)}k`;
      }
      return `${symbol}${(n / 1000).toFixed(0)}k`;
    };
    if (min && max) return `${fmt(min)} – ${fmt(max)}`;
    if (min) return `${fmt(min)}+`;
    return `Up to ${fmt(max!)}`;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <h1 style={{ fontSize: "26px", fontWeight: 800, color: "white", letterSpacing: "-0.5px" }}>
              Job Search & Discovery
            </h1>
            <span
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: "#10b981",
                background: "rgba(16,185,129,0.15)",
                border: "1px solid rgba(16,185,129,0.3)",
                padding: "2px 10px",
                borderRadius: "20px",
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
              }}
            >
              <Compass size={13} />
              Open Search — No Resume Required
            </span>
          </div>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Search for any job role, tech stack, or company across the market regardless of your current resume.
          </p>
        </div>
      </div>

      {/* ── Global Internet Job Engines Status Banner ──────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
          background: "linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(99,102,241,0.08) 100%)",
          border: "1px solid rgba(16,185,129,0.25)",
          borderRadius: "14px",
          padding: "14px 20px",
          boxShadow: "0 4px 20px rgba(0,0,0,0.25)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              background: "rgba(16,185,129,0.2)",
              border: "1px solid rgba(16,185,129,0.35)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#34d399",
            }}
          >
            <Globe size={20} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "14px", fontWeight: 700, color: "white" }}>
                Universal Internet Job Search
              </span>
              <span
                style={{
                  fontSize: "10px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  padding: "1px 6px",
                  borderRadius: "4px",
                  background: "rgba(16,185,129,0.2)",
                  color: "#6ee7b7",
                  border: "1px solid rgba(16,185,129,0.4)",
                }}
              >
                12 Engines Active
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "2px 0 0" }}>
              Aggregating live tech openings across LinkedIn, Hacker News, RemoteOK, WWR, and 8 global job engines simultaneously
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
          {[
            { name: "LinkedIn", type: "Public Global" },
            { name: "RemoteOK", type: "Worldwide Tech & AI" },
            { name: "We Work Remotely", type: "Premier Tech" },
            { name: "Hacker News", type: "YC Startups & Founders" },
            { name: "Jobspresso", type: "Curated Remote & ATS" },
            { name: "Working Nomads", type: "Global Engineering" },
            { name: "Remotive", type: "Global Remote" },
            { name: "Arbeitnow", type: "US & EU Tech" },
            { name: "Himalayas", type: "Worldwide Remote" },
            { name: "The Muse", type: "Enterprise Tech" },
            { name: "Jobicy", type: "Software & DevOps" },
            { name: "Adzuna", type: "India & Global" },
          ].map((src) => (
            <span
              key={src.name}
              style={{
                fontSize: "11px",
                fontWeight: 600,
                color: "#6ee7b7",
                background: "rgba(16,185,129,0.1)",
                border: "1px solid rgba(16,185,129,0.25)",
                borderRadius: "6px",
                padding: "3px 9px",
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
              }}
              title={src.type}
            >
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981", boxShadow: "0 0 6px #10b981" }} />
              {src.name}
            </span>
          ))}
        </div>
      </div>

      {/* ── Search Criteria Requirements Panel ──────────────────────────────── */}
      <div
        className="glass-card"
        style={{
          padding: "22px 24px",
          border: "1px solid rgba(99,102,241,0.25)",
          background: "linear-gradient(135deg, rgba(30,27,75,0.4) 0%, rgba(15,23,42,0.6) 100%)",
        }}
      >
        {/* Criteria Explanation Banner */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "12px",
            background: "rgba(99,102,241,0.1)",
            border: "1px solid rgba(99,102,241,0.2)",
            borderRadius: "10px",
            padding: "12px 16px",
            marginBottom: "18px",
          }}
        >
          <Info size={18} color="#818cf8" style={{ marginTop: "2px", flexShrink: 0 }} />
          <div style={{ fontSize: "13px", lineHeight: "1.5" }}>
            <span style={{ fontWeight: 700, color: "#e0e7ff" }}>Search Criteria Requirements: </span>
            <span style={{ color: "var(--text-secondary)" }}>
              <b style={{ color: "#f43f5e" }}>* Role / Keywords (Required)</b> — enter the job title or technology.{" "}
              <b style={{ color: "#94a3b8" }}>Location & Remote (Optional)</b> — filter by your preferred city or remote setup.
              You can search for <b>any role in the market</b> regardless of what is on your resume!
            </span>
          </div>
        </div>

        {/* Search Inputs Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 220px auto auto", gap: "14px", alignItems: "flex-end" }}>
          {/* 1. Keywords (Required) */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <label
                style={{
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#cbd5e1",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <span>Job Title / Keywords</span>
                <span style={{ color: "#f43f5e", fontSize: "14px" }}>*</span>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 600,
                    color: "#f43f5e",
                    background: "rgba(244,63,94,0.15)",
                    border: "1px solid rgba(244,63,94,0.3)",
                    padding: "1px 6px",
                    borderRadius: "4px",
                    textTransform: "none",
                  }}
                >
                  Required
                </span>
              </label>
              {keywords.length > 0 && (
                <button
                  onClick={() => setKeywords([])}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    fontSize: "11px",
                    cursor: "pointer",
                    textDecoration: "underline",
                  }}
                >
                  Clear all
                </button>
              )}
            </div>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "6px",
                background: "rgba(255,255,255,0.04)",
                border: keywords.length === 0 ? "1px solid rgba(244,63,94,0.4)" : "1px solid var(--border)",
                borderRadius: "10px",
                padding: "8px 12px",
                minHeight: "46px",
                alignItems: "center",
              }}
            >
              {keywords.map((kw) => (
                <span
                  key={kw}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "rgba(99,102,241,0.25)",
                    border: "1px solid rgba(99,102,241,0.4)",
                    color: "#c7d2fe",
                    borderRadius: "6px",
                    padding: "3px 10px",
                    fontSize: "12px",
                    fontWeight: 600,
                  }}
                >
                  {kw}
                  <button
                    onClick={() => removeKeyword(kw)}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      color: "#c7d2fe",
                      display: "flex",
                      padding: 0,
                    }}
                    title="Remove keyword"
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}

              <input
                value={kwInput}
                onChange={(e) => setKwInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={keywords.length === 0 ? "Type role (e.g. React Developer) and press Enter *" : "Add more..."}
                style={{
                  border: "none",
                  background: "none",
                  outline: "none",
                  color: "white",
                  fontSize: "13px",
                  flex: 1,
                  minWidth: "160px",
                  fontFamily: "inherit",
                }}
                id="keyword-input"
              />

              {kwInput.trim() && (
                <button
                  onClick={() => addKeyword(kwInput)}
                  style={{
                    background: "rgba(99,102,241,0.4)",
                    border: "none",
                    borderRadius: "4px",
                    color: "white",
                    fontSize: "11px",
                    padding: "2px 8px",
                    cursor: "pointer",
                  }}
                >
                  Add +
                </button>
              )}
            </div>
          </div>

          {/* 2. Location (Optional) */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <label
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Location <span style={{ color: "var(--text-muted)", fontSize: "11px", fontWeight: 400 }}>(Optional)</span>
              </label>
            </div>
            <div style={{ position: "relative" }}>
              <MapPin
                size={15}
                style={{
                  position: "absolute",
                  left: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--text-muted)",
                }}
              />
              <input
                className="input-field"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. India, Bangalore, or Remote"
                style={{ paddingLeft: "36px", width: "100%" }}
                id="location-input"
              />
            </div>
          </div>

          {/* 3. Remote Toggle (Optional) */}
          <div>
            <label
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--text-secondary)",
                display: "block",
                marginBottom: "8px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Remote
            </label>
            <button
              onClick={() => setRemote(!remote)}
              style={{
                height: "46px",
                padding: "0 16px",
                borderRadius: "10px",
                border: `1px solid ${remote ? "rgba(99,102,241,0.5)" : "var(--border)"}`,
                background: remote ? "rgba(99,102,241,0.2)" : "rgba(255,255,255,0.04)",
                color: remote ? "#a5b4fc" : "var(--text-muted)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "13px",
                fontWeight: 600,
                fontFamily: "inherit",
                transition: "all 0.2s",
              }}
              id="remote-toggle"
            >
              <Wifi size={15} />
              {remote ? "Remote Only ✓" : "Any Mode"}
            </button>
          </div>

          {/* 4. Discover Button */}
          <div>
            <label style={{ display: "block", marginBottom: "8px", opacity: 0 }}>Discover</label>
            <button
              className="btn-primary"
              onClick={() => discoverMutation.mutate()}
              disabled={discoverMutation.isPending}
              style={{
                height: "46px",
                padding: "0 22px",
                fontWeight: 700,
                fontSize: "14px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "linear-gradient(135deg, #10b981 0%, #6366f1 100%)",
                boxShadow: "0 4px 18px rgba(16,185,129,0.3)",
              }}
              id="discover-btn"
            >
              {discoverMutation.isPending ? (
                <Loader2 size={16} style={{ animation: "spin 0.7s linear infinite" }} />
              ) : (
                <Globe size={16} />
              )}
              {discoverMutation.isPending ? "Searching All Internet Sources..." : "Search All Over The Internet"}
            </button>
          </div>
        </div>

        {/* ── Experience Range Selector ─────────────────────────────── */}
        <div
          style={{
            marginTop: "16px",
            padding: "14px 18px",
            borderRadius: "12px",
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.07)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Award size={16} color="#c084fc" />
            <span style={{ fontSize: "12px", fontWeight: 700, color: "#e2e8f0", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Years of Experience Range:
            </span>
            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              (Target candidate seniority for internet discovery)
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            {EXPERIENCE_PRESETS.map((preset) => {
              const active = expPreset === preset.id;
              return (
                <button
                  key={preset.id}
                  onClick={() => setExpPreset(preset.id)}
                  title={preset.desc}
                  style={{
                    padding: "5px 12px",
                    borderRadius: "8px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                    border: active ? "1px solid rgba(192,132,252,0.6)" : "1px solid rgba(255,255,255,0.08)",
                    background: active ? "rgba(192,132,252,0.22)" : "rgba(255,255,255,0.03)",
                    color: active ? "#e9d5ff" : "var(--text-secondary)",
                    transition: "all 0.15s ease",
                  }}
                >
                  {preset.label}
                </button>
              );
            })}

            {/* Custom Min / Max Inputs */}
            {expPreset === "custom" && (
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginLeft: "4px" }}>
                <input
                  type="number"
                  min={0}
                  max={40}
                  placeholder="Min"
                  value={customExpMin}
                  onChange={(e) => setCustomExpMin(e.target.value === "" ? "" : Math.max(0, parseInt(e.target.value) || 0))}
                  style={{
                    width: "60px",
                    padding: "5px 8px",
                    borderRadius: "6px",
                    border: "1px solid rgba(192,132,252,0.4)",
                    background: "rgba(0,0,0,0.3)",
                    color: "white",
                    fontSize: "12px",
                    textAlign: "center",
                  }}
                />
                <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>to</span>
                <input
                  type="number"
                  min={0}
                  max={50}
                  placeholder="Max"
                  value={customExpMax}
                  onChange={(e) => setCustomExpMax(e.target.value === "" ? "" : Math.max(0, parseInt(e.target.value) || 0))}
                  style={{
                    width: "60px",
                    padding: "5px 8px",
                    borderRadius: "6px",
                    border: "1px solid rgba(192,132,252,0.4)",
                    background: "rgba(0,0,0,0.3)",
                    color: "white",
                    fontSize: "12px",
                    textAlign: "center",
                  }}
                />
                <span style={{ color: "#c084fc", fontSize: "11px", fontWeight: 600 }}>years</span>
              </div>
            )}
          </div>
        </div>

        {/* Quick Suggestion Chips */}
        <div style={{ marginTop: "16px", display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>
            Quick suggestions:
          </span>
          {POPULAR_ROLES.map((role) => {
            const isSelected = keywords.includes(role);
            return (
              <button
                key={role}
                onClick={() => {
                  if (isSelected) {
                    removeKeyword(role);
                  } else {
                    addKeyword(role);
                  }
                }}
                style={{
                  fontSize: "11px",
                  fontWeight: 500,
                  padding: "3px 10px",
                  borderRadius: "20px",
                  border: isSelected
                    ? "1px solid rgba(99,102,241,0.6)"
                    : "1px solid rgba(255,255,255,0.08)",
                  background: isSelected ? "rgba(99,102,241,0.25)" : "rgba(255,255,255,0.03)",
                  color: isSelected ? "#c7d2fe" : "var(--text-secondary)",
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                {isSelected ? `✓ ${role}` : `+ ${role}`}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Universal Job Searching Dashboard (Explore & Filter) ────────────── */}
      <div
        className="glass-card"
        style={{
          padding: "18px 24px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <SlidersHorizontal size={18} color="#818cf8" />
            <h2 style={{ fontSize: "17px", fontWeight: 700, color: "white" }}>
              Common Job Search Dashboard
            </h2>
            <span
              style={{
                fontSize: "12px",
                background: "rgba(255,255,255,0.08)",
                padding: "2px 8px",
                borderRadius: "12px",
                color: "var(--text-secondary)",
                fontWeight: 600,
              }}
            >
              {filteredJobs.length} {filteredJobs.length === 1 ? "job" : "jobs"} available
            </span>
          </div>

          {/* Quick Filter Controls: Mode + Source */}
          <div style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" }}>
            {/* Work Mode */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Mode:</span>
              {[
                { id: "all", label: "All" },
                { id: "remote", label: "Remote" },
                { id: "hybrid", label: "Hybrid" },
                { id: "onsite", label: "Onsite" },
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setSelectedWorkMode(m.id)}
                  style={{
                    padding: "4px 8px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: 500,
                    cursor: "pointer",
                    border: `1px solid ${selectedWorkMode === m.id ? "rgba(99,102,241,0.5)" : "var(--border)"}`,
                    background: selectedWorkMode === m.id ? "rgba(99,102,241,0.2)" : "transparent",
                    color: selectedWorkMode === m.id ? "#a5b4fc" : "var(--text-muted)",
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>

            {/* Source */}
            <div style={{ display: "flex", alignItems: "center", gap: "5px", flexWrap: "wrap" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                <Globe size={13} color="#34d399" /> Source:
              </span>
              {[
                { id: "all", label: "All" },
                { id: "linkedin", label: "LinkedIn" },
                { id: "hackernews", label: "Hacker News" },
                { id: "remoteok", label: "RemoteOK" },
                { id: "weworkremotely", label: "WWR" },
                { id: "jobspresso", label: "Jobspresso" },
                { id: "workingnomads", label: "Working Nomads" },
                { id: "remotive", label: "Remotive" },
                { id: "arbeitnow", label: "Arbeitnow" },
                { id: "himalayas", label: "Himalayas" },
                { id: "themuse", label: "The Muse" },
                { id: "jobicy", label: "Jobicy" },
                { id: "adzuna", label: "Adzuna" },
              ].map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedSource(s.id)}
                  style={{
                    padding: "4px 8px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                    border: `1px solid ${selectedSource === s.id ? "rgba(16,185,129,0.5)" : "var(--border)"}`,
                    background: selectedSource === s.id ? "rgba(16,185,129,0.2)" : "transparent",
                    color: selectedSource === s.id ? "#6ee7b7" : "var(--text-muted)",
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>

            {/* Experience Level Filter */}
            <div style={{ display: "flex", alignItems: "center", gap: "5px", flexWrap: "wrap" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                <Award size={13} color="#c084fc" /> Exp:
              </span>
              {[
                { id: "all", label: "All" },
                { id: "0-2", label: "0–2y" },
                { id: "2-5", label: "2–5y" },
                { id: "5-8", label: "5–8y" },
                { id: "8+", label: "8y+" },
              ].map((ep) => (
                <button
                  key={ep.id}
                  onClick={() => setFilterExpLevel(ep.id)}
                  style={{
                    padding: "4px 8px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                    border: `1px solid ${filterExpLevel === ep.id ? "rgba(192,132,252,0.5)" : "var(--border)"}`,
                    background: filterExpLevel === ep.id ? "rgba(192,132,252,0.2)" : "transparent",
                    color: filterExpLevel === ep.id ? "#e9d5ff" : "var(--text-muted)",
                  }}
                >
                  {ep.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Live Filter Bar */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "14px", alignItems: "center" }}>
          {/* Instant Search Bar */}
          <div style={{ position: "relative" }}>
            <Search
              size={16}
              style={{
                position: "absolute",
                left: "14px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-muted)",
              }}
            />
            <input
              className="input-field"
              value={dbSearch}
              onChange={(e) => setDbSearch(e.target.value)}
              placeholder="Search across all jobs by Title, Company, or Skill (e.g. 'Engineer', 'Cisco', 'Python')..."
              style={{ paddingLeft: "40px", width: "100%", fontSize: "13px" }}
              id="instant-search-input"
            />
            {dbSearch && (
              <button
                onClick={() => setDbSearch("")}
                style={{
                  position: "absolute",
                  right: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Match Score Filter */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Filter size={14} color="var(--text-muted)" />
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Match:</span>
            {[
              { val: 0, label: "All (Any)" },
              { val: 50, label: "50%+" },
              { val: 70, label: "70%+" },
            ].map((s) => (
              <button
                key={s.val}
                onClick={() => setMinScore(s.val)}
                style={{
                  padding: "4px 10px",
                  borderRadius: "6px",
                  border: `1px solid ${minScore === s.val ? "rgba(99,102,241,0.5)" : "var(--border)"}`,
                  background: minScore === s.val ? "rgba(99,102,241,0.15)" : "transparent",
                  color: minScore === s.val ? "#a5b4fc" : "var(--text-muted)",
                  fontSize: "12px",
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Jobs Grid ──────────────────────────────────────────────────────── */}
      {listLoading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "16px" }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton" style={{ height: "180px", borderRadius: "16px" }} />
          ))}
        </div>
      ) : filteredJobs.length === 0 ? (
        <div
          className="glass-card"
          style={{ textAlign: "center", padding: "60px 32px", borderRadius: "16px" }}
        >
          <Briefcase size={48} style={{ margin: "0 auto 16px", opacity: 0.3, color: "#818cf8" }} />
          <h3 style={{ fontSize: "18px", fontWeight: 700, color: "white", marginBottom: "8px" }}>
            {dbSearch ? "No jobs match your search" : "No jobs discovered yet"}
          </h3>
          <p style={{ color: "var(--text-muted)", fontSize: "14px", maxWidth: "460px", margin: "0 auto 20px" }}>
            {dbSearch
              ? `No jobs found containing "${dbSearch}". Try clearing your search query or discover new jobs above.`
              : "Use the Search Criteria panel above to search and discover live jobs from the web."}
          </p>
          {dbSearch ? (
            <button
              className="btn-secondary"
              onClick={() => setDbSearch("")}
              style={{ margin: "0 auto" }}
            >
              Clear Search Filter
            </button>
          ) : (
            <button
              className="btn-primary"
              onClick={() => discoverMutation.mutate()}
              disabled={discoverMutation.isPending}
              style={{ margin: "0 auto" }}
            >
              <Sparkles size={16} />
              Discover Jobs Now
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "16px" }}>
          {filteredJobs.map((job) => {
            const companyName = job.company_name || job.company || "Company";
            const applyUrl = job.application_url || job.job_url || job.canonical_url;

            return (
              <div
                key={job.id}
                className="glass-card-hover"
                style={{
                  padding: "22px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  borderRadius: "14px",
                  border: "1px solid rgba(255,255,255,0.07)",
                }}
              >
                <div>
                  {/* Job Header */}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      marginBottom: "12px",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0, marginRight: "12px" }}>
                      <div
                        style={{
                          fontSize: "16px",
                          fontWeight: 700,
                          color: "white",
                          marginBottom: "4px",
                          lineHeight: 1.3,
                        }}
                      >
                        {job.title}
                      </div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          color: "var(--text-muted)",
                          fontSize: "13px",
                        }}
                      >
                        <Building2 size={13} color="#818cf8" />
                        <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>
                          {companyName}
                        </span>
                      </div>
                    </div>

                    {job.match_score !== undefined && job.match_score !== null ? (
                      <span className={`badge ${getMatchColor(job.match_score)}`}>
                        {Math.round(job.match_score)}% match
                      </span>
                    ) : (
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 500,
                          color: "#94a3b8",
                          background: "rgba(255,255,255,0.05)",
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        Market Role
                      </span>
                    )}
                  </div>

                  {/* Meta Pills */}
                  <div
                    style={{
                      display: "flex",
                      gap: "12px",
                      marginBottom: "14px",
                      flexWrap: "wrap",
                    }}
                  >
                    {job.location && (
                      <span
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "12px",
                          color: "var(--text-muted)",
                        }}
                      >
                        <MapPin size={12} /> {job.location}
                      </span>
                    )}

                    {job.work_mode && (
                      <span
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "11px",
                          color: job.work_mode === "remote" ? "#34d399" : "var(--text-muted)",
                          background:
                            job.work_mode === "remote"
                              ? "rgba(52,211,153,0.1)"
                              : "rgba(255,255,255,0.05)",
                          padding: "1px 8px",
                          borderRadius: "4px",
                          textTransform: "capitalize",
                        }}
                      >
                        <Wifi size={11} /> {job.work_mode}
                      </span>
                    )}

                    {formatSalary(job.salary_min, job.salary_max, job.salary_currency) && (
                      <span
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "12px",
                          color: "#34d399",
                          fontWeight: 600,
                        }}
                      >
                        <DollarSign size={12} />{" "}
                        {formatSalary(job.salary_min, job.salary_max, job.salary_currency)}
                      </span>
                    )}

                    {formatExperience(job.experience_min_years, job.experience_max_years) && (
                      <span
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "12px",
                          color: "#c084fc",
                          background: "rgba(192,132,252,0.12)",
                          border: "1px solid rgba(192,132,252,0.25)",
                          padding: "1px 8px",
                          borderRadius: "4px",
                          fontWeight: 600,
                        }}
                      >
                        <Award size={12} color="#c084fc" />
                        {formatExperience(job.experience_min_years, job.experience_max_years)}
                      </span>
                    )}

                    <span
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "12px",
                        color: "var(--text-muted)",
                      }}
                    >
                      <Clock size={12} /> {formatRelativeTime(job.discovered_at)}
                    </span>

                    {(job.source_name || job.source) && (
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "11px",
                          color: "#6ee7b7",
                          background: "rgba(16,185,129,0.12)",
                          border: "1px solid rgba(16,185,129,0.25)",
                          padding: "1px 8px",
                          borderRadius: "4px",
                          textTransform: "capitalize",
                          fontWeight: 600,
                        }}
                      >
                        🌐 {job.source_name || job.source}
                      </span>
                    )}
                  </div>

                  {/* Skills Tags */}
                  {job.required_skills && job.required_skills.length > 0 && (
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "5px",
                        marginBottom: "16px",
                      }}
                    >
                      {job.required_skills.slice(0, 5).map((skill) => (
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
                      {job.required_skills.length > 5 && (
                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                          +{job.required_skills.length - 5} more
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Actions Footer */}
                <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
                  <button
                    className="btn-primary"
                    onClick={() => applyMutation.mutate(job.id)}
                    disabled={applyMutation.isPending}
                    style={{
                      fontSize: "13px",
                      padding: "8px 14px",
                      flex: 1,
                      justifyContent: "center",
                    }}
                  >
                    <Plus size={14} />
                    Add to Queue
                  </button>

                  {applyUrl && (
                    <a
                      href={applyUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-secondary"
                      style={{
                        fontSize: "13px",
                        padding: "8px 14px",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <ExternalLink size={13} />
                      Company Apply Site
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
