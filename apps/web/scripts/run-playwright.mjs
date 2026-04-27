import { spawn } from "node:child_process";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import process from "node:process";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(scriptDir, "..");
const playwrightCliCandidates = [
  path.join(webRoot, "node_modules", "@playwright", "test", "cli.js"),
  path.join(webRoot, "..", "..", "node_modules", "@playwright", "test", "cli.js")
];
const playwrightCli = playwrightCliCandidates.find((candidate) => fs.existsSync(candidate));
const nextCliCandidates = [
  path.join(webRoot, "node_modules", "next", "dist", "bin", "next"),
  path.join(webRoot, "..", "..", "node_modules", "next", "dist", "bin", "next")
];
const nextCli = nextCliCandidates.find((candidate) => fs.existsSync(candidate));
const args = process.argv.slice(2);

if (!playwrightCli) {
  console.error("Could not find the Playwright CLI in the workspace.");
  process.exit(1);
}

if (!nextCli) {
  console.error("Could not find the Next.js CLI in the workspace.");
  process.exit(1);
}

function spawnProcess(commandArgs, env = process.env) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, commandArgs, {
      cwd: webRoot,
      stdio: "inherit",
      env
    });

    child.on("exit", (code, signal) => {
      if (signal) {
        process.kill(process.pid, signal);
        return;
      }

      resolve(code ?? 1);
    });

    child.on("error", reject);
  });
}

const productionBuildIdPath = path.join(webRoot, ".next", "BUILD_ID");

if (!fs.existsSync(productionBuildIdPath)) {
  const buildExitCode = await spawnProcess([nextCli, "build"]);
  if (buildExitCode !== 0) {
    process.exit(buildExitCode);
  }
}

try {
  const exitCode = await spawnProcess([playwrightCli, "test", ...args], {
    ...process.env,
    PLAYWRIGHT_SERVER_MODE: "production"
  });
  process.exit(exitCode);
} catch (error) {
  console.error(`Failed to start Playwright: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
