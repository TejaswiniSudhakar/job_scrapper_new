import { NextResponse } from "next/server";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { parseCsv, type CsvRow } from "@/lib/csv-parser";
import { normalizeDate, normalizeOptionalDate, normalizeSource, normalizeStatus, scoreToTen } from "@/lib/normalize";
import type { Job, WorkMode } from "@/types/jobs";

const jobsCsvPath = path.join(process.env.JOB_SCRAPER_DATA_DIR ?? process.cwd(), "jobs.csv");

let jobsCache: { mtimeMs: number; jobs: Job[] } | undefined;

export async function GET() {
  try {
    const jobs = await readJobs();

    return NextResponse.json({ jobs, sourceFile: jobsCsvPath });
  } catch (error) {
    return NextResponse.json(
      {
        jobs: [],
        error: error instanceof Error ? error.message : "Unable to read scraper jobs.",
        sourceFile: jobsCsvPath
      },
      { status: 500 }
    );
  }
}

async function readJobs() {
  const file = await stat(jobsCsvPath);
  if (jobsCache?.mtimeMs === file.mtimeMs) return jobsCache.jobs;

  const csv = await readFile(jobsCsvPath, "utf8");
  const rows = parseCsv(csv);
  const jobs = rows
    .filter((row) => row.status?.toUpperCase() !== "DELETED")
    .map(mapRowToJob)
    .sort((a, b) => Date.parse(b.scrapedTime) - Date.parse(a.scrapedTime));
  jobsCache = { mtimeMs: file.mtimeMs, jobs };

  return jobs;
}


function mapRowToJob(row: CsvRow): Job {
  const finalScore = toNumber(row.final_score);
  const gptScore = toNumber(row.gpt_score);
  const preScore = toNumber(row.pre_score);
  const score = scoreToTen(finalScore ?? gptScore ?? preScore ?? 0);
  const createdAt = normalizeDate(row.created_at);
  const description = row.job_description || "No description captured.";
  const source = normalizeSource(row.source);
  const experienceRequired = normalizeExperience(row.experience_required, row.reason, description);
  const salary = inferSalary(description, row.reason);

  return {
    id: row.id ? `job_${row.id}` : row.url_hash || row.job_url,
    jobTitle: row.title || "Untitled job",
    company: row.company || "Unknown company",
    location: inferLocation(row.job_url, description),
    salary,
    experienceRequired,
    employmentType: inferEmploymentType(description),
    workMode: inferWorkMode(description),
    source,
    postedTime: createdAt,
    scrapedTime: createdAt,
    gptRelevanceScore: score,
    matchPercentage: Math.round(score * 10),
    applyLink: row.job_url || "#",
    status: normalizeStatus(row.status),
    notes: "",
    clickCount: 0,
    appliedAt: normalizeOptionalDate(row.applied_at || row.last_opened_at),
    description,
    companyInfo: row.company ? `${row.company} job scraped from ${source}.` : "Company details not captured.",
    requiredSkills: inferSkills(description),
    benefits: [],
    gptSummary: summarizeDescription(description),
    gptReasoning: row.reason || "No GPT reasoning captured.",
    scoreBreakdown: parseScoreBreakdown(row.reason, score)
  };
}

function normalizeExperience(rawExperience: string, reasoning: string, description: string) {
  const cleaned = rawExperience.trim();
  if (cleaned && !/^not\s+mentioned$/i.test(cleaned) && cleaned !== "-1") {
    return formatExperience(cleaned);
  }

  return inferExperienceFromReasoning(reasoning) ?? inferExperienceFromDescription(description) ?? "Not mentioned";
}

function inferExperienceFromReasoning(text: string) {
  const normalized = text.replace(/\s+/g, " ");
  const rangeMatch = normalized.match(
    /(?:preferred|required|requires?|desired|minimum|min\.?|at least|compared to the required|below the desired|falls? short of the preferred)\s*(\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(\d+(?:\.\d+)?)\s*(?:\+?\s*)?(?:years?|yrs?)/i
  );

  if (rangeMatch) return formatExperience(`${rangeMatch[1]}-${rangeMatch[2]} years`);

  const singleMatch = normalized.match(
    /(?:preferred|required|requires?|desired|minimum|min\.?|at least|compared to the required|below the desired)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)/i
  );

  if (singleMatch) return formatExperience(`${singleMatch[1]} years`);

  return undefined;
}

function inferExperienceFromDescription(text: string) {
  const normalized = text.replace(/\s+/g, " ");
  const rangeMatch = normalized.match(
    /(?:experience|exp|minimum|min\.?|at least|required|requires?)\D{0,30}(\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(\d+(?:\.\d+)?)\s*(?:\+?\s*)?(?:years?|yrs?)/i
  );

  if (rangeMatch) return formatExperience(`${rangeMatch[1]}-${rangeMatch[2]} years`);

  const singleMatch = normalized.match(
    /(?:minimum|min\.?|at least|required|requires?)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)/i
  );

  if (singleMatch) return formatExperience(`${singleMatch[1]} years`);

  const fallbackMatch = normalized.match(/(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience/i);
  if (fallbackMatch) return formatExperience(`${fallbackMatch[1]} years`);

  return undefined;
}

function formatExperience(value: string) {
  const numbers = value.match(/\d+(?:\.\d+)?/g) ?? [];
  if (!numbers.length) return value;
  if (numbers.length >= 2) return `${numbers[0]}-${numbers[1]} years`;
  return `${numbers[0]} years`;
}

function inferWorkMode(text: string): WorkMode {
  const normalized = text.toLowerCase();
  if (normalized.includes("remote")) return "Remote";
  if (normalized.includes("hybrid")) return "Hybrid";
  return "Onsite";
}

function inferEmploymentType(text: string) {
  const normalized = text.toLowerCase();
  if (normalized.includes("intern")) return "Internship";
  if (normalized.includes("contract")) return "Contract";
  if (normalized.includes("part time") || normalized.includes("part-time")) return "Part-time";
  return "Full-time";
}

function inferSalary(description: string, reasoning: string) {
  const text = `${description} ${reasoning}`.replace(/\s+/g, " ");
  const salaryLabelMatch = text.match(
    /(?:salary|ctc|compensation|package)\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(k|lacs?|lakhs?|lpa|pa|per annum|p\.a\.|\/month|per month|monthly)?(?:\s*(?:-|to|–|—)\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(k|lacs?|lakhs?|lpa|pa|per annum|p\.a\.|\/month|per month|monthly)?)?/i
  );

  if (salaryLabelMatch) {
    return formatSalaryMatch(salaryLabelMatch[1], salaryLabelMatch[2], salaryLabelMatch[3], salaryLabelMatch[4]);
  }

  const compactRangeMatch = text.match(
    /(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(k|lacs?|lakhs?|lpa)\s*(?:-|to|–|—)\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(k|lacs?|lakhs?|lpa)/i
  );

  if (compactRangeMatch) {
    return formatSalaryMatch(compactRangeMatch[1], compactRangeMatch[2], compactRangeMatch[3], compactRangeMatch[4]);
  }

  return "Not mentioned";
}

function formatSalaryMatch(minValue: string, minUnit = "", maxValue?: string, maxUnit = "") {
  const unit = normalizeSalaryUnit(maxUnit || minUnit);
  const min = `${minValue.replaceAll(",", "")}${unit ? ` ${unit}` : ""}`;
  if (!maxValue) return min;
  const max = `${maxValue.replaceAll(",", "")}${unit ? ` ${unit}` : ""}`;
  return `${min}-${max}`;
}

function normalizeSalaryUnit(unit: string) {
  const normalized = unit.toLowerCase();
  if (normalized === "k") return "k/month";
  if (normalized.includes("lac") || normalized.includes("lakh") || normalized === "lpa") return "LPA";
  if (normalized.includes("month") || normalized.includes("/month") || normalized.includes("monthly")) return "/month";
  if (normalized.includes("annum") || normalized.includes("p.a") || normalized === "pa") return "PA";
  return "";
}

function inferLocation(url: string, description: string) {
  const combined = `${url} ${description}`.toLowerCase();
  const locations = ["bengaluru", "bangalore", "hyderabad", "chennai", "pune", "mumbai", "delhi", "gurgaon", "noida"];
  const match = locations.find((location) => combined.includes(location));
  if (!match) return "Not specified";
  return match === "bengaluru" ? "Bengaluru" : match[0].toUpperCase() + match.slice(1);
}

function inferSkills(description: string) {
  const knownSkills = [
    "Java", "Python", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
    "Spring Boot", "Microservices", "REST", "GraphQL", "gRPC",
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Cassandra", "Elasticsearch",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
    "React", "Angular", "Vue", "Next.js", "Node.js",
    "Kafka", "Spark", "Airflow", "Hadoop",
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
    "Selenium", "CI/CD", "Jenkins", "Git", "Linux"
  ];

  return knownSkills.filter((skill) => description.toLowerCase().includes(skill.toLowerCase())).slice(0, 10);
}

function parseScoreBreakdown(reason: string, overallScore: number) {
  const expMatch = reason?.match(/Experience=(\d+(?:\.\d+)?)/);
  const skillMatch = reason?.match(/Skills=(\d+(?:\.\d+)?)/);
  const simMatch = reason?.match(/Similarity=(\d+(?:\.\d+)?)/);

  return {
    skillMatch: skillMatch ? Number(skillMatch[1]) : overallScore,
    salaryMatch: simMatch ? Number(simMatch[1]) : 0,
    experienceMatch: expMatch ? Number(expMatch[1]) : overallScore,
    overallScore
  };
}

function summarizeDescription(description: string) {
  const trimmed = description.replace(/\s+/g, " ").trim();
  return trimmed.length > 220 ? `${trimmed.slice(0, 220)}...` : trimmed;
}

function toNumber(value: string) {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

