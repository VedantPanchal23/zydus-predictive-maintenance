import React from "react";
import { Building2 } from "lucide-react";

export const FACILITIES = [
  "All Facilities",
  "Oral Solid Dosage Block A",
  "Sterile Injectable Complex B",
  "Biologics Pilot Plant C",
  "Central Quality Control Lab",
  "Zydus Comprehensive Cancer Center",
];

export default function FacilityFilter({ activeFacility, onSelect, counts = {} }) {
  return (
    <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
      {FACILITIES.map((facility) => {
        const isSelected = activeFacility === facility;
        const count = counts[facility] ?? 0;
        return (
          <button
            key={facility}
            onClick={() => onSelect(facility)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors flex items-center gap-2 ${
              isSelected
                ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-semibold shadow-sm"
                : "bg-white dark:bg-[#0d0d0d] text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-[#1a1a1a] border border-neutral-200 dark:border-neutral-800"
            }`}
          >
            <Building2 className="w-3.5 h-3.5 flex-shrink-0 text-neutral-400" />
            <span>{facility}</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${isSelected ? "bg-neutral-700 text-neutral-200 dark:bg-neutral-200 dark:text-neutral-800" : "bg-neutral-100 dark:bg-neutral-800 text-neutral-500"}`}>
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
