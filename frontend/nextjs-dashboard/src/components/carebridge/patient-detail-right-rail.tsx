"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { PatientDetail } from "@/lib/api";
import { staticPatients } from "@/components/carebridge/patient-management-static";

type StaticRow = (typeof staticPatients)[number];

type Props = {
  patient: PatientDetail;
  demoRow: StaticRow | undefined;
  isLive: boolean;
  intakeBusy: boolean;
  triggerBusy: boolean;
  canTrigger: boolean;
  onDischargeFile: (text: string) => Promise<void>;
  onTriggerFollowup: () => void;
};

export function PatientDetailRightRail({
  patient,
  demoRow,
  isLive,
  intakeBusy,
  triggerBusy,
  canTrigger,
  onDischargeFile,
  onTriggerFollowup,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const statusLabel = demoRow?.status ?? patient.status ?? "—";
  const ward = demoRow?.ward ?? "—";

  const handlePick = () => {
    setError(null);
    inputRef.current?.click();
  };

  const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError(null);
    try {
      const text = await file.text();
      if (!text.trim()) {
        setError("File is empty.");
        return;
      }
      await onDischargeFile(text);
    } catch {
      setError("Could not read file. Use a .txt discharge summary for intake.");
    }
  };

  return (
    <aside className="order-2 flex w-full shrink-0 flex-col border-t border-[#e8e8e8] bg-white md:min-h-[calc(100vh-52px)] md:w-[min(100%,340px)] md:max-w-[340px] md:border-l md:border-t-0">
      <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-4 py-5 sm:px-5 md:px-6 md:py-6">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-[#888]">Patient summary</h2>
          <div className="mt-3 rounded-xl border border-[#e8e8e8] bg-[#f8f9fa] p-4 shadow-sm">
            <p className="text-lg font-bold text-[#1a1a1a]">{patient.name}</p>
            <p className="mt-1 text-sm text-[#666]">
              {demoRow ? `${demoRow.age}y · ${demoRow.gender}` : "—"} · ID {patient.id.slice(0, 8)}…
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge
                variant="outline"
                className="rounded-full border-[#dbe8fd] bg-[#dbe8fd] text-[#1a4fd6] font-medium uppercase"
              >
                {statusLabel}
              </Badge>
              {isLive && (
                <Badge variant="outline" className="border-green-200 bg-green-50 text-green-800">
                  Live record
                </Badge>
              )}
            </div>
            <p className="mt-3 text-sm text-[#555]">
              <span className="text-[#888]">Diagnosis: </span>
              {patient.discharge_summary?.diagnosis ?? demoRow?.reason ?? "—"}
            </p>
            <p className="mt-1 text-sm text-[#555]">
              <span className="text-[#888]">Ward / Bed: </span>
              {ward}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <input
            ref={inputRef}
            type="file"
            accept=".txt,.text,.md,.markdown"
            className="hidden"
            onChange={onChange}
          />
          {demoRow ? (
            <Button
              type="button"
              onClick={handlePick}
              disabled={intakeBusy}
              className="h-11 w-full rounded-xl bg-[#2d6a2e] text-base font-semibold text-white hover:bg-[#245a25] disabled:opacity-60"
            >
              {intakeBusy ? "Processing intake…" : "Discharge Patient"}
            </Button>
          ) : (
            <p className="rounded-lg border border-[#e8e8e8] bg-[#fafafa] px-3 py-2 text-xs text-[#666]">
              Discharge intake applies to demo patients from the ward list. This record is already in CareBridge —
              manage follow-up below.
            </p>
          )}
          <p className="text-[11px] leading-snug text-[#888]">
            Choose a discharge summary text file. This runs the same Brain intake as{" "}
            <code className="rounded bg-[#f0f0f0] px-1">demo_flow.py</code>, then you can trigger the Twilio follow-up.
          </p>
          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>

        <Button
          type="button"
          variant="outline"
          onClick={onTriggerFollowup}
          disabled={!canTrigger || triggerBusy}
          className="h-10 w-full rounded-xl border-[#2d6a2e]/40 bg-white text-[#2d6a2e] hover:bg-[#f5faf5]"
        >
          {triggerBusy ? "Triggering…" : "Trigger AI follow-up call"}
        </Button>
        {!canTrigger && isLive && (
          <p className="text-[11px] text-amber-800">Scheduler target unavailable.</p>
        )}

        <div>
          <h3 className="text-sm font-bold text-[#1a1a1a]">Care team</h3>
          <ul className="mt-3 space-y-3 text-sm">
            <li className="flex gap-3 rounded-lg border border-[#eee] bg-white p-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#e8f5e9] text-xs font-bold text-[#2d6a2e]">
                AK
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-[#1a1a1a]">Dr. Ahmed Khan</p>
                <p className="text-xs text-[#888]">Cardiology · akhan@carebridge.demo</p>
              </div>
            </li>
            <li className="flex gap-3 rounded-lg border border-[#eee] bg-white p-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#e3f2fd] text-xs font-bold text-[#1565c0]">
                LC
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-[#1a1a1a]">Li-Na Chen, RN</p>
                <p className="text-xs text-[#888]">Floor nurse · lchen@carebridge.demo</p>
              </div>
            </li>
          </ul>
        </div>

        <div className="rounded-lg border border-dashed border-[#ddd] bg-[#fafafa] p-3 text-xs text-[#888]">
          Reports and attachments will appear here after documents are linked in a future release.
        </div>
      </div>
    </aside>
  );
}
