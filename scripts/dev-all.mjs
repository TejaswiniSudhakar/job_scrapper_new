import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  ".."
);

const env = {
  ...process.env,
  JOB_SCRAPER_DATA_DIR: root,
};

const scraper = spawn("python3", ["main.py"], {
  cwd: root,
  env,
  stdio: "inherit",
});

const frontend = spawn("npx", ["next", "dev"], {
  cwd: root,
  env,
  stdio: "inherit",
  shell: true,
});

scraper.on("exit", (code) => {
  console.log(`Scraper exited with code ${code}`);
});

frontend.on("exit", (code) => {
  console.log(`Frontend exited with code ${code}`);
});

process.on("SIGINT", () => {
  scraper.kill();
  frontend.kill();
  process.exit();
});