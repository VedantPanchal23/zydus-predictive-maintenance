import { describe, expect, it } from 'vitest';
import {
  formatDate,
  formatDateTime,
  formatDecimal,
  formatPercent,
  humanizeKey,
} from './formatters';

describe('formatters', () => {
  it('formats percent values', () => {
    expect(formatPercent(0.5234, 1)).toBe('52.3%');
    expect(formatPercent(undefined)).toBe('Not available');
  });

  it('formats decimal values', () => {
    expect(formatDecimal(12.345, 2)).toBe('12.35');
    expect(formatDecimal(null)).toBe('Not available');
  });

  it('humanizes snake case labels', () => {
    expect(humanizeKey('cold_storage')).toBe('cold storage');
    expect(humanizeKey('')).toBe('Not available');
  });

  it('formats dates safely', () => {
    expect(formatDate('2026-04-02T10:29:07Z')).not.toBe('Not available');
    expect(formatDateTime('2026-04-02T10:29:07Z')).not.toBe('Not available');
    expect(formatDate('bad-date')).toBe('Not available');
  });
});
