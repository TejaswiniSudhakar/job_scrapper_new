import { NextRequest, NextResponse } from "next/server";
import { execSync } from "node:child_process";
import path from "node:path";
import { readFileSync, existsSync } from "node:fs";

const projectRoot = process.env.JOB_SCRAPER_DATA_DIR ?? process.cwd();

export async function POST(request: NextRequest) {
  try {
    const job = await request.json();

    if (!job.jobTitle && !job.description) {
      return NextResponse.json({ error: "Job data is required" }, { status: 400 });
    }

    // Write job data to a temp file for the Python script to read
    const tempFile = path.join(projectRoot, "generated_resumes", "_temp_job.json");
    const generatedDir = path.join(projectRoot, "generated_resumes");

    // Ensure directory exists
    if (!existsSync(generatedDir)) {
      const { mkdirSync } = await import("node:fs");
      mkdirSync(generatedDir, { recursive: true });
    }

    const { writeFileSync } = await import("node:fs");
    const jobPayload = {
      job_title: job.jobTitle ?? "",
      company_name: job.company ?? "",
      job_description: job.description ?? "",
      job_url: job.applyLink ?? "",
      experience_required: job.experienceRequired ?? "",
    };
    writeFileSync(tempFile, JSON.stringify(jobPayload), "utf-8");

    // Run the Python resume generator
    const scriptPath = path.join(projectRoot, "services", "resume_generator_cli.py");
    const result = execSync(
      `python "${scriptPath}" "${tempFile}"`,
      { cwd: projectRoot, timeout: 45000, encoding: "utf-8" }
    );

    const output = JSON.parse(result.trim());

    if (output.error) {
      return NextResponse.json({ error: output.error, texPath: output.tex_path }, { status: 500 });
    }

    // Read the generated PDF as base64 for download
    let pdfBase64: string | undefined;
    if (output.pdf_path && existsSync(output.pdf_path)) {
      const pdfBuffer = readFileSync(output.pdf_path);
      pdfBase64 = pdfBuffer.toString("base64");
    }

    return NextResponse.json({
      pdfPath: output.pdf_path,
      texPath: output.tex_path,
      profile: output.profile,
      matchedSkills: output.matched_skills,
      pdfBase64,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Resume generation failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
