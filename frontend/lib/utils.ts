import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatRelativeTime(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

export function getMatchColor(score: number) {
  if (score >= 80) return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
  if (score >= 60) return "text-amber-400 bg-amber-400/10 border-amber-400/20";
  return "text-red-400 bg-red-400/10 border-red-400/20";
}

export function getScoreHex(score: number) {
  if (score >= 80) return "#10b981";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

export function getStatusColor(status: string) {
  const map: Record<string, string> = {
    queued: "text-slate-400 bg-slate-400/10 border-slate-400/20",
    preparing: "text-blue-400 bg-blue-400/10 border-blue-400/20",
    ready: "text-indigo-400 bg-indigo-400/10 border-indigo-400/20",
    submitted: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
    failed: "text-red-400 bg-red-400/10 border-red-400/20",
    cancelled: "text-slate-500 bg-slate-500/10 border-slate-500/20",
    skipped: "text-slate-500 bg-slate-500/10 border-slate-500/20",
  };
  return map[status.toLowerCase()] ?? "text-slate-400 bg-slate-400/10 border-slate-400/20";
}
