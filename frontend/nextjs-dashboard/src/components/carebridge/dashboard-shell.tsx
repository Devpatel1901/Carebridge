"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  NavIconAppointments,
  NavIconMessages,
  NavIconOverview,
  NavIconPatients,
  NavIconReports,
  NavIconStaff,
} from "./nav-icons";

const topNav: {
  id: string;
  label: string;
  href: string;
  Icon: typeof NavIconOverview;
  match: (path: string) => boolean;
}[] = [
  { id: "overview", label: "Overview", href: "/", Icon: NavIconOverview, match: () => false },
  { id: "patients", label: "Patients", href: "/", Icon: NavIconPatients, match: (p) => p === "/" || p.startsWith("/patients") },
  {
    id: "appointments",
    label: "Appointments",
    href: "/appointments",
    Icon: NavIconAppointments,
    match: (p) => p.startsWith("/appointments"),
  },
  { id: "reports", label: "Reports", href: "/timeline", Icon: NavIconReports, match: (p) => p.startsWith("/timeline") },
  { id: "messages", label: "Messages", href: "#", Icon: NavIconMessages, match: () => false },
  { id: "staff", label: "Staff Members", href: "#", Icon: NavIconStaff, match: () => false },
];

const bottomNav = ["Settings", "Help / Support", "Logout"] as const;

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-[#f8f9fa] text-[#1a1a1a] antialiased">
      <aside className="flex w-[185px] shrink-0 flex-col justify-between border-r border-[#e8e8e8] bg-white">
        <div>
          <Link href="/" className="flex items-center gap-2.5 px-5 py-[18px]">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#2d6a2e]">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <span className="text-base font-bold text-[#1a1a1a]">CareBridge</span>
          </Link>

          <nav className="mt-2 px-2.5">
            {topNav.map((item) => {
              const active = item.match(pathname);
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  className={cn(
                    "mb-0.5 flex cursor-pointer items-center gap-3 rounded-[10px] px-4 py-[11px] text-[13.5px] transition-colors duration-150",
                    active
                      ? "bg-[#2d6a2e] font-semibold text-white"
                      : "font-normal text-[#555] hover:bg-[#f5f5f5]"
                  )}
                >
                  <item.Icon active={active} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="px-2.5 pb-5 pt-0">
          {bottomNav.map((item) => (
            <button
              key={item}
              type="button"
              className="mb-px flex w-full cursor-pointer items-center gap-3 rounded-[10px] px-4 py-2.5 text-left text-[13.5px] text-[#555] transition-colors hover:bg-[#f5f5f5]"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="1.8">
                {item === "Settings" && (
                  <>
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
                  </>
                )}
                {item === "Help / Support" && (
                  <>
                    <circle cx="12" cy="12" r="10" />
                    <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </>
                )}
                {item === "Logout" && (
                  <>
                    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </>
                )}
              </svg>
              <span>{item}</span>
            </button>
          ))}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[52px] shrink-0 items-center justify-between border-b border-[#e8e8e8] bg-white px-7">
          <div className="relative w-[360px] max-w-full">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#999]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="search"
              placeholder="Search patients, staff, or inventory..."
              readOnly
              className="w-full rounded-[10px] border border-[#e0e0e0] bg-[#fafafa] py-[9px] pl-[38px] pr-3 text-[13.5px] text-[#888] outline-none transition-shadow placeholder:text-[#888] focus:border-[#2d6a2e] focus:ring-2 focus:ring-[#2d6a2e]/20"
            />
          </div>
          <div className="flex items-center gap-[18px]">
            <button
              type="button"
              className="relative text-[#555] transition-opacity hover:opacity-80"
              aria-label="Notifications"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 01-3.46 0" />
              </svg>
              <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full border-2 border-white bg-[#e74c3c]" />
            </button>
            <button type="button" className="text-[#555] transition-opacity hover:opacity-80" aria-label="Messages">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
              </svg>
            </button>
            <div className="ml-1 flex items-center gap-2">
              <div
                className="h-9 w-9 shrink-0 rounded-full border-2 border-[#e0d9c8] bg-gradient-to-br from-[#8B7355] to-[#A0926B]"
                aria-hidden
              />
              <span className="text-sm font-medium text-[#333]">Dr. Sarah</span>
            </div>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 flex-col overflow-auto">{children}</div>
      </div>
    </div>
  );
}
