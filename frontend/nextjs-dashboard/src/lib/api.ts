const DB_AGENT_URL = process.env.NEXT_PUBLIC_DB_AGENT_URL || "http://localhost:8003";
const BRAIN_AGENT_URL = process.env.NEXT_PUBLIC_BRAIN_AGENT_URL || "http://localhost:8001";
const SCHEDULER_URL = process.env.NEXT_PUBLIC_SCHEDULER_URL || "http://localhost:8004";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export interface PatientSummary {
  id: string;
  name: string;
  phone: string;
  status: string;
  risk_level: string | null;
  created_at: string | null;
}

export interface PatientDetail {
  id: string;
  name: string;
  phone: string;
  dob: string | null;
  email: string | null;
  status: string;
  risk_level: string | null;
  created_at: string | null;
  discharge_summary: {
    id: string;
    diagnosis: string;
    procedures: string | null;
    discharge_date: string | null;
    instructions: string | null;
    raw_text: string;
    created_at: string;
  } | null;
  medications: { id: string; name: string; dosage: string; frequency: string }[];
  questionnaire: {
    id: string;
    questions: { id: string; text: string; question_type: string; relevance: string }[];
    diagnosis_context: string;
    generated_at: string;
  } | null;
  interactions: {
    id: string;
    interaction_type: string;
    channel: string;
    /** Backend may store `question` (from event pipeline) or `question_text`. */
    responses: { question_id?: string; question_text?: string; question?: string; answer: string }[] | null;
    created_at: string;
  }[];
  alerts: {
    id: string;
    alert_type: string;
    severity: string;
    message: string;
    acknowledged: boolean;
    created_at: string;
  }[];
  appointments: {
    id: string;
    appointment_type: string;
    scheduled_at: string | null;
    status: string;
    notes: string | null;
    created_at: string;
  }[];
}

export interface AlertItem {
  id: string;
  patient_id: string;
  patient_name: string | null;
  alert_type: string;
  severity: string;
  message: string;
  acknowledged: boolean;
  created_at: string | null;
}

export interface AppointmentItem {
  id: string;
  patient_id: string;
  patient_name: string | null;
  appointment_type: string;
  scheduled_at: string | null;
  status: string;
  notes: string | null;
  created_at: string | null;
}

export interface TimelineEntry {
  id: string;
  event_type: string;
  patient_id: string;
  patient_name: string | null;
  summary: string;
  created_at: string | null;
  details: Record<string, unknown>;
}

export interface DischargeIntakeRequest {
  patient_name: string;
  patient_phone: string;
  patient_dob: string | null;
  patient_email: string | null;
  discharge_summary_text: string;
  /** When set, intake updates this patient row instead of creating a new id (matches seeded/demo IDs). */
  existing_patient_id?: string | null;
}

export interface DischargeIntakeResponse {
  patient_id: string;
  risk_level: string;
  decision: string;
  generated_questions: unknown[];
  correlation_id: string;
}

export const api = {
  getPatients: () => fetchJson<PatientSummary[]>(`${DB_AGENT_URL}/patients`),
  getPatient: (id: string) => fetchJson<PatientDetail>(`${DB_AGENT_URL}/patients/${id}`),
  getAlerts: () => fetchJson<AlertItem[]>(`${DB_AGENT_URL}/alerts`),
  acknowledgeAlert: (id: string) =>
    fetchJson<{ id: string; acknowledged: boolean }>(`${DB_AGENT_URL}/alerts/${id}/acknowledge`, {
      method: "PATCH",
    }),
  getAppointments: () => fetchJson<AppointmentItem[]>(`${DB_AGENT_URL}/appointments`),
  getTimeline: (patientId: string) =>
    fetchJson<TimelineEntry[]>(`${DB_AGENT_URL}/patients/${patientId}/timeline`),
  triggerFollowup: (patientId: string) =>
    fetchJson<{ status: string }>(`${SCHEDULER_URL}/trigger/${patientId}`, { method: "POST" }),
  /** Brain Agent — same pipeline as scripts/demo_flow.py step 1. Returns new patient_id. */
  ingestDischarge: (body: DischargeIntakeRequest) =>
    fetchJson<DischargeIntakeResponse>(`${BRAIN_AGENT_URL}/intake`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
