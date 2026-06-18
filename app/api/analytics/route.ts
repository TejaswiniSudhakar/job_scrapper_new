import { NextResponse } from "next/server";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import type { DashboardAnalytics, JobStatus, ScraperMetric, ScraperSource, ScraperStatus } from "@/types/jobs";

const backendDir =
  process.env.JOB_SCRAPER_DATA_DIR ??
  "C:\\Users\\Nishant Chandraker\\Downloads\\private-job-scraper-main\\private-job-scraper-main";

const jobsCsvPath = path.join(backendDir, "jobs.csv");
const sources: ScraperSource[] = ["LinkedIn", "Naukri", "Indeed", "Company Site"];
const statuses: JobStatus[] = ["UNAPPLIED", "APPLIED", "INTERVIEW", "REJECTED", "OFFER", "EXPIRED", "SAVED"];

type AnalyticsJob = {
  source: ScraperSource;
  scrapedTime: string;
  status: JobStatus;
  gptRelevanceScore: number;
};

let analyticsCache: { mtimeMs: number; analytics: DashboardAnalytics } | undefined;

export async function GET() {
  try {
    const analytics = await readAnalytics();
    return NextResponse.json(analytics);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to load analytics." },
      { status: 500 }
    );
  }
}

async function readAnalytics() {
  const file = await stat(jobsCsvPath);
  if (analyticsCache?.mtimeMs === file.mtimeMs) return analyticsCache.analytics;

  const csv = await readFile(jobsCsvPath, "utf8");
  const jobs = parseCsv(csv).map(mapRowToAnalyticsJob);
  const today = new Date().toDateString();
  const scrapers: ScraperMetric[] = sources
    .map((source) => {
      const sourceJobs = jobs.filter((job) => job.source === source);
      const latest = sourceJobs[0]?.scrapedTime ?? new Date().toISOString();
      const status: ScraperStatus = sourceJobs.length ? "Completed" : "Idle";

      return {
        source,
        jobsFound: sourceJobs.length,
        activeJobs: sourceJobs.filter((job) => job.status !== "EXPIRED" && job.status !== "REJECTED").length,
        successRate: sourceJobs.length ? 100 : 0,
        lastRunTime: latest,
        status,
        averageScore: sourceJobs.length
          ? Math.round((sourceJobs.reduce((sum, job) => sum + job.gptRelevanceScore, 0) / sourceJobs.length) * 10) / 10
          : 0
      };
    })
    .filter((metric) => metric.jobsFound > 0);

  const analytics: DashboardAnalytics = {
    totalJobsFound: jobs.length,
    totalActiveJobs: jobs.filter((job) => job.status !== "EXPIRED" && job.status !== "REJECTED").length,
    jobsScrapedToday: jobs.filter((job) => new Date(job.scrapedTime).toDateString() === today).length,
    successRate: jobs.length ? 100 : 0,
    scrapers,
    daily: buildDailyMetrics(jobs),
    statusBreakdown: buildStatusBreakdown(jobs)
  };

  analyticsCache = { mtimeMs: file.mtimeMs, analytics };
  return analytics;
}

function parseCsv(csv: string) {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let inQuotes = false;

  for (let index = 0; index < csv.length; index += 1) {
    const char = csv[index];
    const next = csv[index + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        cell += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      row.push(cell);
      cell = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value.length > 0)) rows.push(row);
      row = [];
      cell = "";
      continue;
    }

    cell += char;
  }

  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }

  const [headers = [], ...dataRows] = rows;
  return dataRows.map((values) =>
    Object.fromEntries(headers.map((header, index) => [header.trim(), values[index]?.trim() ?? ""]))
  );
}

function mapRowToAnalyticsJob(row: Record<string, string>): AnalyticsJob {
  return {
    source: normalizeSource(row.source),
    scrapedTime: normalizeDate(row.created_at),
    status: "UNAPPLIED",
    gptRelevanceScore: scoreToTen(Number(row.final_score || row.gpt_score || row.pre_score || 0))
  };
}

function buildDailyMetrics(jobs: AnalyticsJob[]) {
  const days = new Map<
    string,
    {
      date: string;
      scraped: number;
      applied: number;
      saved: number;
      interviews: number;
      rejected: number;
      scoreTotal: number;
    }
  >();

  for (const job of jobs) {
    const date = new Date(job.scrapedTime).toISOString().slice(0, 10);
    const metric =
      days.get(date) ??
      {
        date,
        scraped: 0,
        applied: 0,
        saved: 0,
        interviews: 0,
        rejected: 0,
        scoreTotal: 0
      };

    metric.scraped += 1;
    metric.scoreTotal += job.gptRelevanceScore;
    if (job.status === "APPLIED") metric.applied += 1;
    if (job.status === "SAVED") metric.saved += 1;
    if (job.status === "INTERVIEW") metric.interviews += 1;
    if (job.status === "REJECTED") metric.rejected += 1;
    days.set(date, metric);
  }

  return [...days.values()]
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-14)
    .map(({ scoreTotal, ...metric }) => ({
      ...metric,
      averageScore: metric.scraped ? Math.round((scoreTotal / metric.scraped) * 10) / 10 : 0
    }));
}

function buildStatusBreakdown(jobs: AnalyticsJob[]) {
  return statuses.map((status) => ({
    status,
    count: jobs.filter((job) => job.status === status).length
  }));
}

function normalizeSource(source: string): ScraperSource {
  const normalized = source.toLowerCase();
  if (normalized.includes("linkedin")) return "LinkedIn";
  if (normalized.includes("naukri")) return "Naukri";
  if (normalized.includes("indeed")) return "Indeed";
  return "Company Site";
}

function normalizeDate(value: string) {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? new Date().toISOString() : new Date(parsed).toISOString();
}

function scoreToTen(score: number) {
  const normalized = score > 10 ? score / 10 : score;
  return Math.max(0, Math.min(10, Math.round(normalized * 10) / 10));
}
