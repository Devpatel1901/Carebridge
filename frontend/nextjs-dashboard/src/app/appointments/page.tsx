"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, AppointmentItem } from "@/lib/api";
import { formatEasternDateTime } from "@/lib/datetime";

const statusColors: Record<string, string> = {
  scheduled: "bg-blue-50 text-blue-900 border-blue-200",
  completed: "bg-green-50 text-green-900 border-green-200",
  cancelled: "bg-red-50 text-red-800 border-red-200",
  pending: "bg-amber-50 text-amber-900 border-amber-200",
};

const cardClass = "border border-[#e8e8e8] bg-white shadow-sm";

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAppointments = async () => {
    try {
      setAppointments(await api.getAppointments());
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
  }, []);

  return (
    <div className="space-y-6 px-7 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-[22px] font-bold text-[#1a1a1a]">Appointments</h1>
        <Badge variant="outline" className="border-[#ddd] bg-[#fafafa] text-[#555]">
          {appointments.length} total
        </Badge>
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
            <Card key={ap.id} className={cardClass}>
              <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium capitalize text-[#1a1a1a]">{ap.appointment_type}</span>
                    {ap.patient_name && (
                      <Link href={`/patients/${ap.patient_id}`} className="text-sm text-[#2563eb] hover:underline">
                        {ap.patient_name}
                      </Link>
                    )}
                  </div>
                  {ap.notes && <p className="text-sm text-[#888]">{ap.notes}</p>}
                </div>
                <div className="space-y-1 text-left sm:text-right">
                  <p className="text-sm text-[#333]">
                    {ap.scheduled_at ? formatEasternDateTime(ap.scheduled_at) : "TBD"}
                  </p>
                  <Badge
                    variant="outline"
                    className={statusColors[ap.status] || "border-[#ddd] bg-[#fafafa] text-[#333]"}
                  >
                    {ap.status}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
