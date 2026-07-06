"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, FileText, Trash2, Undo2, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { useDashboardStore } from "@/store/dashboard-store";
import { generateResume } from "@/lib/api/jobs";
import type { Job, JobStatus } from "@/types/jobs";

const statuses: JobStatus[] = ["UNAPPLIED", "APPLIED", "INTERVIEW", "REJECTED", "OFFER", "EXPIRED", "SAVED"];


type RecommendedResume = {
  file: string;
  role: string;
  reason: string;
};

const resumeRules: Array<RecommendedResume & { keywords: string[] }> = [
  {
    file: "Nishant_ML.pdf",
    role: "ML / AI roles",
    reason: "Best fit for ML, AI, data science, model, NLP, LLM, PyTorch, or TensorFlow focused roles.",
    keywords: ["machine learning", "ml engineer", " ai ", "artificial intelligence", "deep learning", "llm", "nlp", "computer vision", "pytorch", "tensorflow", "model", "data scientist"]
  },
  {
    file: "Nishant_data_engineer.pdf",
    role: "Data engineering roles",
    reason: "Best fit for ETL, data pipelines, Spark, Airflow, warehouse, analytics engineering, or big data roles.",
    keywords: ["data engineer", "etl", "pipeline", "spark", "hadoop", "airflow", "databricks", "warehouse", "bigquery", "snowflake", "analytics engineer", "big data"]
  },
  {
    file: "Nishant_cloud_engineer.pdf",
    role: "Cloud / DevOps roles",
    reason: "Best fit for cloud, DevOps, SRE, AWS, Azure, GCP, Kubernetes, Docker, Terraform, or platform roles.",
    keywords: ["cloud", "devops", "sre", "aws", "azure", "gcp", "kubernetes", "docker", "terraform", "platform engineer", "site reliability"]
  },
  {
    file: "Nishant_Backend.pdf",
    role: "Backend roles",
    reason: "Best fit for Java, Spring Boot, APIs, microservices, server-side, and backend software engineering roles.",
    keywords: ["backend", "back end", "java", "spring", "spring boot", "api", "microservices", "server", "software engineer", "developer"]
  }
];

function getRecommendedResume(job: Job): RecommendedResume {
  const text = ` ${job.jobTitle} ${job.company} ${job.description} ${job.gptSummary} ${job.gptReasoning} ${job.requiredSkills.join(" ")} `.toLowerCase();
  const scored = resumeRules.map((resume) => ({
    resume,
    score: resume.keywords.reduce((total, keyword) => total + (text.includes(keyword) ? 1 : 0), 0)
  }));

  scored.sort((a, b) => b.score - a.score);
  const selected = scored[0]?.score ? scored[0].resume : resumeRules[3];
  return {
    file: selected.file,
    role: selected.role,
    reason: selected.reason
  };
}

export function JobDetailsDrawer() {
  const job = useDashboardStore((state) => state.selectedJob);
  const selectJob = useDashboardStore((state) => state.selectJob);
  const updateStatus = useDashboardStore((state) => state.updateStatus);
  const deleteJob = useDashboardStore((state) => state.deleteJob);
  const pushToast = useDashboardStore((state) => state.pushToast);
  const recommendedResume = job ? getRecommendedResume(job) : resumeRules[3];
  const [generatingResume, setGeneratingResume] = useState(false);

  async function handleGenerateResume() {
    if (!job) return;
    setGeneratingResume(true);
    try {
      const result = await generateResume({
        jobTitle: job.jobTitle,
        company: job.company,
        description: job.description,
        applyLink: job.applyLink,
        experienceRequired: job.experienceRequired,
      });

      if (result.error) {
        pushToast({ tone: "danger", title: "Resume generation failed", description: result.error });
      } else if (result.pdfBase64) {
        // Download the PDF
        const blob = new Blob([Uint8Array.from(atob(result.pdfBase64), (c) => c.charCodeAt(0))], { type: "application/pdf" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `Resume_${job.company}_${job.jobTitle}.pdf`.replace(/[^a-zA-Z0-9_.\- ]/g, "_");
        link.click();
        URL.revokeObjectURL(url);
        pushToast({
          tone: "success",
          title: "Resume generated",
          description: `Tailored for ${job.jobTitle} at ${job.company} (${result.profile} profile)`,
        });
      } else {
        pushToast({
          tone: "warning",
          title: "LaTeX generated (no PDF)",
          description: `Install pdflatex to compile. File: ${result.texPath}`,
        });
      }
    } catch {
      pushToast({ tone: "danger", title: "Resume generation failed", description: "Network or server error" });
    } finally {
      setGeneratingResume(false);
    }
  }

  return (
    <AnimatePresence>
      {job && (
        <>
          <motion.button
            aria-label="Close job details"
            className="fixed inset-0 z-40 bg-slate-950/20"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => selectJob(undefined)}
          />
          <motion.aside
            className="fixed right-0 top-0 z-50 h-screen w-full max-w-xl overflow-y-auto border-l border-border bg-panel p-5 shadow-soft"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 240 }}
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge tone="accent">{job.source}</Badge>
                  <StatusBadge status={job.status} />
                  {job.duplicateScore ? <Badge tone="warning">Duplicate {job.duplicateScore}%</Badge> : null}
                </div>
                <h2 className="text-xl font-semibold tracking-normal">{job.jobTitle}</h2>
                <p className="text-sm text-muted">{job.company} · {job.location}</p>
              </div>
              <Button size="icon" variant="ghost" onClick={() => selectJob(undefined)} aria-label="Close">
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="mb-5 grid grid-cols-4 gap-2 rounded-md border border-border bg-background p-3 text-center">
              {Object.entries(job.scoreBreakdown).map(([key, value]) => (
                <div key={key}>
                  <div className="text-lg font-semibold">{value}</div>
                  <div className="text-[11px] capitalize text-muted">{key.replace(/([A-Z])/g, " $1")}</div>
                </div>
              ))}
            </div>

            <div className="mb-5 flex flex-wrap gap-2">
              <Button
                variant="primary"
                onClick={() => {
                  updateStatus(job.id, "APPLIED");
                  window.open(job.applyLink, "_blank", "noopener,noreferrer");
                }}
              >
                <ExternalLink className="h-4 w-4" />
                Direct Apply
              </Button>
              <Button onClick={handleGenerateResume} disabled={generatingResume}>
                <FileText className="h-4 w-4" />
                {generatingResume ? "Generating..." : "Generate Resume"}
              </Button>
              <select
                className="h-9 rounded-md border border-border bg-background px-3 text-sm"
                value={job.status}
                onChange={(event) => updateStatus(job.id, event.target.value as JobStatus)}
              >
                {statuses.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
              <Button onClick={() => updateStatus(job.id, "EXPIRED")}>
                <Undo2 className="h-4 w-4" />
                Ignore
              </Button>
              <Button variant="danger" onClick={() => deleteJob(job.id)}>
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            </div>

            <section className="space-y-5 text-sm">
              <Block title="GPT Summary">{job.gptSummary}</Block>
              <Block title="Match Reasoning">{job.gptReasoning}</Block>
              <Block title="Full Job Description">{job.description}</Block>
              <Block title="Company Information">{job.companyInfo}</Block>
              <div>
                <h3 className="mb-2 text-sm font-semibold">Required Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {job.requiredSkills.map((skill) => (
                    <Badge key={skill}>{skill}</Badge>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="mb-2 text-sm font-semibold">Recommended Resume</h3>
                <div className="rounded-md border border-border bg-background p-3">
                  <div className="text-sm font-semibold">{recommendedResume.file}</div>
                  <div className="mt-1 text-xs font-medium text-muted">{recommendedResume.role}</div>
                  <p className="mt-2 text-xs leading-5 text-muted">{recommendedResume.reason}</p>
                </div>
              </div>
              <div>
                <h3 className="mb-2 text-sm font-semibold">Benefits</h3>
                <ul className="list-inside list-disc space-y-1 text-muted">
                  {job.benefits.map((benefit) => (
                    <li key={benefit}>{benefit}</li>
                  ))}
                </ul>
              </div>
            </section>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <p className="leading-6 text-muted">{children}</p>
    </div>
  );
}
