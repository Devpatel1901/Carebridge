"use client";

import {
  PatientManagementHeader,
  PatientStatCards,
  PatientStaticTableCard,
} from "@/components/carebridge/patient-management-static";
import { AppointmentsSidebar } from "@/components/carebridge/appointments-sidebar";

/**
 * Patient Management dashboard (Figma 1): static stats, dummy census table, calendar + schedule.
 * Live API list is not shown here — use View Details on a demo row, then discharge intake + Twilio flow.
 */
export default function PatientsPage() {
  return (
    <div className="flex min-h-[calc(100vh-52px)] w-full flex-1 flex-col md:flex-row md:items-stretch">
      {/* order-1 = main left; order-2 = right rail (full-height white column) */}
      <div className="order-1 min-w-0 flex-1 space-y-5 px-4 py-5 sm:px-6 sm:py-6 md:px-7">
        <PatientManagementHeader />
        <PatientStatCards variant="figma" />
        <PatientStaticTableCard />
      </div>
      <AppointmentsSidebar />
    </div>
  );
}
