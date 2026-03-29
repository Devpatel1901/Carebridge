import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { DashboardShell } from "@/components/carebridge/dashboard-shell";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CareBridge Dashboard",
  description: "Multi-agent healthcare follow-up system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen antialiased`}>
        <DashboardShell>{children}</DashboardShell>
      </body>
    </html>
  );
}
