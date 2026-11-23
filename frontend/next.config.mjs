/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // proxy.ts forwards worksheet uploads (up to 10 MB plus form overhead) to the backend.
    // Next's default limit is exactly 10 MB, which would cut off the largest allowed files.
    proxyClientMaxBodySize: "11mb",
    // Allow for a sleeping free-tier backend to wake up (about a minute) before giving up.
    proxyTimeout: 120_000,
  },
};

export default nextConfig;
