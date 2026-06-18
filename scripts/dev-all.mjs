import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pythonCandidates = [
  "C:\\Users\\Nishant Chandraker\\Downloads\\private-job-scraper-main\\.venv\\Scripts\\python.exe",
  path.resolve(root, "..", "..", "work", ".venv", "Scripts", "python.exe")
];
const python = pythonCandidates.find((candidate) => existsSync(candidate));
const nextBin = path.resolve(root, "node_modules", "next", "dist", "bin", "next");

if (!python) {
  console.error("[dev:all] Python venv not found. Expected one of:");
  for (const candidate of pythonCandidates) console.error(`  - ${candidate}`);
  process.exit(1);
}

if (!existsSync(nextBin)) {
  console.error("[dev:all] Next.js is not installed. Run npm install first.");
  process.exit(1);
}

const env = {
  ...process.env,
  JOB_SCRAPER_DATA_DIR: root
};

const processes = [
  {
    name: "scraper",
    child: spawn(python, ["main.py"], {
      cwd: root,
      env,
      stdio: "inherit"
    })
  },
  {
    name: "frontend",
    child: spawn(process.execPath, [nextBin, "dev"], {
      cwd: root,
      env,
      stdio: "inherit"
    })
  }
];

let shuttingDown = false;

console.log("[dev:all] Started scraper and frontend.");
console.log("[dev:all] Open http://localhost:3000");
console.log("[dev:all] Press Ctrl+C once to stop both.");

for (const processInfo of processes) {
  processInfo.child.on("exit", (code, signal) => {
    if (shuttingDown) return;

    shuttingDown = true;
    console.log(`[dev:all] ${processInfo.name} exited. Stopping the other process...`);
    stopChildren(signal ?? "SIGINT");
    process.exit(code ?? 0);
  });
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

if (process.platform === "win32") {
  process.on("SIGBREAK", () => shutdown("SIGBREAK"));
}

function shutdown(signal) {
  if (shuttingDown) {
    process.exit(signal === "SIGINT" ? 130 : 0);
  }

  shuttingDown = true;
  console.log(`\n[dev:all] Shutdown requested. Stopping scraper and frontend...`);
  stopChildren(signal);

  setTimeout(() => {
    process.exit(signal === "SIGINT" ? 130 : 0);
  }, 5000).unref();
}

function stopChildren(signal) {
  for (const { child } of processes) {
    if (!child.killed && child.exitCode === null) {
      child.kill(signal);
    }
  }
}
