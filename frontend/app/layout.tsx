import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AlphaOption | Paper Research",
  description: "Local paper-only Nifty option research platform",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
