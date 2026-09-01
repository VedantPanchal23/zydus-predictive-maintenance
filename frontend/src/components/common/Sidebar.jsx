import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import {
  LayoutDashboard,
  Cpu,
  AlertTriangle,
  ClipboardList,
  ShieldCheck,
  Flame,
  Archive,
} from "lucide-react";

export default function Sidebar() {
  const { isAdmin, isEngineer, isAuditor } = useAuth();

  const navItems = [
    {
      to: "/",
      label: "Fleet Command",
      icon: LayoutDashboard,
      roles: ["admin", "engineer", "auditor", "viewer"],
    },
    {
      to: "/equipment/1",
      label: "Digital Twin Studio",
      icon: Cpu,
      roles: ["admin", "engineer", "auditor", "viewer"],
    },
    {
      to: "/incidents",
      label: "GxP Incident Desk",
      icon: AlertTriangle,
      roles: ["admin", "engineer", "auditor", "viewer"],
    },
    {
      to: "/workorders",
      label: "Work Orders (e-Sign)",
      icon: ClipboardList,
      roles: ["admin", "engineer", "auditor", "viewer"],
    },
    {
      to: "/audit-trail",
      label: "21 CFR Part 11 Audit",
      icon: ShieldCheck,
      roles: ["admin", "auditor"],
    },
    {
      to: "/telemetry-dlq",
      label: "Telemetry Quarantine",
      icon: Archive,
      roles: ["admin", "engineer", "auditor"],
    },
    {
      to: "/chaos",
      label: "Chaos Resilience Lab",
      icon: Flame,
      roles: ["admin", "engineer"],
    },
  ];

  return (
    <aside className="w-56 border-r border-neutral-200 dark:border-neutral-800 bg-neutral-50/60 dark:bg-[#050505] p-3 flex flex-col justify-between flex-shrink-0 select-none">
      <div className="space-y-4">
        <div>
          <div className="px-2.5 py-1 text-[10px] font-bold tracking-wider text-neutral-400 uppercase font-mono">
            Navigation
          </div>
          <nav className="mt-1 space-y-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-neutral-200 dark:bg-neutral-800 text-neutral-900 dark:text-white font-semibold"
                        : "text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-900"
                    }`
                  }
                >
                  <Icon className="w-4 h-4 flex-shrink-0 text-neutral-500" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Regulatory Note */}
        <div className="p-3 rounded-md border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-[#0d0d0d]">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-neutral-900 dark:text-white">
            <ShieldCheck className="w-3.5 h-3.5 text-neutral-700 dark:text-neutral-300" />
            <span>GxP Validated</span>
          </div>
          <p className="mt-1 text-[10px] text-neutral-500 leading-relaxed font-sans">
            US FDA 21 CFR Part 11 cryptographic hash chain active.
          </p>
        </div>
      </div>

      <div className="pt-3 border-t border-neutral-200 dark:border-neutral-800 text-[10px] text-neutral-400 font-mono space-y-0.5">
        <div>Architecture: v3.0.0-PROD</div>
        <div>Model Ensemble: Online</div>
      </div>
    </aside>
  );
}
