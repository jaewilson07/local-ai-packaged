/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'immich-server',
        port: '2283',
        pathname: '/api/**',
      },
    ],
    unoptimized: true, // Required for Docker deployment
  },
}

module.exports = nextConfig
