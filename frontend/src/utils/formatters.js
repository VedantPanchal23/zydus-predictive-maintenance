/**
 * Clinical & Regulatory Formatters (Indian Rupee & GxP Standards)
 */

export function formatCurrency(amount) {
  if (amount === undefined || amount === null || isNaN(amount)) return "?0";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatPercent(value, decimals = 1) {
  if (value === undefined || value === null || isNaN(value)) return "0.0%";
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatDateTime(isoString) {
  if (!isoString) return "N/A";
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat("en-IN", {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(d);
  } catch {
    return String(isoString);
  }
}

export function formatNumber(val, decimals = 2) {
  if (val === undefined || val === null || isNaN(val)) return "0";
  return Number(val).toFixed(decimals);
}

export function truncateHash(hash, length = 12) {
  if (!hash) return "N/A";
  if (hash.length <= length * 2) return hash;
  return `${hash.slice(0, length)}...${hash.slice(-length)}`;
}
