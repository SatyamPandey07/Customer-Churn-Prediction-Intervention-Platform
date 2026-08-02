/** @type {import('next').NextConfig} */
import { withSentryConfig } from '@sentry/nextjs';

const nextConfig = {};
export default withSentryConfig(nextConfig, {
  silent: true,
  org: "churn-platform",
  project: "frontend",
});
