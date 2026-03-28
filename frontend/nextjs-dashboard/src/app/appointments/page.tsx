"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, AppointmentItem } from "@/lib/api";

const statusColors: Record<string, string> = {
  scheduled: "bg-blue-900/50 text-blue-300 border-blue-700",
  completed: "bg-green-900/50 text-green-300 border-green-700",
  cancelled: "bg-red-900/50 text-red-300 border-red-700",
  pending: "bg-yellow-900/50 text-yellow-300 border-yellow-700",
};

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAppointments = async () => {
    try {
      setAppointments(await api.getAppointments());
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => {
    fetchAppointments();
    const interval = setInterval(fetchAppointments, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Appointments</h1>
        <Badge variant="outline" className="text-zinc-400">{appointments.length} total</Badge>
      </div>

      {loading ? (
        <div className="p-8 text-center text-zinc-500">Loading...</div>
      ) : appointments.length === 0 ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-8 text-center text-zinc-500">No appointments scheduled.</CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {appointments.map((ap) => (
            <Card key={ap.id} className="bg-zinc-900 border-zinc-800">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium capitalize">{ap.appointment_type}</span>
                    {ap.patient_name && (
                      <Link href={`/patients/${ap.patient_id}`} className="text-blue-400 hover:underline text-sm">
                        {ap.patient_name}
                      </Link>
                    )}
                  </div>
                  {ap.notes && <p className="text-zinc-400 text-sm">{ap.notes}</p>}
                </div>
                <div className="text-right space-y-1">
                  <p className="text-sm">{ap.scheduled_at ? new Date(ap.scheduled_at).toLocaleString() : "TBD"}</p>
                  <Badge variant="outline" className={statusColors[ap.status] || "bg-zinc-800 text-zinc-300 border-zinc-600"}>
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
