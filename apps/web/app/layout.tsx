import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";

import { TenantBrandingProvider } from "@/components/TenantBrandingProvider";

export const metadata = {
  title: "Churn Intervention Platform",
  description: "Predict churn risk, generate SHAP explanations, & automate targeted retention campaigns.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <TenantBrandingProvider>
          <ThemeProvider>
            {children}
          </ThemeProvider>
        </TenantBrandingProvider>
      </body>
    </html>
  );
}
