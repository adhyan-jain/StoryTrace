import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image to just the traced
  // server bundle + node_modules subset, instead of the whole workspace.
  output: "standalone",
};

export default nextConfig;
