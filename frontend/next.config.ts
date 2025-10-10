import type { NextConfig } from "next";

// Bundle analyzer for production build analysis
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

const nextConfig: NextConfig = {
  // Material-UI tree-shaking and optimization
  modularizeImports: {
    '@mui/material': {
      transform: '@mui/material/{{member}}',
    },
    '@mui/icons-material': {
      transform: '@mui/icons-material/{{member}}',
    },
  },
  
  // Emotion compiler optimizations
  compiler: {
    emotion: {
      sourceMap: false,
      autoLabel: 'never',
    },
    removeConsole: process.env.NODE_ENV === 'production',
  },
  
  // Optimize package imports for better tree-shaking
  experimental: {
    optimizePackageImports: ['@mui/material', '@mui/icons-material', 'lucide-react'],
  },
  
  // Production optimizations
  swcMinify: true,
  reactStrictMode: true,
  poweredByHeader: false,
  
  // Image optimization
  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 31536000,
  },
};

export default withBundleAnalyzer(nextConfig);
