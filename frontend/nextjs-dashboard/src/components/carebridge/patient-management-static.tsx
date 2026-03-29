"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

/** Demo census list — mix of admitted, ICU, recovering, stable, and discharged (Figma-style palette). */
export const staticPatients = [
  { id: "1024587", name: "Sarah Chen", age: 42, gender: "F", reason: "Head Trauma", status: "High Risk", ward: "ICU-3" },
  { id: "7658321", name: "Omar Farooq", age: 40, gender: "M", reason: "Heart Failure", status: "Discharged", ward: "—" },
  { id: "2156793", name: "David Lee", age: 67, gender: "M", reason: "Pneumonia", status: "Recovering", ward: "G-12" },
  { id: "3298461", name: "Ayesha Begum", age: 87, gender: "F", reason: "Post-Op Recovery", status: "Stable", ward: "R-14" },
  { id: "4532109", name: "Habib Chowdhury", age: 28, gender: "M", reason: "Post-Op Recovery", status: "Stable", ward: "ICU-3" },
  { id: "5874632", name: "Nasreen Akter", age: 55, gender: "F", reason: "Post Traumatic Stress", status: "High Risk", ward: "ICU-2" },
  { id: "9012345", name: "James Miller", age: 51, gender: "M", reason: "Chest Pain", status: "Admitted", ward: "R-08" },
  { id: "8021566", name: "Priya Nair", age: 34, gender: "F", reason: "Diabetes Management", status: "Admitted", ward: "R-22" },
  { id: "7730199", name: "Robert Kim", age: 72, gender: "M", reason: "COPD Exacerbation", status: "Admitted", ward: "G-05" },
  { id: "6612408", name: "Elena Rossi", age: 29, gender: "F", reason: "Observation", status: "Admitted", ward: "ED-2" },
  { id: "5543891", name: "Marcus Webb", age: 45, gender: "M", reason: "Appendectomy", status: "Discharged", ward: "—" },
  { id: "4488120", name: "Fatima Noor", age: 63, gender: "F", reason: "Stroke Follow-up", status: "Discharged", ward: "—" },
];

const filters = ["All", "Admitted", "Recovery", "High Risk", "Stable", "Discharged"] as const;

export const statusColors: Record<string, { bg: string; text: string }> = {
  "High Risk": { bg: "#fce4e4", text: "#c0392b" },
  Discharged: { bg: "#fdebd0", text: "#b8860b" },
  Recovering: { bg: "#dbe8fd", text: "#1a4fd6" },
  Stable: { bg: "#d5f5e3", text: "#27ae60" },
  Admitted: { bg: "#e3f2fd", text: "#1565c0" },
};

const inHospital = (s: string) =>
  ["Admitted", "High Risk", "Recovering", "Stable"].includes(s);

export function getDashboardStats() {
  const rows = staticPatients;
  const admittedLike = rows.filter((p) => inHospital(p.status)).length;
  const discharged = rows.filter((p) => p.status === "Discharged").length;
  const highRisk = rows.filter((p) => p.status === "High Risk").length;
  const recovery = rows.filter((p) => p.status === "Recovering").length;
  return [
    { label: "Total Patients", value: rows.length },
    { label: "Admitted / In-house", value: admittedLike },
    { label: "In Recovery", value: recovery },
    { label: "High-Risk", value: highRisk },
  ] as const;
}

export function getCensusSummary() {
  const rows = staticPatients;
  return {
    total: rows.length,
    admitted: rows.filter((p) => p.status === "Admitted").length,
    inHouse: rows.filter((p) => inHospital(p.status)).length,
    discharged: rows.filter((p) => p.status === "Discharged").length,
    highRisk: rows.filter((p) => p.status === "High Risk").length,
  };
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

export function PatientStatCards() {
  const stats = getDashboardStats();
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
                {["Patient ID", "Patient Name", "Reason", "Status", "Ward", "Action"].map((h) => (
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
                    <td className="whitespace-nowrap px-4 py-3.5 text-[13px] text-[#555] sm:px-[22px] sm:py-4 sm:text-[13.5px]">
                      {p.id}
                    </td>
                    <td className="min-w-[140px] px-4 py-3.5 sm:px-[22px] sm:py-4">
                      <div className="text-sm font-semibold text-[#1a1a1a]">{p.name}</div>
                      <div className="mt-0.5 text-[11px] text-[#999] sm:text-[12.5px]">
                        {p.age}y · {p.gender}
                      </div>
                    </td>
                    <td className="max-w-[180px] px-4 py-3.5 text-[13px] text-[#555] sm:px-[22px] sm:py-4 sm:text-[13.5px]">
                      <span className="line-clamp-2">{p.reason}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 sm:px-[22px] sm:py-4">
                      <span
                        className="inline-block max-w-[9rem] truncate rounded-full px-2.5 py-1 text-[11px] font-medium sm:max-w-none sm:px-3.5 sm:text-[12.5px]"
                        style={{
                          background: statusColors[p.status]?.bg ?? "#eee",
                          color: statusColors[p.status]?.text ?? "#555",
                        }}
                        title={p.status}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-[13px] text-[#555] sm:px-[22px] sm:py-4 sm:text-[13.5px]">
                      {p.ward}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 sm:px-[22px] sm:py-4">
                      <Link
                        href={`/patients/${p.id}`}
                        className="inline-flex rounded-lg bg-[#2d6a2e] px-3 py-1.5 text-center text-xs font-medium text-white transition-colors duration-200 hover:bg-[#245a25] sm:px-[18px] sm:py-[7px] sm:text-[13px]"
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
