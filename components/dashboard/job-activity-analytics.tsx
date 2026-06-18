"use client";

import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
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

export function JobActivityAnalytics({ analytics }: { analytics: DashboardAnalytics }) {
  const activeStatuses = analytics.statusBreakdown.filter((item) => item.count > 0);
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
            <h2 className="text-sm font-semibold">Daily Job Activity</h2>
            <p className="text-sm text-muted">Scraped jobs, applications, and shortlist movement by day</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="neutral">{totals.scraped.toLocaleString("en-IN")} scraped</Badge>
            <Badge tone="success">{totals.applied.toLocaleString("en-IN")} applied</Badge>
            <Badge tone="accent">{totals.saved.toLocaleString("en-IN")} saved</Badge>
          </div>
        </div>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={analytics.daily}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip />
              <Bar dataKey="scraped" name="Scraped" fill="#14b8a6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="applied" name="Applied" fill="#6366f1" radius={[4, 4, 0, 0]} />
              <Bar dataKey="saved" name="Saved" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid gap-3">
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

        <div className="rounded-md border border-border bg-panel p-4">
          <h2 className="text-sm font-semibold">Average Score Trend</h2>
          <p className="mb-4 text-sm text-muted">Daily GPT score out of 10</p>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics.daily}>
                <XAxis dataKey="date" hide />
                <YAxis domain={[0, 10]} tickLine={false} axisLine={false} fontSize={12} />
                <Tooltip />
                <Line type="monotone" dataKey="averageScore" stroke="#14b8a6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </section>
  );
}

export function buildJobActivityAnalytics(jobs: Job[], analytics: DashboardAnalytics): DashboardAnalytics {
  return {
    ...analytics,
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

function buildStatusBreakdown(jobs: Job[]) {
  const statuses: JobStatus[] = ["UNAPPLIED", "APPLIED", "INTERVIEW", "REJECTED", "OFFER", "EXPIRED", "SAVED"];
  return statuses.map((status) => ({
    status,
    count: jobs.filter((job) => job.status === status).length
  }));
}
