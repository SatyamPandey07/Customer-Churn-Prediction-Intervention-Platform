import "./globals.css";

export const metadata = {
  title: "Churn Prediction Platform",
  description: "Dashboard for churn intervention",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
