import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Permite servir el dev server también por 127.0.0.1, no solo localhost.
  allowedDevOrigins: ["127.0.0.1", "localhost"],

  async headers() {
    return [
      {
        // Cabeceras de seguridad HTTP en todas las rutas. HSTS no hace
        // falta acá: Vercel ya lo agrega automáticamente en producción.
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
