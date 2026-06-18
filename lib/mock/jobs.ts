import type { DashboardAnalytics, Job, SavedSearch } from "@/types/jobs";

const now = new Date("2026-06-08T19:30:00+05:30");

function iso(minutesAgo: number) {
  return new Date(now.getTime() - minutesAgo * 60_000).toISOString();
}

export const mockJobs: Job[] = [
  {
    id: "job_101",
    jobTitle: "Software Engineer I",
    company: "JLL",
    location: "Bengaluru, Karnataka",
    salary: "₹18L - ₹30L",
    salaryMin: 1800000,
    salaryMax: 3000000,
    experienceRequired: "1-3 years",
    employmentType: "Full-time",
    workMode: "Hybrid",
    source: "LinkedIn",
    postedTime: iso(250),
    scrapedTime: iso(4),
    gptRelevanceScore: 89,
    matchPercentage: 92,
    applyLink: "https://in.linkedin.com/jobs/view/software-engineer-i-at-jll-4422999130",
    status: "UNAPPLIED",
    notes: "Strong AI tooling exposure and backend overlap.",
    clickCount: 1,
    lastOpenedAt: iso(2),
    duplicateScore: 92,
    description:
      "Build and maintain customer-facing web applications across frontend and backend services. Collaborate with senior engineers on AI-centric solutions, LLM API experiments, integrations, testing, debugging, and production deployments.",
    companyInfo:
      "JLL is a global real estate and investment management company with growing internal product and intelligence teams.",
    requiredSkills: ["Java", "Spring Boot", "REST APIs", "SQL", "React", "LLM APIs"],
    benefits: ["Hybrid work", "Mentorship", "AI project exposure", "Enterprise product ownership"],
    gptSummary:
      "A strong early-career engineering role with backend, full-stack, and AI experimentation responsibilities.",
    gptReasoning:
      "The role matches Java backend experience, REST API work, SQL, and interest in AI tooling. Salary and experience range are aligned with target expectations.",
    scoreBreakdown: {
      skillMatch: 92,
      salaryMatch: 85,
      experienceMatch: 90,
      overallScore: 89
    },
    isNew: true
  },
  {
    id: "job_102",
    jobTitle: "Backend Java Developer",
    company: "Tata Consultancy Services",
    location: "Pune, Maharashtra",
    salary: "₹10L - ₹18L",
    salaryMin: 1000000,
    salaryMax: 1800000,
    experienceRequired: "2-4 years",
    employmentType: "Full-time",
    workMode: "Onsite",
    source: "Naukri",
    postedTime: iso(680),
    scrapedTime: iso(26),
    gptRelevanceScore: 78,
    matchPercentage: 81,
    applyLink: "https://www.naukri.com/job-listings-backend-java-developer",
    status: "SAVED",
    notes: "Good Java fit, less AI exposure.",
    clickCount: 0,
    duplicateScore: 36,
    description:
      "Design REST services, maintain Spring Boot applications, write SQL procedures, and support enterprise deployments.",
    companyInfo: "Large IT services organization with enterprise delivery teams.",
    requiredSkills: ["Java", "Spring Boot", "Microservices", "Oracle SQL", "PL/SQL"],
    benefits: ["Health coverage", "Learning paths", "Internal mobility"],
    gptSummary: "Solid backend Java role with strong overlap in current skills.",
    gptReasoning:
      "Excellent Java and SQL alignment, but the role is more traditional services delivery and has lower strategic upside.",
    scoreBreakdown: {
      skillMatch: 86,
      salaryMatch: 70,
      experienceMatch: 78,
      overallScore: 78
    }
  },
  {
    id: "job_103",
    jobTitle: "Platform Engineer",
    company: "Razorpay",
    location: "Bengaluru, Karnataka",
    salary: "₹22L - ₹42L",
    salaryMin: 2200000,
    salaryMax: 4200000,
    experienceRequired: "2+ years",
    employmentType: "Full-time",
    workMode: "Hybrid",
    source: "Indeed",
    postedTime: iso(1420),
    scrapedTime: iso(44),
    gptRelevanceScore: 91,
    matchPercentage: 88,
    applyLink: "https://in.indeed.com/viewjob?jk=platform-engineer",
    status: "UNAPPLIED",
    notes: "High upside. Needs cloud confidence.",
    clickCount: 2,
    lastOpenedAt: iso(12),
    description:
      "Own platform tooling, CI/CD workflows, observability, service reliability, and developer productivity for backend teams.",
    companyInfo: "Fintech platform with high-scale engineering systems.",
    requiredSkills: ["Java", "Docker", "Kubernetes", "CI/CD", "GCP", "Observability"],
    benefits: ["High-impact platform work", "Strong engineering culture", "Competitive salary"],
    gptSummary: "High-value platform role that stretches current backend experience toward cloud systems.",
    gptReasoning:
      "Strong match for backend and microservices, with growth areas in Kubernetes and production platform ownership.",
    scoreBreakdown: {
      skillMatch: 84,
      salaryMatch: 94,
      experienceMatch: 82,
      overallScore: 91
    },
    isNew: true
  },
  {
    id: "job_104",
    jobTitle: "Python Automation Engineer",
    company: "Freshworks",
    location: "Chennai, Tamil Nadu",
    salary: "₹12L - ₹24L",
    salaryMin: 1200000,
    salaryMax: 2400000,
    experienceRequired: "1-3 years",
    employmentType: "Full-time",
    workMode: "Remote",
    source: "LinkedIn",
    postedTime: iso(1890),
    scrapedTime: iso(67),
    gptRelevanceScore: 83,
    matchPercentage: 79,
    applyLink: "https://linkedin.com/jobs/view/python-automation-engineer",
    status: "APPLIED",
    notes: "Applied through LinkedIn Easy Apply.",
    clickCount: 1,
    lastOpenedAt: iso(60),
    description:
      "Build internal automation workflows, data collection tools, API integrations, and quality checks for product operations.",
    companyInfo: "SaaS company building customer engagement and support products.",
    requiredSkills: ["Python", "Selenium", "REST APIs", "SQL", "Automation"],
    benefits: ["Remote-friendly", "Automation ownership", "Product exposure"],
    gptSummary: "Good automation fit, but weaker Java/Spring alignment.",
    gptReasoning:
      "The scraping and Selenium experience helps, though long-term backend career alignment is moderate.",
    scoreBreakdown: {
      skillMatch: 80,
      salaryMatch: 82,
      experienceMatch: 86,
      overallScore: 83
    }
  },
  {
    id: "job_105",
    jobTitle: "Associate Software Engineer",
    company: "Zoho",
    location: "Coimbatore, Tamil Nadu",
    salary: "₹8L - ₹16L",
    salaryMin: 800000,
    salaryMax: 1600000,
    experienceRequired: "0-2 years",
    employmentType: "Full-time",
    workMode: "Onsite",
    source: "Naukri",
    postedTime: iso(2880),
    scrapedTime: iso(122),
    gptRelevanceScore: 74,
    matchPercentage: 76,
    applyLink: "https://www.naukri.com/job-listings-associate-software-engineer-zoho",
    status: "INTERVIEW",
    notes: "Recruiter screen scheduled.",
    clickCount: 3,
    lastOpenedAt: iso(18),
    description:
      "Work across product teams to build backend modules, APIs, and data processing features for business applications.",
    companyInfo: "Indian SaaS product company with broad product portfolio.",
    requiredSkills: ["Java", "SQL", "Problem Solving", "APIs"],
    benefits: ["Product company", "Mentorship", "Internal tools"],
    gptSummary: "Stable product role with good early-career fit.",
    gptReasoning: "Strong learning role, although salary ceiling is lower than target.",
    scoreBreakdown: {
      skillMatch: 79,
      salaryMatch: 62,
      experienceMatch: 90,
      overallScore: 74
    }
  },
  {
    id: "job_106",
    jobTitle: "Cloud Backend Engineer",
    company: "Thoughtworks",
    location: "Bengaluru, Karnataka",
    salary: "₹20L - ₹34L",
    salaryMin: 2000000,
    salaryMax: 3400000,
    experienceRequired: "2-5 years",
    employmentType: "Full-time",
    workMode: "Hybrid",
    source: "Company Site",
    postedTime: iso(80),
    scrapedTime: iso(3),
    gptRelevanceScore: 94,
    matchPercentage: 91,
    applyLink: "https://www.thoughtworks.com/careers/jobs/cloud-backend-engineer",
    status: "SAVED",
    notes: "Top opportunity. Tailor resume for GCP and microservices.",
    clickCount: 0,
    duplicateScore: 18,
    description:
      "Develop cloud-native backend services, design APIs, improve delivery pipelines, and pair with client engineering teams.",
    companyInfo: "Technology consultancy known for agile engineering and software craftsmanship.",
    requiredSkills: ["Java", "Spring Boot", "GCP", "Microservices", "CI/CD", "Docker"],
    benefits: ["Engineering mentorship", "Cloud-native projects", "Strong delivery practices"],
    gptSummary: "Best-fit role across backend, microservices, cloud, and career progression.",
    gptReasoning:
      "Excellent alignment with Java/Spring, target cloud growth, API ownership, and consulting exposure.",
    scoreBreakdown: {
      skillMatch: 93,
      salaryMatch: 90,
      experienceMatch: 88,
      overallScore: 94
    },
    isNew: true
  }
];

export const mockAnalytics: DashboardAnalytics = {
  totalJobsFound: 507,
  totalActiveJobs: 342,
  jobsScrapedToday: 126,
  successRate: 91,
  scrapers: [
    {
      source: "LinkedIn",
      jobsFound: 234,
      activeJobs: 144,
      successRate: 93,
      lastRunTime: iso(5),
      status: "Running",
      averageScore: 82
    },
    {
      source: "Naukri",
      jobsFound: 178,
      activeJobs: 121,
      successRate: 88,
      lastRunTime: iso(18),
      status: "Completed",
      averageScore: 76
    },
    {
      source: "Indeed",
      jobsFound: 95,
      activeJobs: 77,
      successRate: 84,
      lastRunTime: iso(32),
      status: "Running",
      averageScore: 79
    }
  ],
  daily: [
    { date: "2026-06-06", scraped: 118, applied: 4, saved: 9, interviews: 1, rejected: 2, averageScore: 7.1 },
    { date: "2026-06-07", scraped: 142, applied: 6, saved: 12, interviews: 2, rejected: 4, averageScore: 7.4 },
    { date: "2026-06-08", scraped: 126, applied: 5, saved: 10, interviews: 1, rejected: 3, averageScore: 7.2 }
  ],
  statusBreakdown: [
    { status: "UNAPPLIED", count: 301 },
    { status: "APPLIED", count: 15 },
    { status: "INTERVIEW", count: 4 },
    { status: "REJECTED", count: 9 },
    { status: "OFFER", count: 1 },
    { status: "EXPIRED", count: 156 },
    { status: "SAVED", count: 21 }
  ]
};

export const savedSearches: SavedSearch[] = [
  {
    id: "remote-python",
    name: "Remote Python Jobs",
    filters: { query: "python", workModes: ["Remote"], minScore: 7 },
    color: "cyan"
  },
  {
    id: "senior-java",
    name: "Senior Java Jobs",
    filters: { query: "java", minScore: 8 },
    color: "emerald"
  },
  {
    id: "high-salary",
    name: "High Salary Roles",
    filters: { minSalary: 2000000, minScore: 8.5 },
    color: "violet"
  }
];
