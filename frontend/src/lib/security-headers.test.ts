import { describe, expect, it } from "vitest";
import { buildSecurityHeaders, resolveApiOrigin } from "./security-headers.mjs";

function headerMap(options: { isDev: boolean; apiBaseUrl?: string }): Record<string, string> {
  return Object.fromEntries(
    buildSecurityHeaders(options).map(({ key, value }: { key: string; value: string }) => [
      key,
      value,
    ]),
  );
}

describe("resolveApiOrigin", () => {
  it("reduces a base URL to its origin", () => {
    expect(resolveApiOrigin("https://api.example.com/v1/")).toBe("https://api.example.com");
  });

  it("falls back to the local backend when the value is missing", () => {
    expect(resolveApiOrigin(undefined)).toBe("http://localhost:8000");
  });

  it("rejects a value that is not a URL", () => {
    expect(() => resolveApiOrigin("not a url")).toThrow(/NEXT_PUBLIC_API_BASE_URL/);
  });
});

describe("buildSecurityHeaders", () => {
  it("sets the baseline hardening headers", () => {
    const headers = headerMap({ isDev: false });

    expect(headers["X-Content-Type-Options"]).toBe("nosniff");
    expect(headers["X-Frame-Options"]).toBe("DENY");
    expect(headers["Referrer-Policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["Permissions-Policy"]).toBe("camera=(), microphone=(), geolocation=()");
  });

  it("sets HSTS without includeSubDomains", () => {
    const value = headerMap({ isDev: false })["Strict-Transport-Security"];

    expect(value).toBe("max-age=31536000");
  });

  it("restricts the CSP to self plus the API origin in production", () => {
    const csp = headerMap({ isDev: false, apiBaseUrl: "https://api.example.com" })[
      "Content-Security-Policy"
    ];

    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("connect-src 'self' https://api.example.com");
    expect(csp).toContain("img-src 'self' data: blob: https://api.example.com");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("base-uri 'self'");
    expect(csp).not.toContain("unsafe-eval");
  });

  it("allows eval and websockets only in development", () => {
    const csp = headerMap({ isDev: true })["Content-Security-Policy"];

    expect(csp).toContain("'unsafe-eval'");
    expect(csp).toContain("ws:");
  });
});
