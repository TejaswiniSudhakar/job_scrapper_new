/**
 * Shared normalization helpers used by both /api/jobs and /api/analytics routes.
 */

import type { JobStatus, ScraperSource } from "@/types/jobs";

const statuses: JobStatus[] = ["UNAPPLIED", "APPLIED", "INTERVIEW", "REJECTED", "OFFER", "EXPIRED", "SAVED"];

export function normalizeSource(source: string): ScraperSource {
  const normalized = source.toLowerCase();
  if (normalized.includes("linkedin") && normalized.includes("v2")) return "LinkedIn v2";
  if (normalized.includes("linkedin")) return "LinkedIn";
  if (normalized.includes("naukri") && normalized.includes("v2")) return "Naukri v2";
  if (normalized.includes("naukri")) return "Naukri";
  if (normalized.includes("indeed") && normalized.includes("v2")) return "Indeed v2";
  if (normalized.includes("indeed")) return "Indeed";
  return source.trim() || "Unknown";
}

export function normalizeDate(value: string) {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? new Date().toISOString() : new Date(parsed).toISOString();
}

export function normalizeOptionalDate(value: string) {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? undefined : new Date(parsed).toISOString();
}

export function normalizeStatus(value: string): JobStatus {
  const normalized = value?.toUpperCase();
  return statuses.includes(normalized as JobStatus) ? (normalized as JobStatus) : "UNAPPLIED";
}

export function scoreToTen(score: number) {
  const normalized = score > 10 ? score / 10 : score;
  return Math.max(0, Math.min(10, Math.round(normalized * 10) / 10));
}
