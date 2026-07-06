"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DashboardAnalytics, Job, JobStatus } from "@/types/jobs";

const statusColors: Record<JobStatus, string> = {
  UNAPPLIED: "#64748b",
  APPLIED: "#14b8a6",
  INTERVIEW: "#6366f1",
  REJECTED: "#ef4444",
  OFFER: "#22c55e",
  EXPIRED: "#f59e0b",
  SAVED: "#8b5cf6"
};

const sourceColors = ["#14b8a6", "#6366f1", "#f59e0b", "#22c55e", "#ef4444", "#8b5cf6", "#06b6d4"];
const knownSources = ["LinkedIn", "LinkedIn v2", "Naukri", "Naukri v2", "Indeed", "Indeed v2"];
const ranges = ["Daily", "Weekly", "Monthly"] as const;
type HistoryRange = (typeof ranges)[number];

export function JobActivityAnalytics({ analytics }: { analytics: DashboardAnalytics }) {
  const [range, setRange] = useState<HistoryRange>("Daily");
  const activeStatuses = analytics.statusBreakdown.filter((item) => item.count > 0);
  const applicationHistory = useMemo(() => aggregateApplicationHistory(analytics.daily, range), [analytics.daily, range]);
  const appliedBySource = analytics.scrapers.filter((scraper) => scraper.jobsApplied > 0);
  const totals = analytics.daily.reduce(
    (acc, day) => ({
      scraped: acc.scraped + day.scraped,
      applied: acc.applied + day.applied,
      saved: acc.saved + day.saved,
      interviews: acc.interviews + day.interviews,
      rejected: acc.rejected + day.rejected
    }),
    { scraped: 0, applied: 0, saved: 0, interviews: 0, rejected: 0 }
  );

  return (
    <section className="grid gap-3 xl:grid-cols-[1.25fr_0.75fr]">
      <div className="rounded-md border border-border bg-panel p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Applications Submitted Over Time</h2>
            <p className="text-sm text-muted">Apply history grouped by day, week, or month</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="success">{totals.applied.toLocaleString("en-IN")} applied</Badge>
            {ranges.map((item) => (
              <Button key={item} size="sm" variant={range === item ? "primary" : "secondary"} onClick={() => setRange(item)}>
                {item}
              </Button>
            ))}
          </div>
        </div>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={applicationHistory}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip />
              <Line type="monotone" dataKey="applied" name="Applied" stroke="#6366f1" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid gap-3">
        <div className="rounded-md border border-border bg-panel p-4">
          <h2 className="text-sm font-semibold">Applications By Source</h2>
          <p className="mb-4 text-sm text-muted">Overall apply share across scrapers</p>
          {appliedBySource.length ? (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={appliedBySource} dataKey="jobsApplied" nameKey="source" innerRadius={44} outerRadius={76} paddingAngle={3}>
                    {appliedBySource.map((entry, index) => (
                      <Cell key={entry.source} fill={sourceColors[index % sourceColors.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-48 items-center justify-center rounded-md bg-background text-sm text-muted">No applications yet</div>
          )}
          <div className="space-y-3">
            {analytics.scrapers.map((item, index) => (
              <div key={item.source} className="flex items-center justify-between gap-2 text-xs">
                <span className="flex min-w-0 items-center gap-2">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: sourceColors[index % sourceColors.length] }} />
                  <span className="truncate">{item.source}</span>
                </span>
                <span className="font-medium">{item.jobsApplied.toLocaleString("en-IN")}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-md border border-border bg-panel p-4">
          <h2 className="text-sm font-semibold">Job Status</h2>
          <p className="mb-4 text-sm text-muted">Current pipeline state</p>
          <div className="space-y-3">
            {activeStatuses.map((item) => (
              <div key={item.status}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-medium">{item.status}</span>
                  <span className="text-muted">{item.count.toLocaleString("en-IN")}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-background">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${analytics.totalJobsFound ? (item.count / analytics.totalJobsFound) * 100 : 0}%`,
                      backgroundColor: statusColors[item.status]
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function buildJobActivityAnalytics(jobs: Job[], analytics: DashboardAnalytics): DashboardAnalytics {
  const today = new Date().toDateString();

  return {
    ...analytics,
    totalJobsFound: jobs.length,
    totalJobsApplied: jobs.filter((job) => job.status === "APPLIED").length,
    jobsScrapedToday: jobs.filter((job) => new Date(job.scrapedTime).toDateString() === today).length,
    jobsAppliedToday: jobs.filter((job) => job.status === "APPLIED" && isSameDay(job.appliedAt, today)).length,
    scrapers: buildScraperMetrics(jobs),
    daily: buildDailyMetrics(jobs),
    statusBreakdown: buildStatusBreakdown(jobs),
    totalActiveJobs: jobs.filter((job) => job.status !== "EXPIRED" && job.status !== "REJECTED").length
  };
}

function buildDailyMetrics(jobs: Job[]) {
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

    if (job.status === "APPLIED" && job.appliedAt) {
      const appliedDate = toDateKey(job.appliedAt);
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

function buildStatusBreakdown(jobs: Job[]) {
  const statuses: JobStatus[] = ["UNAPPLIED", "APPLIED", "INTERVIEW", "REJECTED", "OFFER", "EXPIRED", "SAVED"];
  return statuses.map((status) => ({
    status,
    count: jobs.filter((job) => job.status === status).length
  }));
}

function buildScraperMetrics(jobs: Job[]) {
  const today = new Date().toDateString();
  const sources = [
    ...knownSources,
    ...[...new Set(jobs.map((job) => job.source))].filter((source) => !knownSources.includes(source)).sort((a, b) => a.localeCompare(b))
  ];

  return sources.map((source) => {
    const sourceJobs = jobs.filter((job) => job.source === source);
    const appliedJobs = sourceJobs.filter((job) => job.status === "APPLIED");
    const latest =
      sourceJobs
        .map((job) => job.scrapedTime)
        .sort((a, b) => Date.parse(b) - Date.parse(a))[0] ?? new Date().toISOString();

    return {
      source,
      jobsFound: sourceJobs.length,
      jobsFoundToday: sourceJobs.filter((job) => new Date(job.scrapedTime).toDateString() === today).length,
      jobsApplied: appliedJobs.length,
      jobsAppliedToday: appliedJobs.filter((job) => isSameDay(job.appliedAt, today)).length,
      activeJobs: sourceJobs.filter((job) => job.status !== "EXPIRED" && job.status !== "REJECTED").length,
      successRate: sourceJobs.length ? 100 : 0,
      lastRunTime: latest,
      status: sourceJobs.length ? ("Completed" as const) : ("Idle" as const),
      averageScore: sourceJobs.length
        ? Math.round((sourceJobs.reduce((sum, job) => sum + job.gptRelevanceScore, 0) / sourceJobs.length) * 10) / 10
        : 0
    };
  });
}

function aggregateApplicationHistory(days: DashboardAnalytics["daily"], range: HistoryRange) {
  const buckets = new Map<string, { label: string; applied: number; sortKey: string }>();

  for (const day of days) {
    const date = new Date(`${day.date}T00:00:00`);
    const sortKey = range === "Daily" ? day.date : range === "Weekly" ? getWeekStartKey(date) : day.date.slice(0, 7);
    const label = range === "Daily" ? day.date.slice(5) : sortKey;
    const bucket = buckets.get(sortKey) ?? { label, applied: 0, sortKey };
    bucket.applied += day.applied;
    buckets.set(sortKey, bucket);
  }

  return [...buckets.values()].sort((a, b) => a.sortKey.localeCompare(b.sortKey));
}

function getWeekStartKey(date: Date) {
  const weekStart = new Date(date);
  const day = weekStart.getDay() || 7;
  weekStart.setDate(weekStart.getDate() - day + 1);
  return weekStart.toISOString().slice(0, 10);
}

function isSameDay(value: string | undefined, today: string) {
  return value ? new Date(value).toDateString() === today : false;
}

function toDateKey(value: string) {
  return new Date(value).toISOString().slice(0, 10);
}
