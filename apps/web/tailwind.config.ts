import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        tenant: {
          primary: "var(--tenant-primary, #2563eb)", // default blue-600
          secondary: "var(--tenant-secondary, #1e40af)" // default blue-800
        }
      },
    },
  },
  plugins: [],
};
export default config;
