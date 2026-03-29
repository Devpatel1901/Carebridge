"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

/** Demo census — limited to 5 rows (Figma) to avoid table/page scrollbars; phones kept for discharge intake. */
export const staticPatients = [
  { id: "1024587", name: "Sarah Chen", age: 42, gender: "F", phone: "+15551024587", email: "sarah.chen@demo.com", reason: "Head Trauma", status: "High Risk", ward: "ICU-3" },
  { id: "7658321", name: "Omar Farooq", age: 40, gender: "M", phone: "+15557658321", reason: "Heart Failure", status: "Discharged", ward: "R-18" },
  { id: "2156793", name: "David Lee", age: 67, gender: "M", phone: "+15552156793", email: "d.lee@demo.com", reason: "Pneumonia", status: "Recovering", ward: "G-12" },
  { id: "3298461", name: "Ayesha Begum", age: 87, gender: "F", phone: "+15553298461", reason: "Post-Op Recovery", status: "Stable", ward: "R-14" },
  { id: "4532109", name: "Habib Chowdhury", age: 28, gender: "M", phone: "+15554532109", reason: "Post-Op Recovery", status: "Stable", ward: "ICU-9" },
];

/** Figma filter chips (screenshot 1). */
const filters = ["All", "Recovery", "High Risk", "Stable", "Discharged"] as const;

export const statusColors: Record<string, { bg: string; text: string }> = {
  "High Risk": { bg: "#fce4e4", text: "#c0392b" },
  Discharged: { bg: "#fdebd0", text: "#b8860b" },
  Recovering: { bg: "#dbe8fd", text: "#1a4fd6" },
  Stable: { bg: "#d5f5e3", text: "#27ae60" },
  Admitted: { bg: "#e3f2fd", text: "#1565c0" },
};

const inHospital = (s: string) =>
  ["Admitted", "High Risk", "Recovering", "Stable"].includes(s);

/** Figma dashboard home (screenshot): fixed headline numbers. */
export function getFigmaHomeStats() {
  return [
    { label: "Total Patients", value: 8 },
    { label: "Emergency", value: 1 },
    { label: "Recovery", value: 1 },
    { label: "High-Risk", value: 2 },
  ] as const;
}

export function getDashboardStats() {
  const rows = staticPatients;
  const admittedLike = rows.filter((p) => inHospital(p.status)).length;
  const highRisk = rows.filter((p) => p.status === "High Risk").length;
  const recovery = rows.filter((p) => p.status === "Recovering").length;
  return [
    { label: "Total Patients", value: rows.length },
    { label: "Admitted / In-house", value: admittedLike },
    { label: "In Recovery", value: recovery },
    { label: "High-Risk", value: highRisk },
  ] as const;
}

export function PatientManagementHeader() {
  return (
    <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-xl font-bold leading-tight text-[#1a1a1a] sm:text-[22px]">Patient Management</h1>
        <p className="mt-1 text-[13px] text-[#888] sm:text-[13.5px]">
          Manage, monitor, and review patients
        </p>
      </div>
      <button
        type="button"
        className="inline-flex shrink-0 items-center justify-center gap-2 rounded-[10px] bg-[#2d6a2e] px-5 py-2.5 text-sm font-medium text-white transition-colors duration-200 hover:bg-[#245a25]"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        Add Patient
      </button>
    </div>
  );
}

export function PatientStatCards({ variant = "default" }: { variant?: "default" | "figma" }) {
  const stats = variant === "figma" ? getFigmaHomeStats() : getDashboardStats();
  return (
    <div className="mb-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-xl border border-[#e8e8e8] bg-white px-4 py-4 shadow-sm transition-shadow hover:shadow-md sm:px-[22px] sm:py-[18px]"
        >
          <div className="mb-1.5 text-xs font-semibold text-[#777] sm:text-[13px]">{stat.label}</div>
          <div className="text-2xl font-bold leading-none text-[#1a1a1a] sm:text-[32px]">{stat.value}</div>
        </div>
      ))}
    </div>
  );
}

type PatientStaticTableCardProps = {
  /** Highlights the row when viewing this patient in the app (route id). */
  highlightPatientId?: string;
};

export function PatientStaticTableCard({ highlightPatientId }: PatientStaticTableCardProps) {
  const [activeFilter, setActiveFilter] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredPatients = useMemo(() => {
    return staticPatients.filter((p) => {
      const matchesFilter =
        activeFilter === "All" ||
        p.status === activeFilter ||
        (activeFilter === "Recovery" && p.status === "Recovering");
      const matchesSearch =
        searchQuery === "" ||
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.id.includes(searchQuery) ||
        p.reason.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
    });
  }, [activeFilter, searchQuery]);

  return (
    <div className="overflow-hidden rounded-xl border border-[#e8e8e8] bg-white shadow-sm sm:rounded-[14px]">
      <div className="px-4 pb-3.5 pt-4 sm:px-[22px] sm:pt-[18px]">
        <div className="relative">
          <svg
            className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#999]"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, ID, or condition..."
            className="w-full rounded-[10px] border border-[#e0e0e0] bg-[#fafafa] py-2.5 pl-10 pr-3.5 text-[13px] text-[#555] outline-none transition-shadow placeholder:text-[#999] focus:border-[#2d6a2e] focus:ring-2 focus:ring-[#2d6a2e]/20 sm:text-[13.5px]"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 px-4 pb-3.5 sm:px-[22px]">
        {filters.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setActiveFilter(f)}
            className={`rounded-full px-3 py-1.5 text-xs transition-colors duration-200 sm:px-4 sm:text-[13px] ${
              activeFilter === f
                ? "bg-[#2d6a2e] font-medium text-white"
                : "border border-[#ddd] bg-white font-normal text-[#555] hover:border-[#ccc]"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="-mx-0 overflow-x-auto">
        <div className="inline-block min-w-full align-middle">
          <table className="min-w-[720px] w-full border-collapse">
            <thead>
              <tr className="border-t border-[#eee]">
                {["Patient ID", "Patient Name", "Reason", "Status", "Ward / Bed", "Action"].map((h) => (
                  <th
                    key={h}
                    className="whitespace-nowrap border-b border-[#eee] px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wide text-[#888] sm:px-[22px] sm:text-[12.5px] sm:normal-case sm:tracking-normal"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredPatients.map((p) => {
                const isCurrent = highlightPatientId && p.id === highlightPatientId;
                return (
                  <tr
                    key={p.id}
                    className={`border-b border-[#f0f0f0] transition-colors duration-150 hover:bg-[#fafafa] ${
                      isCurrent ? "bg-[#e8f5e9]/80" : ""
                    }`}
                  >
                    <td className="whitespace-nowrap px-4 py-4 text-[13.5px] text-[#555] sm:px-[22px]">
                      {p.id}
                    </td>
                    <td className="min-w-[140px] px-4 py-4 sm:px-[22px]">
                      <div className="text-sm font-semibold text-[#1a1a1a]">{p.name}</div>
                      <div className="mt-0.5 text-[12.5px] text-[#999]">
                        {p.age}y · {p.gender}
                      </div>
                    </td>
                    <td className="max-w-[220px] px-4 py-4 text-[13.5px] text-[#555] sm:px-[22px]">
                      <span className="line-clamp-2">{p.reason}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-4 sm:px-[22px]">
                      <span
                        className="inline-block rounded-full px-3.5 py-1 text-[12.5px] font-medium"
                        style={{
                          background: statusColors[p.status]?.bg ?? "#eee",
                          color: statusColors[p.status]?.text ?? "#555",
                        }}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-4 text-[13.5px] text-[#555] sm:px-[22px]">
                      {p.ward}
                    </td>
                    <td className="whitespace-nowrap px-4 py-4 sm:px-[22px]">
                      <Link
                        href={`/patients/${p.id}`}
                        className="inline-flex rounded-lg border border-[#2d6a2e]/50 bg-[#e8f5e9] px-[18px] py-[7px] text-[13px] font-semibold text-[#2d6a2e] transition-colors duration-200 hover:bg-[#d4ecd6]"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
