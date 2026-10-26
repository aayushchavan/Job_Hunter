import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (
      err.response?.status === 401 &&
      typeof window !== "undefined" &&
      window.location.pathname !== "/login"
    ) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { email: string; password: string; first_name: string; last_name?: string }) =>
    api.post("/api/v1/auth/register", data),

  login: (email: string, password: string) => {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    return api.post("/api/v1/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },

  me: (token?: string) =>
    api.get("/api/v1/auth/me", token ? { headers: { Authorization: `Bearer ${token}` } } : undefined),
  updateMe: (data: Record<string, any>) => api.put("/api/v1/auth/me", data),
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobsApi = {
  discover: (data: {
    keywords: string[];
    location?: string;
    remote?: boolean;
    results_per_page?: number;
    experience_min_years?: number;
    experience_max_years?: number;
    experience_years?: number;
  }) => api.post("/api/v1/jobs/discover", data),

  list: (params?: {
    page?: number;
    page_size?: number;
    limit?: number;
    search?: string;
    company?: string;
    location?: string;
    work_mode?: string;
    employment_type?: string;
    min_score?: number;
    experience_min_years?: number;
    experience_max_years?: number;
    experience_years?: number;
  }) => {
    const q: Record<string, any> = { ...params };
    if (params?.limit && !params?.page_size) {
      q.page_size = params.limit;
    }
    return api.get("/api/v1/jobs", { params: q });
  },

  stats: () => api.get("/api/v1/jobs/stats"),
  sources: () => api.get("/api/v1/jobs/sources"),
  get: (id: string) => api.get(`/api/v1/jobs/${id}`),
};

// ── Applications ─────────────────────────────────────────────────────────────
export const applicationsApi = {
  create: (data: { job_id: string; resume_id?: string }) =>
    api.post("/api/v1/applications/", data),

  queue: (params?: { status?: string; skip?: number; limit?: number }) =>
    api.get("/api/v1/applications/queue", { params }),

  stats: () => api.get("/api/v1/applications/stats"),

  get: (id: string) => api.get(`/api/v1/applications/${id}`),
  review: (id: string) => api.get(`/api/v1/applications/${id}/review`),
  prepare: (id: string) => api.post(`/api/v1/applications/${id}/prepare`),
  submit: (id: string) => api.post(`/api/v1/applications/${id}/submit`),
  retry: (id: string) => api.post(`/api/v1/applications/${id}/retry`),
  cancel: (id: string) => api.post(`/api/v1/applications/${id}/cancel`),
  dryRun: (data: { job_id: string; resume_id?: string }) =>
    api.post("/api/v1/applications/test", data),
};

// ── Resumes ───────────────────────────────────────────────────────────────────
export const resumesApi = {
  list: () => api.get("/api/v1/resumes"),
  create: (data: { name: string; is_primary?: boolean }) =>
    api.post("/api/v1/resumes", data),
  upload: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/api/v1/resumes/${id}/upload`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  get: (id: string) => api.get(`/api/v1/resumes/${id}`),
  update: (id: string, data: Record<string, any>) =>
    api.put(`/api/v1/resumes/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/resumes/${id}`),
  analyze: (id: string) => api.post(`/api/v1/resumes/${id}/analyze`),
  autofill: (id: string, overwrite: boolean = false) =>
    api.post(`/api/v1/resumes/${id}/autofill`, null, { params: { overwrite } }),
  requirements: (id: string) => api.get(`/api/v1/resumes/${id}/requirements`),
  findJobs: (id: string, limit: number = 15, experienceYears?: number, location?: string) =>
    api.post(`/api/v1/resumes/${id}/find-jobs`, null, {
      params: { limit, experience_years: experienceYears, location: location || undefined },
    }),
  autoApply: (
    id: string,
    minScore: number = 70,
    maxApplications: number = 5,
    experienceYears?: number,
    location?: string
  ) =>
    api.post(`/api/v1/resumes/${id}/auto-apply`, null, {
      params: {
        min_score: minScore,
        max_applications: maxApplications,
        experience_years: experienceYears,
        location: location || undefined,
      },
    }),
  autoPilot: (id: string, experienceYears?: number, location?: string) =>
    api.post(`/api/v1/resumes/${id}/auto-pilot`, null, {
      params: { experience_years: experienceYears, location: location || undefined },
    }),
  getAuditReport: (id: string) => api.get(`/api/v1/resumes/${id}/audit-report`),
  downloadAuditReport: (id: string, format: string = "markdown") =>
    api.get(`/api/v1/resumes/${id}/audit-report/download`, {
      params: { format },
      responseType: "blob",
    }),
};

// ── Settings ─────────────────────────────────────────────────────────────────
export const settingsApi = {
  getAutoApply: () => api.get("/api/v1/settings/auto-apply"),
  updateAutoApply: (data: Record<string, any>) =>
    api.put("/api/v1/settings/auto-apply", data),
};
