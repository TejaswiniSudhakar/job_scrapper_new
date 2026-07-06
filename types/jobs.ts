export type JobStatus =
  | "UNAPPLIED"
  | "APPLIED"
  | "INTERVIEW"
  | "REJECTED"
  | "OFFER"
  | "EXPIRED"
  | "SAVED";

export type ScraperSource = string;

export type ScraperStatus = "Running" | "Failed" | "Completed" | "Idle";

export type WorkMode = "Remote" | "Hybrid" | "Onsite";

export type Job = {
  id: string;
  jobTitle: string;
  company: string;
  location: string;
  salary?: string;
  salaryMin?: number;
  salaryMax?: number;
  experienceRequired: string;
  employmentType: string;
  workMode: WorkMode;
  source: ScraperSource;
  postedTime: string;
  scrapedTime: string;
  gptRelevanceScore: number;
  matchPercentage: number;
  applyLink: string;
  status: JobStatus;
  notes: string;
  clickCount: number;
  lastOpenedAt?: string;
  appliedAt?: string;
  duplicateScore?: number;
  duplicateOf?: string;
  description: string;
  companyInfo: string;
  requiredSkills: string[];
  benefits: string[];
  gptSummary: string;
  gptReasoning: string;
  scoreBreakdown: {
    skillMatch: number;
    salaryMatch: number;
    experienceMatch: number;
    overallScore: number;
  };
  isNew?: boolean;
};

export type ScraperMetric = {
  source: ScraperSource;
  jobsFound: number;
  jobsFoundToday: number;
  jobsApplied: number;
  jobsAppliedToday: number;
  activeJobs: number;
  successRate: number;
  lastRunTime: string;
  status: ScraperStatus;
  averageScore: number;
};

export type DashboardAnalytics = {
  totalJobsFound: number;
  totalJobsApplied: number;
  totalActiveJobs: number;
  jobsScrapedToday: number;
  jobsAppliedToday: number;
  successRate: number;
  scrapers: ScraperMetric[];
  daily: DailyJobMetric[];
  statusBreakdown: StatusMetric[];
};

export type DailyJobMetric = {
  date: string;
  scraped: number;
  applied: number;
  saved: number;
  interviews: number;
  rejected: number;
  averageScore: number;
};

export type StatusMetric = {
  status: JobStatus;
  count: number;
};

export type JobFilters = {
  query: string;
  sources: ScraperSource[];
  statuses: JobStatus[];
  workModes: WorkMode[];
  companies: string[];
  locations: string[];
  minScore: number;
  sortBy: "freshest" | "oldest" | "bestScore";
  minSalary?: number;
  maxSalary?: number;
  postedWithinDays?: 1 | 3 | 7 | 30;
};

export type SavedSearch = {
  id: string;
  name: string;
  filters: Partial<JobFilters>;
  color: string;
};

export type RealtimeEvent =
  | { type: "job.created"; payload: Job }
  | { type: "job.updated"; payload: Job }
  | { type: "scraper.completed"; payload: ScraperMetric }
  | { type: "scraper.failed"; payload: ScraperMetric }
  | { type: "scoring.completed"; payload: { jobId: string; score: number } };
