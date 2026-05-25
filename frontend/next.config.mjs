/** @type {import('next').NextConfig} */
const rawApiProxyTarget =
  process.env.API_PROXY_TARGET ??
  process.env.NEXT_PUBLIC_API_PROXY_TARGET ??
  "https://abbot-study-api-staging.onrender.com";
const normalizedApiProxyTarget = rawApiProxyTarget.replace(/\/+$/, "").replace(/\/api$/, "");
const frontendHosts = new Set([
  "abbot-study-staging.onrender.com",
  process.env.RENDER_EXTERNAL_HOSTNAME,
].filter(Boolean));

function resolveApiProxyTarget(target) {
  try {
    const parsedTarget = new URL(target);
    if (frontendHosts.has(parsedTarget.hostname)) {
      return "https://abbot-study-api-staging.onrender.com";
    }
  } catch {
    return "https://abbot-study-api-staging.onrender.com";
  }

  return target;
}

const apiProxyTarget = resolveApiProxyTarget(normalizedApiProxyTarget);

const nextConfig = {
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget}/api/:path*`
      }
    ];
  },
  async headers() {
    return [
      {
        source: "/:path(dashboard|subjects|learn|settings|command-center)(.*)",
        headers: [
          {
            key: "Cache-Control",
            value: "no-store, no-cache, must-revalidate, private, max-age=0"
          },
          {
            key: "Pragma",
            value: "no-cache"
          },
          {
            key: "Expires",
            value: "0"
          }
        ]
      }
    ];
  }
};

export default nextConfig;
