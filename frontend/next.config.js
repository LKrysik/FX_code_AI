/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  webpack: (config, { dev }) => {
    if (dev) {
      // Avoid eval-based devtool to comply with strict CSP
      config.devtool = 'cheap-module-source-map';
      
      // Reduce dev CPU by ignoring heavy folders in watcher
      config.watchOptions = {
        ...(config.watchOptions || {}),
        ignored: [
          '**/data/**',
          '**/backtest/**',
          '**/backtest_results/**',
          '**/logs/**',
          '**/.venv/**',
          '**/tests/**',
          '**/config/**',
          '**/__pycache__/**',
        ],
      };
    }
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8080/api/:path*', // FastAPI backend
      },
    ]
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: process.env.NODE_ENV === 'development'
              ? "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' ws: wss: http: https:; frame-src 'none';"
              : "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' ws: wss: http: https:; frame-src 'none';",
          },
        ],
      },
    ]
  },
}

module.exports = nextConfig
