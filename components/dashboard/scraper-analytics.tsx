"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Badge } from "@/components/ui/badge";
import { formatRelativeTime } from "@/lib/utils";
import type { DashboardAnalytics, ScraperMetric, ScraperStatus } from "@/types/jobs";

const colors = ["#14b8a6", "#6366f1", "#f59e0b", "#22c55e", "#ef4444", "#8b5cf6", "#06b6d4"];

const statusTone: Record<ScraperStatus, React.ComponentProps<typeof Badge>["tone"]> = {
  Running: "accent",
  Failed: "danger",
  Completed: "success",
  Idle: "neutral"
};

export function ScraperAnalytics({ analytics }: { analytics: DashboardAnalytics }) {
  return (
    <section className="space-y-3">
      <div className="rounded-md border border-border bg-panel p-4">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Scraper Analytics</h2>
            <p className="text-sm text-muted">Daily and overall scraper output from live job data</p>
          </div>
          <Badge tone="accent">Live</Badge>
        </div>

        <div className="overflow-hidden rounded-md border border-border">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-background text-left text-xs uppercase text-muted">
              <tr>
                <th className="px-3 py-2">Scraper</th>
                <th className="px-3 py-2">Total scraped</th>
                <th className="px-3 py-2">Scraped today</th>
                <th className="px-3 py-2">Total applied</th>
                <th className="px-3 py-2">Applied today</th>
                <th className="px-3 py-2">Last run</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {analytics.scrapers.map((scraper) => (
                <tr key={scraper.source} className="border-t border-border">
                  <td className="px-3 py-2 font-medium">{scraper.source}</td>
                  <td className="px-3 py-2">{scraper.jobsFound.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-2">{scraper.jobsFoundToday.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-2">{scraper.jobsApplied.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-2">{scraper.jobsAppliedToday.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-2 text-muted">{formatRelativeTime(scraper.lastRunTime)}</td>
                  <td className="px-3 py-2">
                    <Badge tone={statusTone[scraper.status]}>{scraper.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <SourceDonut title="Overall Jobs Scraped" data={analytics.scrapers} dataKey="jobsFound" />
        <SourceDonut title="Jobs Scraped Today" data={analytics.scrapers} dataKey="jobsFoundToday" />
        <SourceDonut title="Overall Jobs Applied" data={analytics.scrapers} dataKey="jobsApplied" />
        <SourceDonut title="Jobs Applied Today" data={analytics.scrapers} dataKey="jobsAppliedToday" />
      </div>
    </section>
  );
}

function SourceDonut({
  title,
  data,
  dataKey
}: {
  title: string;
  data: ScraperMetric[];
  dataKey: keyof Pick<ScraperMetric, "jobsFound" | "jobsFoundToday" | "jobsApplied" | "jobsAppliedToday">;
}) {
  const chartData = data.filter((item) => Number(item[dataKey]) > 0);
  const total = chartData.reduce((sum, item) => sum + Number(item[dataKey]), 0);

  return (
    <div className="rounded-md border border-border bg-panel p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-xs text-muted">{total.toLocaleString("en-IN")} total</p>
      </div>
      {chartData.length ? (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={chartData} dataKey={dataKey} nameKey="source" innerRadius={44} outerRadius={72} paddingAngle={3}>
                {chartData.map((entry, index) => (
                  <Cell key={entry.source} fill={colors[index % colors.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="flex h-48 items-center justify-center rounded-md bg-background text-sm text-muted">No data yet</div>
      )}
      <div className="mt-3 space-y-2">
        {data.map((item, index) => (
          <div key={item.source} className="flex items-center justify-between gap-2 text-xs">
            <span className="flex min-w-0 items-center gap-2">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />
              <span className="truncate">{item.source}</span>
            </span>
            <span className="font-medium">{Number(item[dataKey]).toLocaleString("en-IN")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
