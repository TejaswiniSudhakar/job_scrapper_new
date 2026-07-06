import { NextResponse } from "next/server";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { parseCsv } from "@/lib/csv-parser";
import { normalizeDate, normalizeOptionalDate, normalizeSource, normalizeStatus, scoreToTen } from "@/lib/normalize";
import type { DashboardAnalytics, JobStatus, ScraperMetric, ScraperSource, ScraperStatus } from "@/types/jobs";

const jobsCsvPath = path.join(process.env.JOB_SCRAPER_DATA_DIR ?? process.cwd(), "jobs.csv");
const knownSources: ScraperSource[] = ["LinkedIn", "LinkedIn v2", "Naukri", "Naukri v2", "Indeed", "Indeed v2"];
const statuses: JobStatus[] = ["UNAPPLIED", "APPLIED", "INTERVIEW", "REJECTED", "OFFER", "EXPIRED", "SAVED"];
type AnalyticsJob = {
  source: ScraperSource;
  scrapedTime: string;
  appliedAt?: string;
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
  const jobs = parseCsv(csv)
    .filter((row) => row.status?.toUpperCase() !== "DELETED")
    .map(mapRowToAnalyticsJob);
  const today = new Date().toDateString();
  const sources = [
    ...knownSources,
    ...[...new Set(jobs.map((job) => job.source))].filter((source) => !knownSources.includes(source)).sort((a, b) => a.localeCompare(b))
  ];
  const scrapers: ScraperMetric[] = sources.map((source) => {
    const sourceJobs = jobs.filter((job) => job.source === source);
    const latest =
      sourceJobs
        .map((job) => job.scrapedTime)
        .sort((a, b) => Date.parse(b) - Date.parse(a))[0] ?? new Date().toISOString();
      const status: ScraperStatus = sourceJobs.length ? "Completed" : "Idle";
      const appliedJobs = sourceJobs.filter((job) => job.status === "APPLIED");

      return {
        source,
        jobsFound: sourceJobs.length,
        jobsFoundToday: sourceJobs.filter((job) => new Date(job.scrapedTime).toDateString() === today).length,
        jobsApplied: appliedJobs.length,
        jobsAppliedToday: appliedJobs.filter((job) => isSameDay(job.appliedAt, today)).length,
        activeJobs: sourceJobs.filter((job) => job.status !== "EXPIRED" && job.status !== "REJECTED").length,
        successRate: sourceJobs.length ? 100 : 0,
        lastRunTime: latest,
        status,
        averageScore: sourceJobs.length
          ? Math.round((sourceJobs.reduce((sum, job) => sum + job.gptRelevanceScore, 0) / sourceJobs.length) * 10) / 10
          : 0
      };
    });

  const analytics: DashboardAnalytics = {
    totalJobsFound: jobs.length,
    totalJobsApplied: jobs.filter((job) => job.status === "APPLIED").length,
    totalActiveJobs: jobs.filter((job) => job.status !== "EXPIRED" && job.status !== "REJECTED").length,
    jobsScrapedToday: jobs.filter((job) => new Date(job.scrapedTime).toDateString() === today).length,
    jobsAppliedToday: jobs.filter((job) => job.status === "APPLIED" && isSameDay(job.appliedAt, today)).length,
    successRate: jobs.length ? 100 : 0,
    scrapers,
    daily: buildDailyMetrics(jobs),
    statusBreakdown: buildStatusBreakdown(jobs)
  };

  analyticsCache = { mtimeMs: file.mtimeMs, analytics };
  return analytics;
}


function mapRowToAnalyticsJob(row: Record<string, string>): AnalyticsJob {
  return {
    source: normalizeSource(row.source),
    scrapedTime: normalizeDate(row.created_at),
    appliedAt: normalizeOptionalDate(row.applied_at || row.last_opened_at),
    status: normalizeStatus(row.status),
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
    const date = toDateKey(job.scrapedTime);
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
    if (job.status === "SAVED") metric.saved += 1;
    if (job.status === "INTERVIEW") metric.interviews += 1;
    if (job.status === "REJECTED") metric.rejected += 1;
    days.set(date, metric);

    if (job.status === "APPLIED") {
      const appliedDate = toDateKey(job.appliedAt ?? job.scrapedTime);
      const appliedMetric =
        days.get(appliedDate) ??
        {
          date: appliedDate,
          scraped: 0,
          applied: 0,
          saved: 0,
          interviews: 0,
          rejected: 0,
          scoreTotal: 0
        };
      appliedMetric.applied += 1;
      days.set(appliedDate, appliedMetric);
    }
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


function isSameDay(value: string | undefined, today: string) {
  return value ? new Date(value).toDateString() === today : false;
}

function toDateKey(value: string) {
  return new Date(value).toISOString().slice(0, 10);
}

