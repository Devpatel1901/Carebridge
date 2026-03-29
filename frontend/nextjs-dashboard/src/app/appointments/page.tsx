"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, AppointmentItem } from "@/lib/api";
import { formatEasternDateTime } from "@/lib/datetime";
import { useDoctor } from "@/lib/doctor-context";

const statusColors: Record<string, string> = {
  scheduled: "bg-blue-50 text-blue-900 border-blue-200",
  confirmed: "bg-green-50 text-green-900 border-green-200",
  completed: "bg-green-50 text-green-900 border-green-200",
  cancelled: "bg-red-50 text-red-800 border-red-200",
  pending: "bg-amber-50 text-amber-900 border-amber-200",
  pending_confirmation: "bg-gray-50 text-gray-600 border-gray-200",
  pending_manual: "bg-orange-50 text-orange-900 border-orange-300",
};

const statusLabel: Record<string, string> = {
  pending_manual: "Needs Manual Scheduling",
  pending_confirmation: "Awaiting Confirmation",
  confirmed: "Confirmed",
  scheduled: "Scheduled",
  completed: "Completed",
  cancelled: "Cancelled",
};

const cardClass = "border border-[#e8e8e8] bg-white shadow-sm";

function PendingManualBanner({ notes }: { notes: string | null }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-orange-200 bg-orange-50 px-3 py-2 text-sm text-orange-800">
      <span className="mt-0.5 shrink-0 text-base">⚠</span>
      <div>
        <p className="font-semibold">Action required — manual scheduling needed</p>
        {notes && <p className="mt-0.5 text-orange-700">{notes}</p>}
      </div>
    </div>
  );
}

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const { doctor } = useDoctor();

  const fetchAppointments = async () => {
    try {
      const data = await api.getAppointments(doctor?.id);
      // Sort: pending_manual first, then by created_at desc
      data.sort((a, b) => {
        if (a.status === "pending_manual" && b.status !== "pending_manual") return -1;
        if (b.status === "pending_manual" && a.status !== "pending_manual") return 1;
        return new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime();
      });
      setAppointments(data);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
    const interval = setInterval(fetchAppointments, 5000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doctor?.id]);

  const pendingManualCount = appointments.filter((a) => a.status === "pending_manual").length;

  return (
    <div className="space-y-6 px-7 py-6">
      <div className="flex items-center justify-between">
        <div>
            <h1 className="text-[22px] font-bold text-[#1a1a1a]">Appointments</h1>
            {doctor && (
              <p className="text-sm text-[#888]">{doctor.name} · {doctor.specialty}</p>
            )}
          </div>
        <div className="flex items-center gap-2">
          {pendingManualCount > 0 && (
            <Badge variant="outline" className="border-orange-300 bg-orange-50 text-orange-800">
              {pendingManualCount} need manual scheduling
            </Badge>
          )}
          <Badge variant="outline" className="border-[#ddd] bg-[#fafafa] text-[#555]">
            {appointments.length} total
          </Badge>
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-[#888]">Loading...</div>
      ) : appointments.length === 0 ? (
        <Card className={cardClass}>
          <CardContent className="p-8 text-center text-[#888]">No appointments scheduled.</CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {appointments.map((ap) => (
            <Card
              key={ap.id}
              className={`${cardClass} ${ap.status === "pending_manual" ? "border-orange-200" : ""}`}
            >
              <CardContent className="flex flex-col gap-3 p-4">
                {/* Pending manual banner */}
                {ap.status === "pending_manual" && (
                  <PendingManualBanner notes={ap.notes} />
                )}

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium capitalize text-[#1a1a1a]">
                        {ap.appointment_type.replace(/_/g, " ")}
                      </span>
                      {ap.patient_name && (
                        <Link
                          href={`/patients/${ap.patient_id}`}
                          className="text-sm text-[#2563eb] hover:underline"
                        >
                          {ap.patient_name}
                        </Link>
                      )}
                    </div>

                    {/* Doctor name for confirmed/scheduled appointments */}
                    {ap.doctor_name && ap.status !== "pending_manual" && (
                      <p className="text-sm text-[#555]">
                        <span className="font-medium">With:</span> {ap.doctor_name}
                      </p>
                    )}

                    {/* Notes for non-pending_manual (pending_manual notes shown in banner) */}
                    {ap.notes && ap.status !== "pending_manual" && (
                      <p className="text-sm text-[#888]">{ap.notes}</p>
                    )}
                  </div>

                  <div className="space-y-1 text-left sm:text-right">
                    <p className="text-sm text-[#333]">
                      {ap.scheduled_at
                        ? formatEasternDateTime(ap.scheduled_at)
                        : ap.status === "pending_manual"
                          ? "Not yet scheduled"
                          : "TBD"}
                    </p>
                    <Badge
                      variant="outline"
                      className={statusColors[ap.status] || "border-[#ddd] bg-[#fafafa] text-[#333]"}
                    >
                      {statusLabel[ap.status] || ap.status}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
