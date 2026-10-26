"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Zap, Eye, EyeOff, Loader2 } from "lucide-react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { useToast } from "@/components/ui/ToastProvider";

type Tab = "login" | "register";

export default function LoginPage({ initialTab = "login" }: { initialTab?: Tab }) {
  const [tab, setTab] = useState<Tab>(initialTab);
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const { setAuth } = useAuthStore();
  const { toast } = useToast();
  const router = useRouter();

  // Login form state
  const [loginData, setLoginData] = useState({ email: "", password: "" });

  // Register form state
  const [regData, setRegData] = useState({ first_name: "", last_name: "", email: "", password: "" });

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await authApi.login(loginData.email, loginData.password);
      const token = res.data.access_token;
      localStorage.setItem("access_token", token);
      const meRes = await authApi.me(token);
      setAuth(meRes.data, token);
      toast("Welcome back! 🎉", "success");
      router.push("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Invalid credentials";
      toast(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (regData.password.length < 8) {
      toast("Password must be at least 8 characters", "warning");
      return;
    }
    setLoading(true);
    try {
      await authApi.register(regData);
      // Auto login after register
      const res = await authApi.login(regData.email, regData.password);
      const token = res.data.access_token;
      localStorage.setItem("access_token", token);
      const meRes = await authApi.me(token);
      setAuth(meRes.data, token);
      toast("Account created! Welcome aboard 🚀", "success");
      router.push("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Registration failed";
      toast(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <div style={{ width: "100%", maxWidth: "420px" }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div
            style={{
              width: "52px",
              height: "52px",
              borderRadius: "16px",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
              boxShadow: "0 0 30px rgba(99,102,241,0.5)",
            }}
          >
            <Zap size={26} fill="white" color="white" />
          </div>
          <h1 style={{ fontSize: "26px", fontWeight: 800, color: "white", marginBottom: "6px" }}>
            AI <span className="gradient-text-purple">Job Hunter</span>
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Automate your job search with AI
          </p>
        </div>

        {/* Card */}
        <div className="glass-card" style={{ padding: "32px" }}>
          {/* Tabs */}
          <div
            style={{
              display: "flex",
              background: "rgba(255,255,255,0.05)",
              borderRadius: "10px",
              padding: "4px",
              marginBottom: "28px",
            }}
          >
            {(["login", "register"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                style={{
                  flex: 1,
                  padding: "9px",
                  borderRadius: "8px",
                  border: "none",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "13px",
                  transition: "all 0.2s",
                  background: tab === t ? "linear-gradient(135deg, #6366f1, #8b5cf6)" : "transparent",
                  color: tab === t ? "white" : "var(--text-muted)",
                  fontFamily: "inherit",
                }}
              >
                {t === "login" ? "Sign In" : "Create Account"}
              </button>
            ))}
          </div>

          {/* Login Form */}
          {tab === "login" && (
            <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div>
                <label style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                  Email
                </label>
                <input
                  className="input-field"
                  type="email"
                  placeholder="you@example.com"
                  value={loginData.email}
                  onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                  required
                  id="login-email"
                />
              </div>
              <div>
                <label style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                  Password
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    className="input-field"
                    type={showPass ? "text" : "password"}
                    placeholder="••••••••"
                    value={loginData.password}
                    onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                    required
                    id="login-password"
                    style={{ paddingRight: "44px" }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    style={{
                      position: "absolute",
                      right: "14px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      color: "var(--text-muted)",
                    }}
                  >
                    {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              <button className="btn-primary" type="submit" disabled={loading} style={{ justifyContent: "center", marginTop: "4px" }}>
                {loading ? <Loader2 size={16} className="animate-spin" /> : null}
                {loading ? "Signing in..." : "Sign In"}
              </button>
            </form>
          )}

          {/* Register Form */}
          {tab === "register" && (
            <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                    First Name
                  </label>
                  <input
                    className="input-field"
                    type="text"
                    placeholder="Aayush"
                    value={regData.first_name}
                    onChange={(e) => setRegData({ ...regData, first_name: e.target.value })}
                    required
                    id="reg-first-name"
                  />
                </div>
                <div>
                  <label style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                    Last Name
                  </label>
                  <input
                    className="input-field"
                    type="text"
                    placeholder="Sharma"
                    value={regData.last_name}
                    onChange={(e) => setRegData({ ...regData, last_name: e.target.value })}
                    id="reg-last-name"
                  />
                </div>
              </div>
              <div>
                <label style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                  Email
                </label>
                <input
                  className="input-field"
                  type="email"
                  placeholder="you@example.com"
                  value={regData.email}
                  onChange={(e) => setRegData({ ...regData, email: e.target.value })}
                  required
                  id="reg-email"
                />
              </div>
              <div>
                <label style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                  Password
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    className="input-field"
                    type={showPass ? "text" : "password"}
                    placeholder="Min. 8 characters"
                    value={regData.password}
                    onChange={(e) => setRegData({ ...regData, password: e.target.value })}
                    required
                    id="reg-password"
                    style={{ paddingRight: "44px" }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    style={{
                      position: "absolute",
                      right: "14px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      color: "var(--text-muted)",
                    }}
                  >
                    {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              <button className="btn-primary" type="submit" disabled={loading} style={{ justifyContent: "center", marginTop: "4px" }}>
                {loading ? <Loader2 size={16} /> : null}
                {loading ? "Creating account..." : "Create Account"}
              </button>
            </form>
          )}
        </div>

        <p style={{ textAlign: "center", marginTop: "20px", fontSize: "12px", color: "var(--text-muted)" }}>
          Built with ❤️ — 100% automated job applications
        </p>
      </div>
    </div>
  );
}
