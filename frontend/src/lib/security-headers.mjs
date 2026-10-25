const DEFAULT_API_BASE_URL = "http://localhost:8000";

/** @param {string | undefined} apiBaseUrl */
export function resolveApiOrigin(apiBaseUrl) {
  try {
    return new URL(apiBaseUrl || DEFAULT_API_BASE_URL).origin;
  } catch {
    throw new Error(`NEXT_PUBLIC_API_BASE_URL must be a valid URL, got '${apiBaseUrl}'`);
  }
}

/** @param {{ isDev: boolean, apiBaseUrl?: string }} options */
export function buildSecurityHeaders({ isDev, apiBaseUrl }) {
  const apiOrigin = resolveApiOrigin(apiBaseUrl);
  const scriptSrc = ["'self'", "'unsafe-inline'", ...(isDev ? ["'unsafe-eval'"] : [])];
  const connectSrc = ["'self'", apiOrigin, ...(isDev ? ["ws:"] : [])];
  const csp = [
    "default-src 'self'",
    `script-src ${scriptSrc.join(" ")}`,
    "style-src 'self' 'unsafe-inline'",
    `img-src 'self' data: blob: ${apiOrigin}`,
    `connect-src ${connectSrc.join(" ")}`,
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self'",
  ].join("; ");

  return [
    { key: "Content-Security-Policy", value: csp },
    { key: "Strict-Transport-Security", value: "max-age=31536000" },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  ];
}
