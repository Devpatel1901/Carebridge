"use client";

import { useState } from "react";
import { Building2, ChevronRight, FileText, Mail, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PatientDetail } from "@/lib/api";
import { staticPatients } from "@/components/carebridge/patient-management-static";
import { DischargeUploadModal } from "@/components/carebridge/discharge-upload-modal";

type StaticRow = (typeof staticPatients)[number];

type Props = {
  patient: PatientDetail;
  demoRow: StaticRow | undefined;
  intakeBusy: boolean;
  onDischargeFile: (text: string) => Promise<void>;
};

function formatPhoneDisplay(phone: string | undefined | null) {
  if (!phone) return "—";
  const d = phone.replace(/\D/g, "");
  if (d.length === 11 && d.startsWith("1")) {
    return `+1 (${d.slice(1, 4)}) ${d.slice(4, 7)}-${d.slice(7)}`;
  }
  return phone;
}

function patientIdLine(patient: PatientDetail, demoRow: StaticRow | undefined) {
  if (demoRow) return `ID: ${demoRow.id}`;
  if (/^\d+$/.test(patient.id)) return `ID: ${patient.id}`;
  return `ID: ${patient.id.slice(0, 8)}…`;
}

export function PatientDetailRightRail({ patient, demoRow, intakeBusy, onDischargeFile }: Props) {
  const [modalOpen, setModalOpen] = useState(false);

  const statusLabel = demoRow?.status ?? patient.status ?? "—";
  const statusUpper = statusLabel.toUpperCase();
  const diagnosis = patient.discharge_summary?.diagnosis ?? demoRow?.reason ?? "—";
  const wardBed = demoRow?.ward ?? "—";
  const ageGender =
    demoRow != null ? `${demoRow.age}y, ${demoRow.gender === "M" ? "Male" : demoRow.gender === "F" ? "Female" : demoRow.gender}` : "—";

  const dischargeNote =
    statusLabel === "Recovering"
      ? "*Discharge requested — Awaiting*"
      : statusLabel === "Discharged"
        ? "*Patient discharged — summary on file*"
        : "*In active care — review follow-up plan*";

  return (
    <>
      <aside className="order-2 flex w-full shrink-0 flex-col border-t border-[#e8e8e8] bg-white md:min-h-[calc(100vh-52px)] md:w-[min(100%,360px)] md:max-w-[360px] md:border-l md:border-t-0">
        <div className="flex flex-1 flex-col gap-0 overflow-y-auto">
          {/* Patient Information */}
          <section className="px-4 py-5 sm:px-5 md:px-6 md:py-6">
            <h2 className="text-base font-bold text-[#1a1a1a]">Patient Information</h2>
            <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#999]">Patient summary</p>

            <dl className="mt-4 space-y-3 text-[13px]">
              <div className="flex justify-between gap-3">
                <dt className="shrink-0 text-[#666]">Patient Name</dt>
                <dd className="text-right font-bold text-[#1a1a1a]">{patient.name}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="shrink-0 text-[#666]">Age, Gender</dt>
                <dd className="text-right font-bold text-[#1a1a1a]">{ageGender}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="shrink-0 text-[#666]">Patient ID</dt>
                <dd className="text-right font-bold text-[#1a1a1a]">{patientIdLine(patient, demoRow)}</dd>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <dt className="text-[#666]">Status</dt>
                <dd>
                  <span className="inline-block rounded-md bg-[#dbe8fd] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-[#1a4fd6]">
                    {statusUpper}
                  </span>
                </dd>
              </div>
            </dl>

            <p className="mt-4 text-[13px] italic leading-snug text-[#888]">{dischargeNote}</p>

            <div className="my-5 h-px bg-[#eee]" />

            <button
              type="button"
              className="flex w-full items-center justify-between gap-2 rounded-lg border border-transparent py-2.5 text-left text-[13px] transition-colors hover:bg-[#f8f9fa]"
            >
              <span className="text-[#666]">Diagnosis</span>
              <span className="flex min-w-0 items-center gap-1 font-semibold text-[#1a1a1a]">
                <span className="truncate">{diagnosis}</span>
                <ChevronRight className="h-4 w-4 shrink-0 text-[#bbb]" />
              </span>
            </button>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-2 rounded-lg border border-transparent py-2.5 text-left text-[13px] transition-colors hover:bg-[#f8f9fa]"
            >
              <span className="text-[#666]">Ward / Bed</span>
              <span className="flex items-center gap-1 font-semibold text-[#1a1a1a]">
                {wardBed}
                <ChevronRight className="h-4 w-4 shrink-0 text-[#bbb]" />
              </span>
            </button>

            <Button
              type="button"
              onClick={() => setModalOpen(true)}
              disabled={intakeBusy}
              className="mt-5 h-11 w-full rounded-lg bg-[#2d5a43] text-[15px] font-semibold text-white shadow-sm hover:bg-[#244a36] disabled:opacity-60"
            >
              {intakeBusy ? "Processing…" : "Discharge Patient"}
            </Button>
          </section>

          <div className="h-px bg-[#eee]" />

          {/* Care Team */}
          <section className="px-4 py-5 sm:px-5 md:px-6 md:py-6">
            <h2 className="text-base font-bold text-[#1a1a1a]">Care Team</h2>

            <ul className="mt-4 space-y-4">
              <li className="flex gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e8e8e8] text-xs font-bold text-[#444]">
                  AK
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[#1a1a1a]">Dr. Ahmed Khan</p>
                  <p className="text-[13px] text-[#888]">Cardiologist</p>
                </div>
              </li>
              <li className="flex gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e3f2fd] text-xs font-bold text-[#1565c0]">
                  LC
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[#1a1a1a]">Li-Na Chen</p>
                  <p className="text-[13px] text-[#888]">Nurse</p>
                </div>
              </li>
            </ul>

            <div className="mt-5 space-y-3 text-[13px]">
              <div className="flex gap-2 text-[#666]">
                <Building2 className="mt-0.5 h-4 w-4 shrink-0 text-[#aaa]" />
                <p>
                  <span className="text-[#666]">Department: </span>
                  <span className="font-bold text-[#1a1a1a]">Internal Medicine</span>
                </p>
              </div>
              <div className="flex gap-2 text-[#666]">
                <Phone className="mt-0.5 h-4 w-4 shrink-0 text-[#aaa]" />
                <p>{formatPhoneDisplay(patient.phone)}</p>
              </div>
              <div className="flex gap-2 text-[#666]">
                <Mail className="mt-0.5 h-4 w-4 shrink-0 text-[#aaa]" />
                <p className="break-all">ahmed.khan@carebridge.org</p>
              </div>
            </div>

            <div className="my-5 h-px bg-[#eee]" />

            <p className="text-sm font-bold text-[#1a1a1a]">Assigned Team:</p>
            <ul className="mt-3 space-y-4">
              <li className="flex gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#f0f0f0] text-[10px] font-bold text-[#666]">
                  MR
                </div>
                <div className="min-w-0 text-[13px]">
                  <p>
                    <span className="font-bold text-[#1a1a1a]">P.T. Maria Rossi</span>
                    <span className="text-[#888]"> (Physical Therapy)</span>
                  </p>
                  <p className="mt-0.5 text-[#888]">maria.rossi@carebridge.org</p>
                </div>
              </li>
              <li className="flex gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#d5f5e3] text-[10px] font-bold text-[#2d6a2e]">
                  JD
                </div>
                <div className="min-w-0 text-[13px]">
                  <p className="font-bold text-[#1a1a1a]">Dietitian John Doe</p>
                  <p className="mt-0.5 text-[#888]">john.doe@carebridge.org</p>
                </div>
              </li>
            </ul>
          </section>

          <div className="h-px bg-[#eee]" />

          {/* Reports */}
          <section className="px-4 pb-8 pt-5 sm:px-5 md:px-6 md:pb-10 md:pt-6">
            <h2 className="text-base font-bold text-[#1a1a1a]">Reports</h2>
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-[#e8e8e8] bg-[#f5f5f5] px-3 py-3 text-[13px] text-[#555]">
              <FileText className="mt-0.5 h-4 w-4 shrink-0 text-[#888]" />
              <p className="leading-snug">Latest discharge summary and attachments will appear here when synced.</p>
            </div>
          </section>
        </div>
      </aside>

      <DischargeUploadModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        busy={intakeBusy}
        onComplete={onDischargeFile}
      />
    </>
  );
}
