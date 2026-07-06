"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { KpiStrip } from "@/components/dashboard/kpi-strip";
import { buildJobActivityAnalytics, JobActivityAnalytics } from "@/components/dashboard/job-activity-analytics";
import { ScraperAnalytics } from "@/components/dashboard/scraper-analytics";
import { AppShell } from "@/components/layout/app-shell";
import { Toaster } from "@/components/layout/toaster";
import { FiltersBar } from "@/components/jobs/filters-bar";
import { JobDetailsDrawer } from "@/components/jobs/job-details-drawer";
import { JobGrid } from "@/components/jobs/job-grid";
import { fetchAnalytics, fetchJobs } from "@/lib/api/jobs";
import { useLiveJobs } from "@/hooks/use-live-jobs";
import { useDashboardStore } from "@/store/dashboard-store";
import type { Job } from "@/types/jobs";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 20_000,
      refetchOnWindowFocus: false
    }
  }
});

export default function Page() {
  return (
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>
  );
}

function DashboardPage() {
  useLiveJobs();
  const [mounted, setMounted] = useState(false);
  const hasLoadedJobs = useRef(false);
  const knownJobIds = useRef(new Set<string>());
  const jobs = useDashboardStore((state) => state.jobs);
  const setJobs = useDashboardStore((state) => state.setJobs);
  const filters = useDashboardStore((state) => state.filters);
  const pushToast = useDashboardStore((state) => state.pushToast);
  const debouncedFilters = useDebouncedValue(filters, 250);

  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: () => fetchJobs(),
    refetchInterval: 5_000,
    refetchIntervalInBackground: true
  });

  const analyticsQuery = useQuery({
    queryKey: ["analytics"],
    queryFn: fetchAnalytics,
    refetchInterval: 15_000,
    refetchIntervalInBackground: true
  });

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!jobsQuery.data) return;

    if (!hasLoadedJobs.current) {
      knownJobIds.current = new Set(jobsQuery.data.map((job) => job.id));
      hasLoadedJobs.current = true;
      setJobs(jobsQuery.data);
      return;
    }

    const newJobs = jobsQuery.data.filter((job) => !knownJobIds.current.has(job.id));
    const newJobIds = new Set(newJobs.map((job) => job.id));
    knownJobIds.current = new Set(jobsQuery.data.map((job) => job.id));

    setJobs(
      jobsQuery.data.map((job) => ({
        ...job,
        isNew: newJobIds.has(job.id) || job.isNew
      }))
    );
  }, [jobsQuery.data, setJobs]);

  const filteredJobs = useMemo(() => applyClientFilters(jobs, debouncedFilters), [jobs, debouncedFilters]);
  const liveAnalytics = useMemo(
    () => (analyticsQuery.data ? buildJobActivityAnalytics(jobs, analyticsQuery.data) : undefined),
    [analyticsQuery.data, jobs]
  );

  function exportCsv() {
    const headers = [
      "Job Title",
      "Company",
      "Location",
      "Salary",
      "Experience Required",
      "Employment Type",
      "Source",
      "Posted Time",
      "Scraped Time",
      "GPT Relevance Score",
      "Match Percentage",
      "Apply Link",
      "Job Status",
      "Notes"
    ];
    const rows = filteredJobs.map((job) => [
      job.jobTitle,
      job.company,
      job.location,
      job.salary ?? "",
      job.experienceRequired,
      job.employmentType,
      job.source,
      job.postedTime,
      job.scrapedTime,
      job.gptRelevanceScore,
      job.matchPercentage,
      job.applyLink,
      job.status,
      job.notes
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `job-dashboard-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    pushToast({
      tone: "success",
      title: "Export ready",
      description: `${filteredJobs.length} jobs exported to CSV.`
    });
  }

  if (!mounted) return null;

  return (
    <AppShell>
      {liveAnalytics ? <KpiStrip analytics={liveAnalytics} /> : null}
      {liveAnalytics ? <ScraperAnalytics analytics={liveAnalytics} /> : null}
      {liveAnalytics ? <JobActivityAnalytics analytics={liveAnalytics} /> : null}
      <FiltersBar onExport={exportCsv} onRefresh={() => { void jobsQuery.refetch(); void analyticsQuery.refetch(); }} isRefreshing={jobsQuery.isFetching || analyticsQuery.isFetching} />
      <section className="overflow-hidden rounded-md border border-border bg-panel">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold">Live Job Feed</h2>
            <p className="text-sm text-muted">
              {filteredJobs.length.toLocaleString("en-IN")} jobs · New jobs appear at the top
            </p>
          </div>
          <div className="text-xs text-muted">Sticky headers · Resizable columns · Multi-filter · Bulk select · Pagination</div>
        </div>
        <JobGrid jobs={filteredJobs} />
      </section>
      <JobDetailsDrawer />
      <Toaster />
    </AppShell>
  );
}

function applyClientFilters(jobs: Job[], filters: ReturnType<typeof useDashboardStore.getState>["filters"]) {
  const filtered = jobs.filter((job) => {
    if (filters.query && !matchesSearchQuery(job, filters.query)) return false;
    if (filters.minScore && job.gptRelevanceScore < filters.minScore) return false;
    if (filters.sources.length && !filters.sources.includes(job.source)) return false;
    if (filters.workModes.length && !filters.workModes.includes(job.workMode)) return false;
    if (filters.statuses.length && !filters.statuses.includes(job.status)) return false;
    if (filters.postedWithinDays) {
      const age = Date.now() - Date.parse(job.postedTime);
      if (age > filters.postedWithinDays * 24 * 60 * 60 * 1000) return false;
    }
    return true;
  });

  return [...filtered].sort((a, b) => {
    const statusOrder = getStatusSortOrder(a.status) - getStatusSortOrder(b.status);
    if (statusOrder !== 0) return statusOrder;

    if (filters.sortBy === "oldest") return Date.parse(a.scrapedTime) - Date.parse(b.scrapedTime);
    if (filters.sortBy === "bestScore") return b.gptRelevanceScore - a.gptRelevanceScore;
    return Date.parse(b.scrapedTime) - Date.parse(a.scrapedTime);
  });
}

function getStatusSortOrder(status: Job["status"]) {
  return status === "APPLIED" ? 1 : 0;
}

function matchesSearchQuery(job: Job, query: string) {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return true;

  return [
    job.jobTitle,
    job.company,
    job.location,
    job.source,
    job.description,
    job.gptSummary,
    job.gptReasoning,
    job.requiredSkills.join(" "),
    job.notes
  ]
    .join(" ")
    .toLowerCase()
    .includes(normalizedQuery);
}

function useDebouncedValue<T>(value: T, delayMs: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [value, delayMs]);

  return debouncedValue;
}
