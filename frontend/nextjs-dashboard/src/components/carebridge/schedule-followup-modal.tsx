"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarDays, Clock, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { defaultEasternDateTimeParts, DISPLAY_TIME_ZONE } from "@/lib/datetime";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  patientId: string;
  onScheduled: () => Promise<void>;
};

const MINUTE_OPTIONS = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, "0"));

function from24Hour(time24: string): { h12: number; m: string; ap: "AM" | "PM" } {
  const [H, rawM] = time24.split(":");
  const Hn = parseInt(H ?? "0", 10);
  let Mn = parseInt(rawM ?? "0", 10);
  if (Number.isNaN(Mn)) Mn = 0;
  Mn = Math.max(0, Math.min(59, Mn));
  const M = String(Mn).padStart(2, "0");
  const ap: "AM" | "PM" = Hn >= 12 ? "PM" : "AM";
  let h12 = Hn % 12;
  if (h12 === 0) h12 = 12;
  return { h12, m: M, ap };
}

function to24Hour(h12: number, minute: string, ap: "AM" | "PM"): string {
  let H: number;
  if (ap === "AM") {
    H = h12 === 12 ? 0 : h12;
  } else {
    H = h12 === 12 ? 12 : h12 + 12;
  }
  return `${String(H).padStart(2, "0")}:${minute}`;
}

/** DB/async pipeline can lag the HTTP response — refetch a few times so the list updates. */
async function refreshAfterSchedule(onScheduled: () => Promise<void>): Promise<void> {
  await onScheduled();
  await new Promise((r) => setTimeout(r, 450));
  await onScheduled();
  await new Promise((r) => setTimeout(r, 900));
  await onScheduled();
}

const selectClass =
  "w-full cursor-pointer appearance-none rounded-xl border-2 border-[#c5d9c5] bg-white px-3 py-2.5 text-center text-sm font-semibold text-[#1a3d24] shadow-sm outline-none transition-colors hover:border-[#2d6a2e] focus:border-[#2d6a2e] focus:ring-2 focus:ring-[#2d6a2e]/25 disabled:opacity-50";

export function ScheduleFollowupModal({ open, onOpenChange, patientId, onScheduled }: Props) {
  const [date, setDate] = useState("");
  const [h12, setH12] = useState(10);
  const [minute, setMinute] = useState("00");
  const [ap, setAp] = useState<"AM" | "PM">("AM");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setError(null);
      return;
    }
    const d = defaultEasternDateTimeParts();
    setDate(d.date);
    const t = from24Hour(d.time);
    setH12(t.h12);
    setMinute(t.m);
    setAp(t.ap);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onOpenChange(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onOpenChange]);

  const datePreview = useMemo(() => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
    const [y, mo, d] = date.split("-").map(Number);
    const dt = new Date(y, mo - 1, d);
    if (Number.isNaN(dt.getTime())) return null;
    return dt.toLocaleDateString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }, [date]);

  const time24 = to24Hour(h12, minute, ap);

  const handleSubmit = async () => {
    if (!date.trim()) {
      setError("Choose a date.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.scheduleDoctorFollowup(patientId, {
        eastern_date: date.trim(),
        eastern_time: time24,
      });
      await refreshAfterSchedule(onScheduled);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not schedule follow-up.");
    } finally {
      setBusy(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !busy) onOpenChange(false);
      }}
    >
      <div className="absolute inset-0 bg-black/45 backdrop-blur-[2px]" aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="schedule-followup-title"
        className="relative z-[101] w-full max-w-lg overflow-hidden rounded-2xl border border-[#d8e5d8] bg-white shadow-2xl shadow-black/10"
      >
        <div className="flex items-start justify-between border-b border-[#e5ebe5] bg-[#f6faf6] px-5 py-4 sm:px-6">
          <h2 id="schedule-followup-title" className="text-lg font-bold text-[#1a3d24]">
            Schedule follow-up call
          </h2>
          <button
            type="button"
            disabled={busy}
            onClick={() => onOpenChange(false)}
            className="rounded-lg p-1.5 text-[#5a6b5a] transition-colors hover:bg-white hover:text-[#1a1a1a] disabled:opacity-50"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-5 px-5 py-5 sm:px-6">
          <p className="text-sm leading-relaxed text-[#4a5a4a]">
            Pick when the automated voice follow-up should run. All times are{" "}
            <span className="font-semibold text-[#2d4a32]">US Eastern</span> ({DISPLAY_TIME_ZONE})
            — the scheduler runs the call at that moment.
          </p>

          <div className="rounded-2xl border-2 border-[#c5d9c5] bg-gradient-to-b from-[#fbfcfb] to-[#f0f6f0] p-4 shadow-inner">
            <div className="mb-3 flex items-center gap-2 text-[#2d6a2e]">
              <CalendarDays className="h-5 w-5 shrink-0" strokeWidth={2} />
              <span className="text-xs font-bold uppercase tracking-wider">Date</span>
            </div>
            <input
              id="sf-date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              disabled={busy}
              className="w-full min-h-[52px] cursor-pointer rounded-xl border-2 border-[#a8c4a8] bg-white px-4 py-3 text-base font-medium text-[#1a3d24] shadow-sm outline-none transition-[border,box-shadow] focus:border-[#2d6a2e] focus:ring-4 focus:ring-[#2d6a2e]/15 disabled:opacity-60 [color-scheme:light]"
            />
            {datePreview && (
              <p className="mt-3 text-center text-sm font-medium text-[#3d5c43]">{datePreview}</p>
            )}
          </div>

          <div className="rounded-2xl border-2 border-[#b8cce8] bg-gradient-to-b from-[#fafcfe] to-[#eef4fc] p-4 shadow-inner">
            <div className="mb-3 flex items-center gap-2 text-[#1a4a7a]">
              <Clock className="h-5 w-5 shrink-0" strokeWidth={2} />
              <span className="text-xs font-bold uppercase tracking-wider">Time (Eastern)</span>
            </div>
            <div className="grid grid-cols-3 gap-2 sm:gap-3">
              <div>
                <label htmlFor="sf-hour" className="mb-1 block text-[10px] font-semibold uppercase text-[#5a6b7a]">
                  Hour
                </label>
                <select
                  id="sf-hour"
                  value={h12}
                  onChange={(e) => setH12(parseInt(e.target.value, 10))}
                  disabled={busy}
                  className={selectClass}
                >
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="sf-min" className="mb-1 block text-[10px] font-semibold uppercase text-[#5a6b7a]">
                  Minute
                </label>
                <select
                  id="sf-min"
                  value={minute}
                  onChange={(e) => setMinute(e.target.value)}
                  disabled={busy}
                  className={selectClass}
                >
                  {MINUTE_OPTIONS.map((m) => (
                    <option key={m} value={m}>
                      :{m}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="sf-ap" className="mb-1 block text-[10px] font-semibold uppercase text-[#5a6b7a]">
                  Period
                </label>
                <select
                  id="sf-ap"
                  value={ap}
                  onChange={(e) => setAp(e.target.value as "AM" | "PM")}
                  disabled={busy}
                  className={selectClass}
                >
                  <option value="AM">AM</option>
                  <option value="PM">PM</option>
                </select>
              </div>
            </div>
            <p className="mt-3 text-center text-xs text-[#5a6b7a]">
              24-hour equivalent: <span className="font-mono font-semibold text-[#1a3d24]">{time24}</span>
            </p>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex flex-wrap justify-end gap-2 border-t border-[#eee] pt-4">
            <Button
              type="button"
              variant="outline"
              disabled={busy}
              onClick={() => onOpenChange(false)}
              className="border-[#ccc]"
            >
              Cancel
            </Button>
            <Button
              type="button"
              disabled={busy}
              onClick={() => void handleSubmit()}
              className="bg-[#2d6a2e] text-white hover:bg-[#245a25]"
            >
              {busy ? "Scheduling…" : "Schedule"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
