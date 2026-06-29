/**
 * Deterministic, locale-independent relative time formatting.
 *
 * Returns the original string unchanged when it cannot be parsed so callers can
 * safely pass through provenance values that are not ISO timestamps.
 */
export function formatRelativeTime(iso: string, now: number = Date.now()): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return iso;
  }

  const diffMs = now - parsed;
  const future = diffMs < 0;
  const seconds = Math.round(Math.abs(diffMs) / 1000);

  if (seconds < 45) {
    return "just now";
  }

  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return phrase(minutes, "minute", future);
  }

  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return phrase(hours, "hour", future);
  }

  const days = Math.round(hours / 24);
  if (days < 7) {
    return phrase(days, "day", future);
  }

  const weeks = Math.round(days / 7);
  if (weeks < 5) {
    return phrase(weeks, "week", future);
  }

  const months = Math.round(days / 30);
  if (months < 12) {
    return phrase(months, "month", future);
  }

  const years = Math.round(days / 365);
  return phrase(years, "year", future);
}

function phrase(value: number, unit: string, future: boolean): string {
  const label = `${value} ${value === 1 ? unit : `${unit}s`}`;
  return future ? `in ${label}` : `${label} ago`;
}
