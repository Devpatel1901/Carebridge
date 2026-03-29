"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type AppointmentItem } from "@/lib/api";
import {
  apiInstantToEasternDateKey,
  easternTodayDateKey,
  formatEasternTimeOnly,
} from "@/lib/datetime";
import { useDoctor } from "@/lib/doctor-context";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const WEEK_DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const STATUS_COLOR: Record<string, string> = {
  confirmed: "#3d7c3f",
  scheduled: "#3d7c3f",
  completed: "#3d7c3f",
  pending: "#d97706",
  pending_confirmation: "#a0b8a0",
  pending_manual: "#ea580c",
  cancelled: "#9ca3af",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Returns the days array for a calendar grid, null = empty leading cell. */
function buildCalendarDays(year: number, month: number): (number | null)[] {
  const firstDayOfWeek = new Date(year, month, 1).getDay(); // 0 = Sun
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const days: (number | null)[] = [];
  for (let i = 0; i < firstDayOfWeek; i++) days.push(null);
  for (let d = 1; d <= daysInMonth; d++) days.push(d);
  return days;
}

function titleCase(str: string): string {
  return str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Right navbar: live calendar and schedule for the logged-in doctor.
 * Appointments are fetched from the DB Agent and filtered by doctor ID.
 * Clicking a calendar day shows that day's appointments in the schedule list.
 * Days with appointments show a small green indicator dot.
 */
export function AppointmentsSidebar() {
  const { doctor } = useDoctor();

  const todayKey = useMemo(() => easternTodayDateKey(), []);

  const [currentYear, setCurrentYear] = useState(() => {
    const [y] = todayKey.split("-").map(Number);
    return y;
  });
  const [currentMonth, setCurrentMonth] = useState(() => {
    const [, m] = todayKey.split("-").map(Number);
    return m - 1;
  }); // 0-indexed
  const [selectedDate, setSelectedDate] = useState<string>(todayKey);
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);

  // Fetch appointments, re-poll every 30 s
  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        const data = await api.getAppointments(doctor?.id);
        if (!cancelled) setAppointments(data);
      } catch {
        // silent — sidebar is non-critical
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [doctor?.id]);

  // Build date → appointments map (only scheduled/confirmed/completed have a date)
  const apptByDate = useMemo(() => {
    const map: Record<string, AppointmentItem[]> = {};
    for (const appt of appointments) {
      const key = apiInstantToEasternDateKey(appt.scheduled_at);
      if (!key) continue;
      if (!map[key]) map[key] = [];
      map[key].push(appt);
    }
    return map;
  }, [appointments]);

  // Set of day-numbers (1-31) that have at least one appointment in the current month view
  const daysWithAppts = useMemo(() => {
    const set = new Set<number>();
    for (const key of Object.keys(apptByDate)) {
      const [y, m, d] = key.split("-").map(Number);
      if (y === currentYear && m - 1 === currentMonth) set.add(d);
    }
    return set;
  }, [apptByDate, currentYear, currentMonth]);

  const calendarDays = useMemo(
    () => buildCalendarDays(currentYear, currentMonth),
    [currentYear, currentMonth],
  );

  // Appointments for the selected day, sorted by time
  const selectedAppts = useMemo(() => {
    return (apptByDate[selectedDate] ?? []).slice().sort((a, b) => {
      if (!a.scheduled_at) return 1;
      if (!b.scheduled_at) return -1;
      return a.scheduled_at < b.scheduled_at ? -1 : 1;
    });
  }, [apptByDate, selectedDate]);

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------

  const prevMonth = () => {
    if (currentMonth === 0) { setCurrentYear((y) => y - 1); setCurrentMonth(11); }
    else setCurrentMonth((m) => m - 1);
  };

  const nextMonth = () => {
    if (currentMonth === 11) { setCurrentYear((y) => y + 1); setCurrentMonth(0); }
    else setCurrentMonth((m) => m + 1);
  };

  // ---------------------------------------------------------------------------
  // Labels
  // ---------------------------------------------------------------------------

  const isToday = selectedDate === todayKey;
  const selectedDayLabel = isToday
    ? "Today"
    : new Date(`${selectedDate}T00:00:00`).toLocaleDateString([], {
        weekday: "long",
        month: "long",
        day: "numeric",
      });

  const scheduleHeading = isToday
    ? "Today's Schedule"
    : `Schedule — ${new Date(`${selectedDate}T00:00:00`).toLocaleDateString([], { month: "short", day: "numeric" })}`;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <aside className="order-2 flex w-full min-w-0 flex-col border-t border-[#e8e8e8] bg-white md:min-h-[calc(100vh-52px)] md:w-[310px] md:max-w-[310px] md:shrink-0 md:border-l md:border-t-0">
      <div className="flex flex-1 flex-col px-4 py-5 sm:px-5 md:min-h-0 md:grow md:px-[22px] md:py-6">

        {/* Header */}
        <h2 className="mb-4 text-base font-bold text-[#1a1a1a]">Upcoming Appointments</h2>

        {/* Month + navigation */}
        <div className="mb-3 flex items-center justify-between">
          <div>
            <span className="block text-sm font-semibold text-[#1a1a1a]">{selectedDayLabel}</span>
            <span className="text-xs text-[#999]">{MONTH_NAMES[currentMonth]} {currentYear}</span>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={prevMonth}
              className="rounded-md p-1 text-[#999] transition-colors hover:bg-[#f0f0f0] hover:text-[#555]"
              aria-label="Previous month"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <button
              type="button"
              onClick={nextMonth}
              className="rounded-md p-1 text-[#999] transition-colors hover:bg-[#f0f0f0] hover:text-[#555]"
              aria-label="Next month"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </div>
        </div>

        {/* Calendar grid */}
        <div className="mb-5 w-full">
          {/* Day-of-week headers */}
          <div className="mb-1.5 grid grid-cols-7 gap-0 text-center">
            {WEEK_DAYS.map((d) => (
              <div key={d} className="py-1 text-[10px] font-medium text-[#999] sm:text-xs">{d}</div>
            ))}
          </div>

          {/* Day cells */}
          <div className="grid grid-cols-7 gap-0 text-center">
            {calendarDays.map((day, i) => {
              if (day === null) {
                return <div key={`pad-${i}`} />;
              }

              const dateKey = `${currentYear}-${String(currentMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
              const isSelected = dateKey === selectedDate;
              const isTodayCell = dateKey === todayKey;
              const hasAppt = daysWithAppts.has(day);

              return (
                <button
                  key={dateKey}
                  type="button"
                  onClick={() => setSelectedDate(dateKey)}
                  aria-label={`${day} ${MONTH_NAMES[currentMonth]}`}
                  aria-pressed={isSelected}
                  className={
                    isSelected
                      ? "relative mx-auto flex h-7 w-7 items-center justify-center rounded-full bg-[#2d6a2e] text-[11px] font-semibold text-white sm:h-8 sm:w-8 sm:text-[13px]"
                      : isTodayCell
                      ? "relative mx-auto flex h-7 w-7 cursor-pointer items-center justify-center rounded-full border border-[#2d6a2e] text-[11px] font-semibold text-[#2d6a2e] transition-colors hover:bg-[#f0f7f0] sm:h-8 sm:w-8 sm:text-[13px]"
                      : "relative mx-auto flex h-7 w-7 cursor-pointer items-center justify-center rounded-full py-1 text-[11px] text-[#444] transition-colors hover:bg-[#f5f5f5] sm:h-8 sm:w-8 sm:py-[7px] sm:text-[13px]"
                  }
                >
                  {day}
                  {/* Dot indicator for days with appointments */}
                  {hasAppt && !isSelected && (
                    <span className="absolute bottom-0.5 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-[#2d6a2e]" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Schedule list */}
        <h3 className="mb-3 text-[15px] font-bold text-[#1a1a1a]">{scheduleHeading}</h3>

        {selectedAppts.length === 0 ? (
          <p className="text-[13px] text-[#aaa]">No appointments on this day.</p>
        ) : (
          <div className="flex flex-col gap-1 overflow-y-auto">
            {selectedAppts.map((appt) => (
              <div key={appt.id} className="flex gap-3 py-2">
                <div
                  className="min-h-[32px] w-[3px] shrink-0 rounded-sm"
                  style={{ background: STATUS_COLOR[appt.status] ?? "#a0b8a0" }}
                />
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] font-medium leading-snug text-[#1a1a1a] sm:text-[13.5px]">
                    {appt.scheduled_at ? formatEasternTimeOnly(appt.scheduled_at) : "TBD"}
                    {" — "}
                    {titleCase(appt.appointment_type)}
                    {appt.patient_name ? `: ${appt.patient_name}` : ""}
                  </div>
                  {appt.doctor_name && (
                    <div className="mt-0.5 text-[11px] text-[#999] sm:text-[12px]">
                      {appt.doctor_name}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
