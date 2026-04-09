import React from 'react';
import { cn } from '../utils/cn';

const TONE_CLASS = {
  critical: 'bg-red-100 text-red-700',
  warning: 'bg-amber-100 text-amber-700',
  success: 'bg-emerald-100 text-emerald-700',
  info: 'bg-blue-100 text-blue-700',
  neutral: 'bg-slate-100 text-slate-700',
};

export default function StatusBadge({ children, tone = 'neutral', className }) {
  return (
    <span className={cn('status-badge', TONE_CLASS[tone] || TONE_CLASS.neutral, className)}>
      {children}
    </span>
  );
}
