import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const projectRoot = process.cwd();
const args = process.argv.slice(2);
const env = { ...process.env };

while (args[0] === "--env") {
  const pair = args[1];
  if (!pair || !pair.includes("=")) {
    console.error("Expected KEY=VALUE after --env");
    process.exit(1);
  }

  const [key, ...valueParts] = pair.split("=");
  env[key] = valueParts.join("=");
  args.splice(0, 2);
}

if (!args.length) {
  console.error("No Python command was provided.");
  process.exit(1);
}

const pythonCandidates = [
  path.join(projectRoot, ".venv", "Scripts", "python.exe"),
  path.join(projectRoot, ".venv", "bin", "python3"),
  path.join(projectRoot, ".venv", "bin", "python"),
  process.env.PYTHON,
  "python"
].filter(Boolean);

const pythonCommand =
  pythonCandidates.find((candidate) => candidate && fs.existsSync(candidate)) ?? pythonCandidates.at(-1);

const child = spawn(pythonCommand, args, {
  stdio: "inherit",
  env,
  shell: false
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 1);
});

child.on("error", (error) => {
  console.error(`Failed to start Python command: ${error.message}`);
  process.exit(1);
});
