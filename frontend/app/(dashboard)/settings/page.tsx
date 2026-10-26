"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi, settingsApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { useToast } from "@/components/ui/ToastProvider";
import {
  User,
  Sliders,
  Cpu,
  Save,
  CheckCircle,
  AlertTriangle,
  Shield,
  Zap,
  Globe,
  Briefcase,
  Link2,
  Phone,
  Mail,
  MapPin,
  Clock,
  Sparkles,
  Loader2,
} from "lucide-react";
import { getMatchColor, getScoreHex } from "@/lib/utils";

interface ProfileFormData {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  city: string;
  state: string;
  country: string;
  current_title: string;
  current_company: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
}

interface AutoApplyFormData {
  is_enabled: boolean;
  mode: "safe" | "auto";
  min_match_score: number;
  max_applications_per_day: number;
  delay_min_seconds: number;
  delay_max_seconds: number;
  max_retries: number;
  require_approval_before_submit: boolean;
  is_test_mode: boolean;
}

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Profile state
  const [profileForm, setProfileForm] = useState<ProfileFormData>({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    city: "",
    state: "",
    country: "",
    current_title: "",
    current_company: "",
    linkedin_url: "",
    github_url: "",
    portfolio_url: "",
  });

  // Auto-apply state
  const [autoApplyForm, setAutoApplyForm] = useState<AutoApplyFormData>({
    is_enabled: false,
    mode: "safe",
    min_match_score: 90,
    max_applications_per_day: 10,
    delay_min_seconds: 30,
    delay_max_seconds: 120,
    max_retries: 3,
    require_approval_before_submit: true,
    is_test_mode: true,
  });

  // Fetch current user
  const { data: meData, isLoading: meLoading } = useQuery({
    queryKey: ["authMe"],
    queryFn: () => authApi.me().then((r) => r.data),
  });

  // Fetch auto-apply settings
  const { data: settingsData, isLoading: settingsLoading } = useQuery({
    queryKey: ["autoApplySettings"],
    queryFn: () => settingsApi.getAutoApply().then((r) => r.data),
  });

  useEffect(() => {
    if (meData) {
      setProfileForm({
        first_name: meData.first_name || "",
        last_name: meData.last_name || "",
        email: meData.email || "",
        phone: meData.phone || "",
        city: meData.city || "",
        state: meData.state || "",
        country: meData.country || "",
        current_title: meData.current_title || "",
        current_company: meData.current_company || "",
        linkedin_url: meData.linkedin_url || "",
        github_url: meData.github_url || "",
        portfolio_url: meData.portfolio_url || "",
      });
    }
  }, [meData]);

  useEffect(() => {
    if (settingsData) {
      setAutoApplyForm({
        is_enabled: Boolean(settingsData.is_enabled),
        mode: settingsData.mode || "safe",
        min_match_score: Number(settingsData.min_match_score ?? 90),
        max_applications_per_day: Number(settingsData.max_applications_per_day ?? 10),
        delay_min_seconds: Number(settingsData.delay_min_seconds ?? 30),
        delay_max_seconds: Number(settingsData.delay_max_seconds ?? 120),
        max_retries: Number(settingsData.max_retries ?? 3),
        require_approval_before_submit: Boolean(settingsData.require_approval_before_submit ?? true),
        is_test_mode: Boolean(settingsData.is_test_mode ?? true),
      });
    }
  }, [settingsData]);

  // Profile mutation
  const profileMutation = useMutation({
    mutationFn: (data: Partial<ProfileFormData>) => authApi.updateMe(data),
    onSuccess: (res) => {
      toast("Profile updated successfully! ✨", "success");
      updateUser(res.data);
      queryClient.invalidateQueries({ queryKey: ["authMe"] });
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to update profile";
      toast(msg, "error");
    },
  });

  // Auto-apply settings mutation
  const autoApplyMutation = useMutation({
    mutationFn: (data: AutoApplyFormData) => settingsApi.updateAutoApply(data),
    onSuccess: () => {
      toast("Auto-Apply settings saved! 🚀", "success");
      queryClient.invalidateQueries({ queryKey: ["autoApplySettings"] });
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to save auto-apply settings";
      toast(msg, "error");
    },
  });

  const handleProfileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    profileMutation.mutate(profileForm);
  };

  const handleAutoApplySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    autoApplyMutation.mutate(autoApplyForm);
  };

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", paddingBottom: "60px" }}>
      {/* Header */}
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: 800, color: "white", marginBottom: "8px" }}>
          Settings & Preferences
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
          Manage your personal profile, auto-apply automation parameters, and AI engine preferences.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
        {/* 1. Profile Section */}
        <div className="glass-card" style={{ padding: "28px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "20px",
              paddingBottom: "16px",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "rgba(99,102,241,0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#6366f1",
              }}
            >
              <User size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "white" }}>Candidate Profile</h2>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                Information used by AI to automatically fill job application forms
              </p>
            </div>
          </div>

          {meLoading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}>
              <Loader2 className="animate-spin" size={24} color="#6366f1" />
            </div>
          ) : (
            <form onSubmit={handleProfileSubmit}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                  gap: "18px",
                  marginBottom: "20px",
                }}
              >
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                    First Name *
                  </label>
                  <input
                    type="text"
                    required
                    className="input-field"
                    value={profileForm.first_name}
                    onChange={(e) => setProfileForm({ ...profileForm, first_name: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Last Name
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    value={profileForm.last_name}
                    onChange={(e) => setProfileForm({ ...profileForm, last_name: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Email Address *
                  </label>
                  <div style={{ position: "relative" }}>
                    <input
                      type="email"
                      disabled
                      className="input-field"
                      style={{ opacity: 0.7, cursor: "not-allowed", paddingLeft: "36px" }}
                      value={profileForm.email}
                    />
                    <Mail size={16} style={{ position: "absolute", left: "12px", top: "14px", color: "var(--text-muted)" }} />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Phone Number
                  </label>
                  <div style={{ position: "relative" }}>
                    <input
                      type="text"
                      className="input-field"
                      style={{ paddingLeft: "36px" }}
                      placeholder="+91 9876543210"
                      value={profileForm.phone}
                      onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })}
                    />
                    <Phone size={16} style={{ position: "absolute", left: "12px", top: "14px", color: "var(--text-muted)" }} />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Current Job Title
                  </label>
                  <div style={{ position: "relative" }}>
                    <input
                      type="text"
                      className="input-field"
                      style={{ paddingLeft: "36px" }}
                      placeholder="e.g. Senior Software Engineer"
                      value={profileForm.current_title}
                      onChange={(e) => setProfileForm({ ...profileForm, current_title: e.target.value })}
                    />
                    <Briefcase size={16} style={{ position: "absolute", left: "12px", top: "14px", color: "var(--text-muted)" }} />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Current Company
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. Acme Corp"
                    value={profileForm.current_company}
                    onChange={(e) => setProfileForm({ ...profileForm, current_company: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Location (City / State / Country)
                  </label>
                  <div style={{ position: "relative" }}>
                    <input
                      type="text"
                      className="input-field"
                      style={{ paddingLeft: "36px" }}
                      placeholder="e.g. Bengaluru, Karnataka, India"
                      value={profileForm.city ? `${profileForm.city}${profileForm.state ? `, ${profileForm.state}` : ""}${profileForm.country ? `, ${profileForm.country}` : ""}` : ""}
                      onChange={(e) => {
                        const parts = e.target.value.split(",").map((s) => s.trim());
                        setProfileForm({
                          ...profileForm,
                          city: parts[0] || "",
                          state: parts[1] || "",
                          country: parts[2] || "",
                        });
                      }}
                    />
                    <MapPin size={16} style={{ position: "absolute", left: "12px", top: "14px", color: "var(--text-muted)" }} />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                    LinkedIn Profile URL
                  </label>
                  <div style={{ position: "relative" }}>
                    <input
                      type="url"
                      className="input-field"
                      style={{ paddingLeft: "36px" }}
                      placeholder="https://linkedin.com/in/username"
                      value={profileForm.linkedin_url}
                      onChange={(e) => setProfileForm({ ...profileForm, linkedin_url: e.target.value })}
                    />
                    <Link2 size={16} style={{ position: "absolute", left: "12px", top: "14px", color: "var(--text-muted)" }} />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Portfolio / Website URL
                  </label>
                  <div style={{ position: "relative" }}>
                    <input
                      type="url"
                      className="input-field"
                      style={{ paddingLeft: "36px" }}
                      placeholder="https://myportfolio.dev"
                      value={profileForm.portfolio_url}
                      onChange={(e) => setProfileForm({ ...profileForm, portfolio_url: e.target.value })}
                    />
                    <Globe size={16} style={{ position: "absolute", left: "12px", top: "14px", color: "var(--text-muted)" }} />
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button
                  type="submit"
                  disabled={profileMutation.isPending}
                  className="btn-primary"
                >
                  {profileMutation.isPending ? (
                    <>
                      <Loader2 className="animate-spin" size={16} />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save size={16} />
                      Save Profile Changes
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* 2. Auto-Apply Settings Section */}
        <div className="glass-card" style={{ padding: "28px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "20px",
              paddingBottom: "16px",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "10px",
                  background: "rgba(139,92,246,0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#8b5cf6",
                }}
              >
                <Sliders size={20} />
              </div>
              <div>
                <h2 style={{ fontSize: "18px", fontWeight: 700, color: "white" }}>Auto-Apply Bot Configuration</h2>
                <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                  Tune the background bot application rate, threshold filters, and safety constraints
                </p>
              </div>
            </div>

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 14px",
                borderRadius: "20px",
                background: autoApplyForm.is_enabled ? "rgba(16,185,129,0.12)" : "rgba(255,255,255,0.05)",
                border: `1px solid ${autoApplyForm.is_enabled ? "rgba(16,185,129,0.3)" : "var(--border)"}`,
              }}
            >
              <div
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: autoApplyForm.is_enabled ? "#10b981" : "#64748b",
                  boxShadow: autoApplyForm.is_enabled ? "0 0 10px #10b981" : "none",
                }}
              />
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: autoApplyForm.is_enabled ? "#10b981" : "var(--text-muted)",
                }}
              >
                {autoApplyForm.is_enabled ? "Bot Active" : "Bot Paused"}
              </span>
            </div>
          </div>

          {settingsLoading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}>
              <Loader2 className="animate-spin" size={24} color="#8b5cf6" />
            </div>
          ) : (
            <form onSubmit={handleAutoApplySubmit}>
              {/* Main Toggle Banner */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "16px 20px",
                  borderRadius: "12px",
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid var(--border)",
                  marginBottom: "24px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <Zap
                    size={22}
                    color={autoApplyForm.is_enabled ? "#6366f1" : "var(--text-muted)"}
                  />
                  <div>
                    <div style={{ fontSize: "15px", fontWeight: 600, color: "white" }}>
                      Enable Autonomous Applying
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      When turned on, the system continuously monitors discovered jobs and prepares applications.
                    </div>
                  </div>
                </div>

                <label
                  style={{
                    position: "relative",
                    display: "inline-block",
                    width: "50px",
                    height: "26px",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={autoApplyForm.is_enabled}
                    onChange={(e) => setAutoApplyForm({ ...autoApplyForm, is_enabled: e.target.checked })}
                    style={{ opacity: 0, width: 0, height: 0 }}
                  />
                  <span
                    style={{
                      position: "absolute",
                      cursor: "pointer",
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      backgroundColor: autoApplyForm.is_enabled ? "#6366f1" : "rgba(255,255,255,0.15)",
                      transition: "0.25s",
                      borderRadius: "34px",
                    }}
                  >
                    <span
                      style={{
                        position: "absolute",
                        content: '""',
                        height: "20px",
                        width: "20px",
                        left: autoApplyForm.is_enabled ? "27px" : "3px",
                        bottom: "3px",
                        backgroundColor: "white",
                        transition: "0.25s",
                        borderRadius: "50%",
                      }}
                    />
                  </span>
                </label>
              </div>

              {/* Grid of parameters */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                  gap: "24px",
                  marginBottom: "24px",
                }}
              >
                {/* Match Score Threshold */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)" }}>
                      Minimum Match Score
                    </label>
                    <span
                      style={{
                        fontSize: "13px",
                        fontWeight: 700,
                        color: getScoreHex(autoApplyForm.min_match_score),
                        padding: "2px 8px",
                        borderRadius: "6px",
                        background: "rgba(255,255,255,0.06)",
                      }}
                    >
                      {autoApplyForm.min_match_score}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min={40}
                    max={98}
                    step={1}
                    value={autoApplyForm.min_match_score}
                    onChange={(e) => setAutoApplyForm({ ...autoApplyForm, min_match_score: Number(e.target.value) })}
                    style={{ width: "100%", accentColor: "#6366f1", cursor: "pointer" }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                    <span>Lenient (40%)</span>
                    <span>Strict (95%+)</span>
                  </div>
                </div>

                {/* Daily limit */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <label style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)" }}>
                      Daily Application Limit
                    </label>
                    <span style={{ fontSize: "13px", fontWeight: 700, color: "white" }}>
                      {autoApplyForm.max_applications_per_day} jobs / day
                    </span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={50}
                    step={1}
                    value={autoApplyForm.max_applications_per_day}
                    onChange={(e) => setAutoApplyForm({ ...autoApplyForm, max_applications_per_day: Number(e.target.value) })}
                    style={{ width: "100%", accentColor: "#8b5cf6", cursor: "pointer" }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                    <span>1 job/day</span>
                    <span>50 jobs/day</span>
                  </div>
                </div>

                {/* Delay between applications */}
                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "8px" }}>
                    Delay Between Submissions
                  </label>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div style={{ flex: 1 }}>
                      <input
                        type="number"
                        min={5}
                        max={300}
                        className="input-field"
                        value={autoApplyForm.delay_min_seconds}
                        onChange={(e) => setAutoApplyForm({ ...autoApplyForm, delay_min_seconds: Number(e.target.value) })}
                      />
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px", display: "block" }}>Min sec</span>
                    </div>
                    <span style={{ color: "var(--text-muted)" }}>to</span>
                    <div style={{ flex: 1 }}>
                      <input
                        type="number"
                        min={10}
                        max={600}
                        className="input-field"
                        value={autoApplyForm.delay_max_seconds}
                        onChange={(e) => setAutoApplyForm({ ...autoApplyForm, delay_max_seconds: Number(e.target.value) })}
                      />
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px", display: "block" }}>Max sec</span>
                    </div>
                  </div>
                </div>

                {/* Operating Mode */}
                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "8px" }}>
                    Application Review Mode
                  </label>
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button
                      type="button"
                      onClick={() => setAutoApplyForm({ ...autoApplyForm, mode: "safe", require_approval_before_submit: true })}
                      style={{
                        flex: 1,
                        padding: "10px",
                        borderRadius: "10px",
                        border: `1px solid ${autoApplyForm.mode === "safe" ? "var(--accent-primary)" : "var(--border)"}`,
                        background: autoApplyForm.mode === "safe" ? "rgba(99,102,241,0.15)" : "rgba(255,255,255,0.03)",
                        color: autoApplyForm.mode === "safe" ? "white" : "var(--text-secondary)",
                        cursor: "pointer",
                        fontSize: "12px",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                      }}
                    >
                      <Shield size={14} color={autoApplyForm.mode === "safe" ? "#6366f1" : undefined} />
                      Safe Mode
                    </button>

                    <button
                      type="button"
                      onClick={() => setAutoApplyForm({ ...autoApplyForm, mode: "auto", require_approval_before_submit: false })}
                      style={{
                        flex: 1,
                        padding: "10px",
                        borderRadius: "10px",
                        border: `1px solid ${autoApplyForm.mode === "auto" ? "var(--accent-secondary)" : "var(--border)"}`,
                        background: autoApplyForm.mode === "auto" ? "rgba(139,92,246,0.15)" : "rgba(255,255,255,0.03)",
                        color: autoApplyForm.mode === "auto" ? "white" : "var(--text-secondary)",
                        cursor: "pointer",
                        fontSize: "12px",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                      }}
                    >
                      <Zap size={14} color={autoApplyForm.mode === "auto" ? "#8b5cf6" : undefined} />
                      Full Autopilot
                    </button>
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
                    {autoApplyForm.mode === "safe"
                      ? "Prepares answers & cover letters, pauses for manual 1-click approval."
                      : "Directly fills and submits applications on qualifying jobs."}
                  </span>
                </div>
              </div>

              {/* Safety & Test Mode Row */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                  gap: "16px",
                  padding: "16px",
                  borderRadius: "12px",
                  background: "rgba(255,255,255,0.02)",
                  border: "1px solid var(--border)",
                  marginBottom: "24px",
                }}
              >
                <label style={{ display: "flex", alignItems: "flex-start", gap: "12px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={autoApplyForm.is_test_mode}
                    onChange={(e) => setAutoApplyForm({ ...autoApplyForm, is_test_mode: e.target.checked })}
                    style={{ marginTop: "3px", accentColor: "#6366f1", width: "16px", height: "16px" }}
                  />
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "white" }}>
                      Test Mode (Dry Run)
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      Fills out forms and validates fields without clicking final submit button.
                    </div>
                  </div>
                </label>

                <label style={{ display: "flex", alignItems: "flex-start", gap: "12px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={autoApplyForm.require_approval_before_submit}
                    onChange={(e) =>
                      setAutoApplyForm({ ...autoApplyForm, require_approval_before_submit: e.target.checked })
                    }
                    style={{ marginTop: "3px", accentColor: "#6366f1", width: "16px", height: "16px" }}
                  />
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "white" }}>
                      Require Approval Before Submit
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      Holds applications in &quot;Ready&quot; state until you click submit in Queue.
                    </div>
                  </div>
                </label>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button
                  type="submit"
                  disabled={autoApplyMutation.isPending}
                  className="btn-primary"
                >
                  {autoApplyMutation.isPending ? (
                    <>
                      <Loader2 className="animate-spin" size={16} />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save size={16} />
                      Save Auto-Apply Config
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* 3. AI Provider Section */}
        <div className="glass-card" style={{ padding: "28px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "20px",
              paddingBottom: "16px",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "rgba(16,185,129,0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#10b981",
              }}
            >
              <Cpu size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "white" }}>AI Intelligence Engine</h2>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                Active LLM backend generating tailored answers and cover letters
              </p>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "16px",
            }}
          >
            <div
              style={{
                padding: "16px",
                borderRadius: "12px",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>
                Primary Provider
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Sparkles size={16} color="#6366f1" />
                <span style={{ fontSize: "15px", fontWeight: 700, color: "white" }}>Google Gemini</span>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 700,
                    padding: "2px 6px",
                    borderRadius: "4px",
                    background: "rgba(99,102,241,0.2)",
                    color: "#a5b4fc",
                  }}
                >
                  DEFAULT
                </span>
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                gemini-1.5-flash / gemini-1.5-pro
              </div>
            </div>

            <div
              style={{
                padding: "16px",
                borderRadius: "12px",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>
                API Key Status
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <CheckCircle size={16} color="#10b981" />
                <span style={{ fontSize: "14px", fontWeight: 600, color: "#10b981" }}>Configured via .env</span>
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", fontFamily: "monospace", marginTop: "4px" }}>
                AIzaSy************************ (Masked)
              </div>
            </div>

            <div
              style={{
                padding: "16px",
                borderRadius: "12px",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>
                Fallback Engine
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Shield size={16} color="#f59e0b" />
                <span style={{ fontSize: "14px", fontWeight: 600, color: "white" }}>Rule-Based Fallback</span>
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
                Ensures 100% form completion even if API quota is reached
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
