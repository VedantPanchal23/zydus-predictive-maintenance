import React from 'react';

export default function PageHeader({ title, description, meta }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
      </div>
      {meta ? <div className="shrink-0">{meta}</div> : null}
    </div>
  );
}
