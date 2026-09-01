import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ShieldCheck, Lock, User, AlertCircle, KeyRound, ShieldAlert } from "lucide-react";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail || "Authentication failed. Verify GxP credentials.");
    } finally {
      setLoading(false);
    }
  };

  const quickSwitch = (user, pass) => {
    setUsername(user);
    setPassword(pass);
  };

  return (
    <div className="min-h-screen bg-surface-base flex flex-col justify-center items-center p-4 relative overflow-hidden">
      {/* Background Subtle Tech Dot Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:20px_20px] opacity-30 pointer-events-none" />

      {/* Top Ambient Glow */}
      <div className="absolute top-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="clinical-card w-full max-w-md p-7 border-surface-border bg-surface-panel/90 shadow-2xl relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-5">
          <div className="w-12 h-12 mx-auto rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center shadow-glow-cyan border border-cyan-400/30 mb-3">
            <ShieldCheck className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-lg font-extrabold tracking-tight text-white">ZYDUS LIFESCIENCES</h1>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">Predictive Maintenance & Oncology Asset Intelligence</p>
        </div>

        {/* 21 CFR Part 11 Regulatory Box */}
        <div className="mb-4 p-3 rounded-lg bg-surface-base border border-surface-border text-[11px] text-slate-400 font-mono flex items-start gap-2.5">
          <ShieldAlert className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
          <span className="leading-relaxed">
            Restricted GxP Environment. Electronic signatures & access are logged under US FDA 21 CFR Part 11.
          </span>
        </div>

        {error && (
          <div className="mb-4 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-3.5">
          <div>
            <label className="block text-[11px] font-semibold text-slate-300 mb-1 font-mono uppercase">
              Username / ID
            </label>
            <div className="relative">
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="clinical-input w-full pl-8"
                placeholder="e.g. admin"
              />
              <User className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-300 mb-1 font-mono uppercase">
              Password
            </label>
            <div className="relative">
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="clinical-input w-full pl-8"
                placeholder="••••••••"
              />
              <KeyRound className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="clinical-btn-primary w-full py-2.5 mt-2"
          >
            <Lock className="w-3.5 h-3.5" />
            <span>{loading ? "Authenticating..." : "Sign In with GxP Credentials"}</span>
          </button>
        </form>

        {/* Demo Role Switcher */}
        <div className="mt-5 pt-4 border-t border-surface-border">
          <div className="text-[10px] font-bold text-slate-400 mb-2 uppercase tracking-wider text-center font-mono">
            Demo Role Quick Switch
          </div>
          <div className="grid grid-cols-4 gap-1.5 font-mono text-[11px]">
            <button
              onClick={() => quickSwitch("admin", "admin123")}
              className="px-2 py-1 rounded bg-surface-base hover:bg-surface-elevated border border-surface-border text-purple-300 transition-colors text-center font-medium"
            >
              admin
            </button>
            <button
              onClick={() => quickSwitch("engineer", "engineer123")}
              className="px-2 py-1 rounded bg-surface-base hover:bg-surface-elevated border border-surface-border text-cyan-300 transition-colors text-center font-medium"
            >
              engineer
            </button>
            <button
              onClick={() => quickSwitch("auditor", "auditor123")}
              className="px-2 py-1 rounded bg-surface-base hover:bg-surface-elevated border border-surface-border text-amber-300 transition-colors text-center font-medium"
            >
              auditor
            </button>
            <button
              onClick={() => quickSwitch("viewer", "viewer123")}
              className="px-2 py-1 rounded bg-surface-base hover:bg-surface-elevated border border-surface-border text-slate-300 transition-colors text-center font-medium"
            >
              viewer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
