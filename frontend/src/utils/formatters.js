export function formatDateTime(value, fallback = 'Not available') {
  if (!value) {
    return fallback;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? fallback : date.toLocaleString();
}

export function formatDate(value, fallback = 'Not available') {
  if (!value) {
    return fallback;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? fallback : date.toLocaleDateString();
}

export function formatPercent(value, digits = 1, fallback = 'Not available') {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return fallback;
  }

  return `${(value * 100).toFixed(digits)}%`;
}

export function formatDecimal(value, digits = 1, fallback = 'Not available') {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return fallback;
  }

  return value.toFixed(digits);
}

export function humanizeKey(value, fallback = 'Not available') {
  if (!value) {
    return fallback;
  }

  return value.replaceAll('_', ' ');
}
