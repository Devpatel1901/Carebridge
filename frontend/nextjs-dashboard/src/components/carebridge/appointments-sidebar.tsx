"use client";

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

/**
 * Right navbar: Upcoming Appointments (calendar) + Today’s Schedule only.
 * `order-2` keeps this column on the right when paired with main `order-1` (do not use order-none on lg).
 */
export function AppointmentsSidebar() {
  const marchDays = buildMarchDays();

  return (
    <aside
      className="order-2 flex w-full min-w-0 flex-col border-t border-[#e8e8e8] bg-white md:min-h-[calc(100vh-52px)] md:w-[310px] md:max-w-[310px] md:shrink-0 md:border-l md:border-t-0"
    >
      <div className="flex flex-1 flex-col px-4 py-5 sm:px-5 md:min-h-0 md:grow md:px-[22px] md:py-6">
        <h2 className="mb-4 text-base font-bold text-[#1a1a1a]">Upcoming Appointments</h2>

        <div className="mb-3 flex items-center justify-between">
          <div>
            <span className="block text-sm font-semibold text-[#1a1a1a]">Today</span>
            <span className="text-xs text-[#999]">March 2026</span>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded-md p-1 text-[#999] transition-colors hover:bg-[#f0f0f0] hover:text-[#555]"
              aria-label="Previous month"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <button
              type="button"
              className="rounded-md p-1 text-[#999] transition-colors hover:bg-[#f0f0f0] hover:text-[#555]"
              aria-label="Next month"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </div>
        </div>

        <div className="mb-5 w-full">
          <div className="mb-1.5 grid grid-cols-7 gap-0 text-center">
            {weekDays.map((d) => (
              <div key={d} className="py-1 text-[10px] font-medium text-[#999] sm:text-xs">
                {d}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-0 text-center">
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

        <h3 className="mb-3 text-[15px] font-bold text-[#1a1a1a]">Today&apos;s Schedule</h3>
        <div className="flex flex-col gap-1">
          {schedule.map((item, i) => (
            <div key={i} className="flex gap-3 py-2">
              <div className="min-h-[32px] w-[3px] shrink-0 rounded-sm" style={{ background: item.color }} />
              <div className="min-w-0 flex-1">
                <div className="text-[12px] font-medium leading-snug text-[#1a1a1a] sm:text-[13.5px]">
                  {item.time} - {item.title}
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
