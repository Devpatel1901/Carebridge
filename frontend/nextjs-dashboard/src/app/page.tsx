"use client";

import { useEffect, useState } from "react";
import {
  PatientManagementHeader,
  PatientStatCards,
  PatientStaticTableCard,
} from "@/components/carebridge/patient-management-static";
import { AppointmentsSidebar } from "@/components/carebridge/appointments-sidebar";
import { api, type PatientSummary } from "@/lib/api";

type LoadState = "loading" | "error" | "ok";

/**
 * Patient Management dashboard: stats and ward table load from the DB Agent (`GET /patients`)
 * so IDs and clinical rows match seeded SQLite data.
 */
export default function PatientsPage() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");

  useEffect(() => {
    let cancelled = false;
    setLoadState("loading");
    api
      .getPatients()
      .then((data) => {
        if (!cancelled) {
          setPatients(data);
          setLoadState("ok");
        }
      })
      .catch(() => {
        if (!cancelled) setLoadState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex min-h-[calc(100vh-52px)] w-full flex-1 flex-col md:flex-row md:items-stretch">
      <div className="order-1 min-w-0 flex-1 space-y-5 px-4 py-5 sm:px-6 sm:py-6 md:px-7">
        <PatientManagementHeader />
        <PatientStatCards variant="figma" patients={patients} />
        <PatientStaticTableCard patients={patients} loadState={loadState} />
      </div>
      <AppointmentsSidebar />
    </div>
  );
}
