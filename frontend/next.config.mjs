/** @type {import('next').NextConfig} */
const apiProxyTarget =
  process.env.API_PROXY_TARGET ??
  process.env.NEXT_PUBLIC_API_PROXY_TARGET ??
  "https://abbot-study-api-staging.onrender.com";

const nextConfig = {
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
