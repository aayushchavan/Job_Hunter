"use client";

import { useQuery } from "@tanstack/react-query";
import { jobsApi, applicationsApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { Briefcase, SendHorizontal, TrendingUp, Zap, ExternalLink, RefreshCw, Plus } from "lucide-react";
import Link from "next/link";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";
import { getMatchColor, formatRelativeTime } from "@/lib/utils";

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  sub,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
  sub?: string;
}) {
  return (
    <div className="stat-card">
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "16px" }}>
        <div
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "10px",
            background: `${color}15`,
            border: `1px solid ${color}30`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon size={18} color={color} />
        </div>
      </div>
      <div style={{ fontSize: "28px", fontWeight: 800, color: "white", marginBottom: "4px", letterSpacing: "-0.5px" }}>
        {value}
      </div>
      <div style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500 }}>{label}</div>
      {sub && <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>{sub}</div>}
    </div>
  );
}

// Custom tooltip for chart
function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (active && payload && payload.length) {
    return (
      <div
        style={{
          background: "rgba(13,13,26,0.95)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "10px 14px",
          fontSize: "13px",
        }}
      >
        <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>{label}</div>
        <div style={{ color: "#6366f1", fontWeight: 700 }}>{payload[0].value} applications</div>
      </div>
    );
  }
  return null;
}

export default function DashboardPage() {
  const { user } = useAuthStore();

  const { data: jobStats } = useQuery({
    queryKey: ["job-stats"],
    queryFn: () => jobsApi.stats().then((r) => r.data),
  });

  const { data: appStats } = useQuery({
    queryKey: ["app-stats"],
    queryFn: () => applicationsApi.stats().then((r) => r.data),
  });

  const { data: recentJobs, isLoading: jobsLoading } = useQuery({
    queryKey: ["jobs", { limit: 6 }],
    queryFn: () => jobsApi.list({ limit: 6 }).then((r) => r.data),
  });

  // Build chart data from appStats
  const chartData = appStats?.daily_breakdown
    ? Object.entries(appStats.daily_breakdown as Record<string, number>).map(([date, count]) => ({
        date: new Date(date).toLocaleDateString("en-IN", { day: "numeric", month: "short" }),
        applications: count,
      }))
    : [
        { date: "Mon", applications: 0 },
        { date: "Tue", applications: 0 },
        { date: "Wed", applications: 0 },
        { date: "Thu", applications: 0 },
        { date: "Fri", applications: 0 },
        { date: "Sat", applications: 0 },
        { date: "Sun", applications: 0 },
      ];

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "white", marginBottom: "4px" }}>
            {greeting()}, {user?.first_name ?? "there"} 👋
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Here&apos;s what&apos;s happening with your job search today
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <Link href="/jobs" className="btn-primary">
            <Plus size={16} />
            Discover Jobs
          </Link>
          <Link href="/applications" className="btn-secondary">
            <SendHorizontal size={15} />
            View Queue
          </Link>
        </div>
      </div>

      {/* Stats Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px" }}>
        <StatCard
          label="Jobs Discovered"
          value={jobStats?.total_discovered ?? jobStats?.total_jobs ?? 0}
          icon={Briefcase}
          color="#6366f1"
          sub={`${jobStats?.discovered_today ?? jobStats?.jobs_found_today ?? 0} today`}
        />
        <StatCard
          label="Applications"
          value={appStats?.total ?? appStats?.applications_started ?? 0}
          icon={SendHorizontal}
          color="#10b981"
          sub={`${appStats?.today ?? appStats?.applications_submitted ?? 0} today`}
        />
        <StatCard
          label="Success Rate"
          value={`${appStats?.success_rate ?? 0}%`}
          icon={TrendingUp}
          color="#f59e0b"
          sub="Submitted / Prepared"
        />
        <StatCard
          label="Auto-Apply"
          value={appStats?.auto_apply_enabled ? "Active" : "Paused"}
          icon={Zap}
          color={appStats?.auto_apply_enabled ? "#10b981" : "#6366f1"}
          sub="Go to Settings to toggle"
        />
      </div>

      {/* Chart + Recent Jobs */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        {/* Activity Chart */}
        <div className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
            <div>
              <h2 style={{ fontSize: "15px", fontWeight: 700, color: "white" }}>Application Activity</h2>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>Last 7 days</p>
            </div>
            <TrendingUp size={16} color="var(--text-muted)" />
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="appGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "#475569" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#475569" }}
                axisLine={false}
                tickLine={false}
                width={25}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="applications"
                stroke="#6366f1"
                strokeWidth={2}
                fill="url(#appGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Recent Jobs */}
        <div className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
            <div>
              <h2 style={{ fontSize: "15px", fontWeight: 700, color: "white" }}>Recent Jobs</h2>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>Latest discoveries</p>
            </div>
            <Link href="/jobs" style={{ color: "#6366f1", fontSize: "12px", fontWeight: 600, textDecoration: "none" }}>
              View All →
            </Link>
          </div>

          {jobsLoading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="skeleton" style={{ height: "48px" }} />
              ))}
            </div>
          ) : (!recentJobs?.items?.length && !recentJobs?.jobs?.length) ? (
            <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-muted)" }}>
              <Briefcase size={32} style={{ margin: "0 auto 12px", opacity: 0.3 }} />
              <p style={{ fontSize: "14px" }}>No jobs discovered yet</p>
              <Link href="/jobs" className="btn-primary" style={{ display: "inline-flex", marginTop: "12px", fontSize: "12px", padding: "8px 16px" }}>
                Discover Jobs
              </Link>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {(recentJobs?.items ?? recentJobs?.jobs ?? []).slice(0, 5).map((job: any) => (
                <div
                  key={job.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "10px",
                    borderRadius: "10px",
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "white", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {job.title}
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{job.company_name || job.company || "Company"} • {formatRelativeTime(job.discovered_at)}</div>
                  </div>
                  {job.match_score !== undefined && job.match_score !== null && (
                    <span className={`badge ${getMatchColor(job.match_score)}`}>
                      {Math.round(job.match_score)}%
                    </span>
                  )}
                  {(job.application_url || job.job_url) && (
                    <a href={job.application_url || job.job_url} target="_blank" rel="noreferrer" style={{ color: "var(--text-muted)" }}>
                      <ExternalLink size={13} />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Application Status Breakdown */}
      {appStats && (
        <div className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 700, color: "white" }}>Application Pipeline</h2>
            <Link href="/applications" className="btn-secondary" style={{ fontSize: "12px", padding: "6px 14px" }}>
              <RefreshCw size={13} />
              Manage All
            </Link>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "12px" }}>
            {[
              { label: "Queued", key: "queued", color: "#94a3b8" },
              { label: "Preparing", key: "preparing", color: "#60a5fa" },
              { label: "Ready", key: "ready", color: "#a78bfa" },
              { label: "Submitted", key: "submitted", color: "#34d399" },
              { label: "Failed", key: "failed", color: "#f87171" },
              { label: "Cancelled", key: "cancelled", color: "#64748b" },
            ].map(({ label, key, color }) => (
              <div
                key={key}
                style={{
                  textAlign: "center",
                  padding: "16px 12px",
                  borderRadius: "10px",
                  background: `${color}08`,
                  border: `1px solid ${color}20`,
                }}
              >
                <div style={{ fontSize: "22px", fontWeight: 800, color, marginBottom: "4px" }}>
                  {(appStats as Record<string, number>)[key] ?? 0}
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 500 }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
