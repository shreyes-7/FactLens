/**
 * Formatting helpers for numbers, dates, currency, and file sizes.
 */

export function formatBytes(bytes: number, decimals = 1): string {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export function formatNormalizedValue(val: number | null | undefined, unit?: string | null): string {
  if (val === null || val === undefined) return "—";

  const absVal = Math.abs(val);
  const prefix = unit === "INR" ? "₹" : unit === "USD" ? "$" : "";

  // Indian numbering system for INR
  if (unit === "INR") {
    if (absVal >= 1e7) {
      return `${prefix}${(val / 1e7).toFixed(2)} Cr`;
    }
    if (absVal >= 1e5) {
      return `${prefix}${(val / 1e5).toFixed(2)} Lakh`;
    }
  }

  // Western numbering system
  if (absVal >= 1e9) {
    return `${prefix}${(val / 1e9).toFixed(2)}B`;
  }
  if (absVal >= 1e6) {
    return `${prefix}${(val / 1e6).toFixed(2)}M`;
  }
  if (absVal >= 1e3) {
    return `${prefix}${(val / 1e3).toFixed(2)}K`;
  }

  return `${prefix}${val.toLocaleString()}`;
}

export function formatDate(dateString?: string | null): string {
  if (!dateString) return "—";
  try {
    const d = new Date(dateString);
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(d);
  } catch {
    return dateString;
  }
}

export function formatConfidence(score?: number | null): string {
  if (score === null || score === undefined) return "—";
  return `${Math.round(score * 100)}%`;
}
