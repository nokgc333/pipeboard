import { buildSecurityHeaders } from "./src/lib/security-headers.mjs";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: buildSecurityHeaders({
          isDev: process.env.NODE_ENV !== "production",
          apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
        }),
      },
    ];
  },
};

export default nextConfig;
