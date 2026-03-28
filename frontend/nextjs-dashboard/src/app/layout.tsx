import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CareBridge Dashboard",
  description: "Multi-agent healthcare follow-up system",
};

const navItems = [
  { href: "/", label: "Patients", icon: "👥" },
  { href: "/alerts", label: "Alerts", icon: "🔔" },
  { href: "/appointments", label: "Appointments", icon: "📅" },
  { href: "/timeline", label: "Timeline", icon: "📊" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-zinc-950 text-zinc-100 min-h-screen`}>
        <div className="flex min-h-screen">
          <aside className="w-64 border-r border-zinc-800 bg-zinc-900 p-6 flex flex-col gap-2">
            <Link href="/" className="text-xl font-bold text-white mb-8 block">
              CareBridge
            </Link>
            <nav className="flex flex-col gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
                >
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              ))}
            </nav>
          </aside>
          <main className="flex-1 p-8 overflow-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
