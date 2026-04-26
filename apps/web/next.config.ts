import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const appRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  experimental: {
    typedRoutes: true
  },
  outputFileTracingRoot: appRoot
};

export default nextConfig;
