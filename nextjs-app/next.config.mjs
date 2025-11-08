/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ['@prisma/client'],
  },
  images: {
    domains: ['pub-yourcloudflare.r2.dev'],
  },
};

export default nextConfig;
