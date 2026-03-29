import type { PatientDetail } from "@/lib/api";
import { staticPatients } from "@/components/carebridge/patient-management-static";

export function findStaticPatient(routeId: string) {
  return staticPatients.find((p) => p.id === routeId);
}

function mapRiskLevel(status: string): string | null {
  if (status === "High Risk") return "high";
  if (status === "Stable") return "low";
  if (status === "Recovering") return "medium";
  if (status === "Discharged") return "low";
  if (status === "Admitted") return "medium";
  return "medium";
}

/** Static PatientDetail for Figma/demo IDs before a DB record exists. */
export function buildDemoPatientDetail(row: (typeof staticPatients)[number]): PatientDetail {
  return {
    id: row.id,
    name: row.name,
    phone: row.phone,
    dob: null,
    email: row.email ?? null,
    status: row.status,
    risk_level: mapRiskLevel(row.status),
    created_at: new Date().toISOString(),
    discharge_summary: {
      id: `demo-ds-${row.id}`,
      diagnosis: row.reason,
      procedures: null,
      discharge_date: row.status === "Discharged" ? "TBD (demo)" : null,
      instructions:
        "Demo admission/discharge copy. Upload a discharge document using Discharge Patient to run the live CareBridge intake pipeline.",
      raw_text: "",
      created_at: new Date().toISOString(),
    },
    medications: [
      {
        id: `demo-med-${row.id}`,
        name: "Placeholder (demo)",
        dosage: "—",
        frequency: "—",
      },
    ],
    questionnaire: null,
    interactions: [],
    alerts: [],
    appointments: [],
  };
}

export function isDemoRouteId(routeId: string): boolean {
  return staticPatients.some((p) => p.id === routeId);
}
