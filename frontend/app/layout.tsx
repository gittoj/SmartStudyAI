import type { ReactNode } from "react";
import { Analytics } from "@vercel/analytics/next";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

export const metadata = { title: "SmartStudy AI" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SiteHeader />
        {children}
        {/* Vercel Web Analytics: cookieless page views only. Never add custom events that carry
            worksheet text, child names or answers (see spec.md, Libraries). */}
        <Analytics />
      </body>
    </html>
  );
}
