import React from 'react';
import { cn } from '../utils/cn';

function headerCellClass(align) {
  if (align === 'right') return 'text-right';
  if (align === 'center') return 'text-center';
  return 'text-left';
}

export default function DataTableCard({
  title,
  description,
  action,
  meta,
  columns,
  rows,
  renderRow,
  rowKey,
  isLoading = false,
  loadingMessage = 'Loading data...',
  emptyMessage = 'No data is available.',
  className,
}) {
  const hasRows = rows.length > 0;

  return (
    <div className={cn('rounded-lg border border-slate-200 bg-white', className)}>
      {(title || description || action) && (
        <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-4 py-3">
          <div>
            {title ? <h2 className="text-lg font-semibold text-slate-900">{title}</h2> : null}
            {description ? <p className="text-sm text-slate-600">{description}</p> : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
      )}

      {meta !== undefined && meta !== null && (
        <div className="border-b border-slate-200 px-4 py-3 text-sm text-slate-600">
          {meta}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={cn(
                    'px-4 py-3 font-medium text-slate-600',
                    headerCellClass(column.align),
                    column.className,
                  )}
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {isLoading ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-6 text-center text-slate-500">
                  {loadingMessage}
                </td>
              </tr>
            ) : hasRows ? (
              rows.map((row, index) => renderRow(row, index, rowKey ? rowKey(row, index) : index))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-4 py-6 text-center text-slate-500">
                  {emptyMessage}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
