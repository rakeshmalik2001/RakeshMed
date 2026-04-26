import { execSync, spawn } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const nextDir = path.join(appRoot, ".next");
const nextBin = path.join(appRoot, "..", "..", "node_modules", "next", "dist", "bin", "next");

function parsePort(argv) {
  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index];

    if ((current === "--port" || current === "-p") && argv[index + 1]) {
      const parsed = Number.parseInt(argv[index + 1], 10);
      if (!Number.isNaN(parsed)) {
        return parsed;
      }
    }

    if (current.startsWith("--port=")) {
      const parsed = Number.parseInt(current.slice("--port=".length), 10);
      if (!Number.isNaN(parsed)) {
        return parsed;
      }
    }
  }

  return 3000;
}

function cleanNextDirectory() {
  if (!existsSync(nextDir)) {
    return;
  }

  rmSync(nextDir, {
    recursive: true,
    force: true,
    maxRetries: 10,
    retryDelay: 200
  });
  console.log(`Removed ${nextDir}`);
}

function stopWindowsPortListener(port) {
  if (process.platform !== "win32") {
    return;
  }

  try {
    const output = execSync(
      `powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort ${port} -State Listen | Select-Object -ExpandProperty OwningProcess"`,
      {
        cwd: appRoot,
        stdio: ["ignore", "pipe", "ignore"]
      }
    )
      .toString()
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

    const pids = [...new Set(output)];

    for (const pid of pids) {
      execSync(`taskkill /PID ${pid} /F`, {
        cwd: appRoot,
        stdio: ["ignore", "ignore", "ignore"]
      });
      console.log(`Stopped process ${pid} using port ${port}`);
    }
  } catch {
    // If nothing is listening or the command is unavailable, continue normally.
  }
}

const args = process.argv.slice(2);
const port = parsePort(args);

stopWindowsPortListener(port);
cleanNextDirectory();

const child = spawn(process.execPath, [nextBin, "dev", ...args], {
  cwd: appRoot,
  env: process.env,
  stdio: "inherit"
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});
