import { savedSearches } from "@/lib/mock/jobs";
import type { DashboardAnalytics, Job, JobFilters, JobStatus, SavedSearch } from "@/types/jobs";

export async function fetchJobs(filters?: Partial<JobFilters>): Promise<Job[]> {
  const response = await fetch("/api/jobs", { cache: "no-store" });
  const data = (await response.json()) as { jobs?: Job[]; error?: string };

  if (!response.ok) {
    throw new Error(data.error ?? "Unable to load scraper jobs.");
  }

  let jobs = [...(data.jobs ?? [])].sort((a, b) => Date.parse(b.scrapedTime) - Date.parse(a.scrapedTime));

  if (filters?.query) {
    const query = filters.query.toLowerCase();
    jobs = jobs.filter((job) =>
      [job.jobTitle, job.company, job.location, job.source, job.description]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }

  if (filters?.sources?.length) {
    jobs = jobs.filter((job) => filters.sources?.includes(job.source));
  }

  if (filters?.statuses?.length) {
    jobs = jobs.filter((job) => filters.statuses?.includes(job.status));
  }

  if (filters?.workModes?.length) {
    jobs = jobs.filter((job) => filters.workModes?.includes(job.workMode));
  }

  if (filters?.minScore) {
    jobs = jobs.filter((job) => job.gptRelevanceScore >= filters.minScore!);
  }

  return jobs;
}

export async function fetchAnalytics(): Promise<DashboardAnalytics> {
  const response = await fetch("/api/analytics", { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load scraper analytics.");
  return response.json();
}

export async function fetchSavedSearches(): Promise<SavedSearch[]> {
  return savedSearches;
}

export async function updateJobStatus(jobId: string, status: JobStatus): Promise<{ jobId: string; status: JobStatus; appliedAt?: string }> {
  const response = await fetch("/api/jobs/status", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jobId, status })
  });

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error ?? "Failed to update job status");
  }

  return response.json();
}

export async function deleteJobFromDb(jobId: string): Promise<void> {
  await fetch("/api/jobs/status", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jobId })
  });
}

export async function generateResume(job: { jobTitle: string; company: string; description: string; applyLink: string; experienceRequired: string }): Promise<{
  pdfBase64?: string;
  texPath?: string;
  profile?: string;
  matchedSkills?: string[];
  error?: string;
}> {
  const response = await fetch("/api/jobs/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(job)
  });

  return response.json();
}

export async function trackApplyClick(jobId: string): Promise<{ jobId: string; openedAt: string }> {
  return { jobId, openedAt: new Date().toISOString() };
}
