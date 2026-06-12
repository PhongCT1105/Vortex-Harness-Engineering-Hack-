import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/run", destination: "http://localhost:8000/run" },
      { source: "/approve", destination: "http://localhost:8000/approve" },
      { source: "/chat", destination: "http://localhost:8000/chat" },
      { source: "/events", destination: "http://localhost:8000/events" },
      { source: "/config", destination: "http://localhost:8000/config" },
      { source: "/health", destination: "http://localhost:8000/health" },
      { source: "/supply-chain", destination: "http://localhost:8000/supply-chain" },
      { source: "/supply-chain/:path*", destination: "http://localhost:8000/supply-chain/:path*" },
    ];
  },
};

export default nextConfig;
