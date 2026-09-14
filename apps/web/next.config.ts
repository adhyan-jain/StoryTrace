import type { NextConfig } from "next";

// Baked in at build time (see apps/web/Dockerfile) -- the browser's own
// connect-src target, not the in-network "backend" service name.
const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Auth tokens live in localStorage (see src/lib/auth.tsx), a deliberate
// tradeoff to avoid a cookie-based CSRF surface -- but that means an XSS
// bug here is a direct token-theft path with no other mitigation. CSP is
// the actual backstop: it blocks the exfiltration/script-injection vectors
// an XSS would otherwise rely on.
const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  `connect-src 'self' ${apiUrl}`,
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image to just the traced
  // server bundle + node_modules subset, instead of the whole workspace.
  output: "standalone",
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
        ],
      },
    ];
  },
};

export default nextConfig;
