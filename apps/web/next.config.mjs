/** @type {import('next').NextConfig} */
import { withSentryConfig } from '@sentry/nextjs';

const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default withSentryConfig(nextConfig, {
  silent: true,
  org: "churn-platform",
  project: "frontend",
});
