import { existsSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const nextDir = path.join(appRoot, ".next");

if (existsSync(nextDir)) {
  rmSync(nextDir, {
    recursive: true,
    force: true,
    maxRetries: 10,
    retryDelay: 200
  });
  console.log(`Removed ${nextDir}`);
} else {
  console.log(`No .next directory to remove at ${nextDir}`);
}
