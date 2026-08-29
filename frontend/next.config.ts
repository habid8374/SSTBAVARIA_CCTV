import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Permite servir el dev server también por 127.0.0.1, no solo localhost.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
