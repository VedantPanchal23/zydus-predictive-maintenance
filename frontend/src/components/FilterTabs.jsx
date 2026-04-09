import React from 'react';
import { cn } from '../utils/cn';

function normalizeItem(item) {
  if (typeof item === 'string') {
    return { label: item, value: item };
  }

  return item;
}

export default function FilterTabs({ items, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => {
        const normalized = normalizeItem(item);
        const isActive = normalized.value === value;

        return (
          <button
            key={normalized.value}
            type="button"
            onClick={() => onChange(normalized.value)}
            className={cn(
              'rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-slate-900 text-white'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
            )}
          >
            {normalized.label}
          </button>
        );
      })}
    </div>
  );
}
