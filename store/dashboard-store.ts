"use client";

import { create } from "zustand";
import type { Job, JobFilters, JobStatus, SavedSearch } from "@/types/jobs";
import { updateJobStatus as apiUpdateJobStatus, deleteJobFromDb } from "@/lib/api/jobs";

type Toast = {
  id: string;
  title: string;
  description: string;
  tone: "success" | "warning" | "danger" | "info";
};

type PersistedJobState = Partial<Pick<Job, "status" | "notes" | "clickCount" | "lastOpenedAt" | "appliedAt">> & {
  deleted?: boolean;
};

const jobStateStorageKey = "job-dashboard-job-state";

type DashboardState = {
  jobs: Job[];
  selectedJob?: Job;
  filters: JobFilters;
  savedSearches: SavedSearch[];
  toasts: Toast[];
  hiddenColumns: string[];
  darkMode: boolean;
  setJobs: (jobs: Job[]) => void;
  addJob: (job: Job) => void;
  deleteJob: (jobId: string) => void;
  updateStatus: (jobId: string, status: JobStatus) => void;
  selectJob: (job?: Job) => void;
  updateFilters: (filters: Partial<JobFilters>) => void;
  setSavedSearches: (savedSearches: SavedSearch[]) => void;
  pushToast: (toast: Omit<Toast, "id">) => void;
  dismissToast: (id: string) => void;
  toggleColumn: (columnId: string) => void;
  toggleTheme: () => void;
};

const defaultFilters: JobFilters = {
  query: "",
  sources: [],
  statuses: [],
  workModes: [],
  companies: [],
  locations: [],
  minScore: 5,
  sortBy: "freshest"
};

export const useDashboardStore = create<DashboardState>((set) => ({
  jobs: [],
  filters: defaultFilters,
  savedSearches: [],
  toasts: [],
  hiddenColumns: [],
  darkMode: false,
  setJobs: (jobs) =>
    set((state) => ({
      jobs: jobs
        .map((job) => {
          const existing = state.jobs.find((item) => item.id === job.id);
          const persisted = loadPersistedJobState(job.id);
          if (persisted?.deleted) return undefined;

          return existing
            ? {
                ...job,
                status: existing.status,
                notes: existing.notes,
                clickCount: existing.clickCount,
                lastOpenedAt: existing.lastOpenedAt,
                appliedAt: existing.appliedAt,
                isNew: job.isNew || existing.isNew
              }
            : persisted
              ? { ...job, ...persisted }
              : job;
        })
        .filter((job): job is Job => Boolean(job))
    })),
  addJob: (job) =>
    set((state) => ({
      jobs: [job, ...state.jobs.filter((item) => item.id !== job.id)]
    })),
  deleteJob: (jobId) =>
    set((state) => {
      const existing = state.jobs.find((job) => job.id === jobId);
      savePersistedJobState(jobId, { ...existing, deleted: true });

      // Persist to backend DB
      deleteJobFromDb(jobId).catch(() => {});

      return {
        jobs: state.jobs.filter((job) => job.id !== jobId),
        selectedJob: state.selectedJob?.id === jobId ? undefined : state.selectedJob
      };
    }),
  updateStatus: (jobId, status) =>
    set((state) => {
      const existing = state.jobs.find((job) => job.id === jobId);
      const appliedAt =
        status === "APPLIED"
          ? existing?.appliedAt ?? new Date().toISOString()
          : existing?.appliedAt;
      if (existing) savePersistedJobState(jobId, { ...existing, status, appliedAt });

      // Persist to backend DB
      apiUpdateJobStatus(jobId, status).catch(() => {});

      return {
        jobs: state.jobs.map((job) => (job.id === jobId ? { ...job, status, appliedAt } : job)),
        selectedJob:
          state.selectedJob?.id === jobId ? { ...state.selectedJob, status, appliedAt } : state.selectedJob
      };
    }),
  selectJob: (job) => set({ selectedJob: job }),
  updateFilters: (filters) =>
    set((state) => ({
      filters: { ...state.filters, ...filters }
    })),
  setSavedSearches: (savedSearches) => set({ savedSearches }),
  pushToast: (toast) =>
    set((state) => ({
      toasts: [
        {
          id: crypto.randomUUID(),
          ...toast
        },
        ...state.toasts
      ].slice(0, 5)
    })),
  dismissToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id)
    })),
  toggleColumn: (columnId) =>
    set((state) => ({
      hiddenColumns: state.hiddenColumns.includes(columnId)
        ? state.hiddenColumns.filter((id) => id !== columnId)
        : [...state.hiddenColumns, columnId]
    })),
  toggleTheme: () =>
    set((state) => {
      document.documentElement.classList.toggle("dark", !state.darkMode);
      return { darkMode: !state.darkMode };
    })
}));

function loadPersistedJobState(jobId: string): PersistedJobState | undefined {
  if (typeof window === "undefined") return undefined;

  try {
    const data = JSON.parse(window.localStorage.getItem(jobStateStorageKey) ?? "{}") as Record<string, PersistedJobState>;
    return data[jobId];
  } catch {
    return undefined;
  }
}

function savePersistedJobState(jobId: string, job: PersistedJobState) {
  if (typeof window === "undefined") return;

  try {
    const data = JSON.parse(window.localStorage.getItem(jobStateStorageKey) ?? "{}") as Record<string, PersistedJobState>;
    data[jobId] = {
      status: job.status,
      notes: job.notes,
      clickCount: job.clickCount,
      lastOpenedAt: job.lastOpenedAt,
      appliedAt: job.appliedAt,
      deleted: job.deleted
    };
    window.localStorage.setItem(jobStateStorageKey, JSON.stringify(data));
  } catch {
    // Local storage persistence is best-effort.
  }
}
