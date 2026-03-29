"use client";

import { getCensusSummary } from "./patient-management-static";

const schedule = [
  { time: "09:00", title: "Patient Review: Sarah Chen", sub: "Sarah Chen", color: "#3d7c3f" },
  { time: "10:30", title: "Consult with Dr. Wong", sub: null, color: "#a0b8a0" },
  { time: "11:45", title: "Trauma Ward Rounds", sub: null, color: "#a0b8a0" },
  { time: "13:30", title: "Next Consultation: David Lee", sub: "David Lee", color: "#3d7c3f" },
  { time: "15:00", title: "Surgery: Post-op Review", sub: null, color: "#a0b8a0" },
];

const weekDays = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function buildMarchDays() {
  const days: number[] = [];
  for (let i = 1; i <= 31; i++) days.push(i);
  return days;
}

/** Right column: census status strip + calendar + today’s schedule (responsive). */
export function AppointmentsSidebar() {
  const marchDays = buildMarchDays();
  const census = getCensusSummary();

  return (
    <aside
      className="order-2 flex w-full min-w-0 flex-col border-t border-[#e8e8e8] bg-white lg:order-none lg:w-[min(100%,320px)] lg:max-w-[320px] lg:shrink-0 lg:border-l lg:border-t-0"
    >
      <div className="flex max-h-[min(85vh,900px)] flex-1 flex-col overflow-y-auto px-4 py-5 sm:px-6 lg:max-h-none lg:px-[22px] lg:py-6">
        {/* Status bar — matches dummy census */}
        <div className="mb-5 rounded-xl border border-[#e8e8e8] bg-[#f8f9fa] p-3 shadow-sm">
          <p className="mb-2 text-center text-[11px] font-semibold uppercase tracking-wide text-[#888] sm:text-xs">
            Census overview
          </p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div className="rounded-lg bg-white px-2 py-2 text-center shadow-sm ring-1 ring-[#e8e8e8]">
              <div className="text-lg font-bold leading-none text-[#2d6a2e] sm:text-xl">{census.inHouse}</div>
              <div className="mt-1 text-[10px] text-[#888] sm:text-[11px]">In-house</div>
            </div>
            <div className="rounded-lg bg-white px-2 py-2 text-center shadow-sm ring-1 ring-[#e8e8e8]">
              <div className="text-lg font-bold leading-none text-[#1565c0] sm:text-xl">{census.admitted}</div>
              <div className="mt-1 text-[10px] text-[#888] sm:text-[11px]">Admitted</div>
            </div>
            <div className="rounded-lg bg-white px-2 py-2 text-center shadow-sm ring-1 ring-[#e8e8e8]">
              <div className="text-lg font-bold leading-none text-[#b8860b] sm:text-xl">{census.discharged}</div>
              <div className="mt-1 text-[10px] text-[#888] sm:text-[11px]">Discharged</div>
            </div>
            <div className="rounded-lg bg-white px-2 py-2 text-center shadow-sm ring-1 ring-[#e8e8e8]">
              <div className="text-lg font-bold leading-none text-[#c0392b] sm:text-xl">{census.highRisk}</div>
              <div className="mt-1 text-[10px] text-[#888] sm:text-[11px]">High-risk</div>
            </div>
          </div>
        </div>

        <h2 className="mb-4 text-base font-bold text-[#1a1a1a] sm:mb-[18px]">Upcoming Appointments</h2>

        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-semibold text-[#1a1a1a]">Today · Mar 2026</span>
          <div className="flex gap-2">
            <button
              type="button"
              className="cursor-pointer rounded-md p-1 text-[#999] transition-colors hover:bg-[#f0f0f0] hover:text-[#555]"
              aria-label="Previous month"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <button
              type="button"
              className="cursor-pointer rounded-md p-1 text-[#999] transition-colors hover:bg-[#f0f0f0] hover:text-[#555]"
              aria-label="Next month"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </div>
        </div>

        <div className="mb-6 w-full max-w-full">
          <div className="mb-1.5 grid grid-cols-7 gap-0.5 text-center sm:gap-0">
            {weekDays.map((d) => (
              <div key={d} className="py-1 text-[10px] font-medium text-[#999] sm:text-xs">
                {d}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-y-1 text-center">
            {marchDays.map((day, i) => (
              <div
                key={i}
                className={
                  day === 28
                    ? "mx-auto flex h-7 w-7 items-center justify-center rounded-full bg-[#2d6a2e] text-[11px] font-semibold text-white sm:h-8 sm:w-8 sm:text-[13px]"
                    : "py-1 text-[11px] text-[#444] sm:py-[7px] sm:text-[13px]"
                }
              >
                {day}
              </div>
            ))}
          </div>
        </div>

        <h3 className="mb-3 text-sm font-bold text-[#1a1a1a] sm:mb-4 sm:text-[15px]">Today&apos;s Schedule</h3>
        <div className="flex flex-col gap-1 sm:gap-1.5">
          {schedule.map((item, i) => (
            <div
              key={i}
              className="flex gap-3 rounded-lg py-2 transition-colors hover:bg-[#fafafa] sm:py-2.5"
            >
              <div className="min-h-[36px] w-[3px] shrink-0 rounded-sm" style={{ background: item.color }} />
              <div className="min-w-0 flex-1">
                <div className="text-[12px] font-medium leading-snug text-[#1a1a1a] sm:text-[13.5px]">
                  {item.time} — {item.title}
                </div>
                {item.sub && <div className="mt-0.5 text-[11px] text-[#999] sm:text-[12.5px]">{item.sub}</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
