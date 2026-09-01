import React from "react";
import { useAuth } from "../../context/AuthContext";
import { useTelemetry } from "../../context/TelemetryContext";
import { useTheme } from "../../context/ThemeContext";
import { ShieldCheck, LogOut, Radio, User, Sun, Moon, ShieldAlert } from "lucide-react";

export default function Navbar() {
  const { user, logout, role } = useAuth();
  const { isConnected } = useTelemetry();
  const { isDark, toggleTheme } = useTheme();

  return (
    <header className="h-14 border-b border-neutral-200 dark:border-neutral-800 bg-white dark:bg-black px-5 flex items-center justify-between z-30 sticky top-0">
      {/* Brand & Platform Identity */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md bg-neutral-900 dark:bg-white flex items-center justify-center text-white dark:text-neutral-900 font-bold flex-shrink-0">
          <ShieldCheck className="w-4.5 h-4.5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold tracking-tight text-neutral-900 dark:text-white">ZYDUS LIFESCIENCES</span>
            <span className="text-[10px] font-mono font-semibold px-1.5 py-0.2 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700 uppercase">
              GAMP 5
            </span>
          </div>
          <p className="text-[10px] text-neutral-500 font-medium">Predictive Maintenance & Oncology Operations</p>
        </div>
      </div>

      {/* Right Controls: Stream status, Theme Toggle, Role, User, Logout */}
      <div className="flex items-center gap-3">
        {/* Stream Status */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-[#111] text-[11px] font-mono">
          <Radio className={`w-3 h-3 ${isConnected ? "text-emerald-600 dark:text-emerald-400 animate-pulse" : "text-rose-600 dark:text-rose-400"}`} />
          <span className="text-neutral-700 dark:text-neutral-300 font-medium">{isConnected ? "LIVE STREAM" : "OFFLINE"}</span>
        </div>

        {/* Theme Switcher Button */}
        <button
          onClick={toggleTheme}
          title={isDark ? "Switch to Pure White Cleanroom Mode" : "Switch to Pure Black Dark Mode"}
          className="p-1.5 rounded-md border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-[#111] text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* 21 CFR Indicator */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-neutral-100 dark:bg-neutral-800/80 border border-neutral-200 dark:border-neutral-700 text-[10px] font-mono text-neutral-700 dark:text-neutral-300">
          <ShieldAlert className="w-3 h-3 text-neutral-500" />
          <span>21 CFR PART 11</span>
        </div>

        {/* User Profile */}
        <div className="flex items-center gap-2 pl-3 border-l border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 flex items-center justify-center text-neutral-700 dark:text-neutral-300">
              <User className="w-3.5 h-3.5" />
            </div>
            <div className="hidden sm:block text-left">
              <div className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 leading-tight">{user?.username || "Operator"}</div>
              <span className="text-[9px] font-mono font-semibold uppercase text-neutral-500">
                {role}
              </span>
            </div>
          </div>

          <button
            onClick={logout}
            title="Sign Out"
            className="p-1.5 text-neutral-400 hover:text-rose-600 dark:hover:text-rose-400 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-900 transition-colors ml-1"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
