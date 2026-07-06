/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts"],
  },
  transpilePackages: ["@ag-grid-community/react"],
};

module.exports = nextConfig;