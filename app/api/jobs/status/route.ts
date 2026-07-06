import { NextRequest, NextResponse } from "next/server";
import Database from "better-sqlite3";
import path from "node:path";

const dbPath = path.join(process.env.JOB_SCRAPER_DATA_DIR ?? process.cwd(), "jobs.db");

export async function PATCH(request: NextRequest) {
  try {
    const { jobId, status } = (await request.json()) as { jobId: string; status: string };

    if (!jobId || !status) {
      return NextResponse.json({ error: "jobId and status are required" }, { status: 400 });
    }

    const db = new Database(dbPath);
    ensureColumns(db);

    const result = runStatusUpdate(db, jobId, status);
    db.close();

    if (result.changes === 0) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    return NextResponse.json({ jobId, status, appliedAt: status === "APPLIED" ? new Date().toISOString() : undefined });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to update status" },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { jobId } = (await request.json()) as { jobId: string };

    if (!jobId) {
      return NextResponse.json({ error: "jobId is required" }, { status: 400 });
    }

    const db = new Database(dbPath);
    ensureColumns(db);

    const result = runStatusUpdate(db, jobId, "DELETED");
    db.close();

    if (result.changes === 0) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    return NextResponse.json({ jobId, deleted: true });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to delete job" },
      { status: 500 }
    );
  }
}

function ensureColumns(db: InstanceType<typeof Database>) {
  const columns = db.pragma("table_info(jobs)") as { name: string }[];
  const names = new Set(columns.map((c) => c.name));
  if (!names.has("status")) db.exec("ALTER TABLE jobs ADD COLUMN status TEXT");
  if (!names.has("applied_at")) db.exec("ALTER TABLE jobs ADD COLUMN applied_at TEXT");
}

function runStatusUpdate(db: InstanceType<typeof Database>, jobId: string, status: string) {
  const numericId = jobId.startsWith("job_") ? jobId.slice(4) : undefined;
  const urlHash = jobId.startsWith("job_") ? undefined : jobId;

  if (status === "APPLIED") {
    const appliedAt = new Date().toISOString();
    if (numericId) {
      return db.prepare("UPDATE jobs SET status = ?, applied_at = ? WHERE id = ?").run(status, appliedAt, numericId);
    }
    return db.prepare("UPDATE jobs SET status = ?, applied_at = ? WHERE url_hash = ?").run(status, appliedAt, urlHash);
  }

  if (numericId) {
    return db.prepare("UPDATE jobs SET status = ? WHERE id = ?").run(status, numericId);
  }
  return db.prepare("UPDATE jobs SET status = ? WHERE url_hash = ?").run(status, urlHash);
}
