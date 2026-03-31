/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  // Rewrites are ignored for `output: "export"`. For local dev, set
  // NEXT_PUBLIC_API_BASE=http://127.0.0.1:8080 while the API runs on 8080.
};

export default nextConfig;
