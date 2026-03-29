"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SeverityBadge } from "@/components/severity-badge";
import { api, PatientDetail } from "@/lib/api";
import { buildDemoPatientDetail, findStaticPatient } from "@/lib/demo-patient";
import { PatientDetailRightRail } from "@/components/carebridge/patient-detail-right-rail";

const tabListClass =
  "inline-flex h-auto w-full flex-wrap gap-1 rounded-lg bg-[#f0f0f0] p-1 text-[#555] sm:w-fit";
const tabTriggerClass =
  "rounded-md px-3 py-2 text-sm font-medium text-[#555] transition-colors hover:text-[#1a1a1a] data-active:bg-[#2d6a2e] data-active:text-white data-active:shadow-sm";

const cardClass = "rounded-xl border border-[#e8e8e8] bg-white shadow-sm";

const layoutRow =
  "flex w-full min-h-[calc(100vh-52px)] flex-1 flex-col md:flex-row md:items-stretch";

export default function PatientDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [apiPatient, setApiPatient] = useState<PatientDetail | null>(null);
  const [apiAttempted, setApiAttempted] = useState(false);
  const [intakeBusy, setIntakeBusy] = useState(false);
  const [triggerBusy, setTriggerBusy] = useState(false);
  const [workflowTargetId, setWorkflowTargetId] = useState<string | null>(null);

  const demoRow = useMemo(() => findStaticPatient(id), [id]);

  const patient = useMemo(() => {
    if (apiPatient) return apiPatient;
    if (demoRow) return buildDemoPatientDetail(demoRow);
    return null;
  }, [apiPatient, demoRow]);

  const isLive = Boolean(apiPatient);

  const fetchPatient = useCallback(async () => {
    try {
      const data = await api.getPatient(id);
      setApiPatient(data);
    } catch {
      setApiPatient(null);
    } finally {
      setApiAttempted(true);
    }
  }, [id]);

  useEffect(() => {
    setApiAttempted(false);
    setApiPatient(null);
    fetchPatient();
    const t = setInterval(fetchPatient, 8000);
    return () => clearInterval(t);
  }, [fetchPatient]);

  useEffect(() => {
    if (apiPatient) {
      setWorkflowTargetId(apiPatient.id);
      return;
    }
    const envId = process.env.NEXT_PUBLIC_TRIGGER_PATIENT_ID?.trim();
    if (envId) {
      setWorkflowTargetId(envId);
      return;
    }
    let cancelled = false;
    api
      .getPatients()
      .then((list) => {
        if (!cancelled) setWorkflowTargetId(list[0]?.id ?? null);
      })
      .catch(() => {
        if (!cancelled) setWorkflowTargetId(null);
      });
    return () => {
      cancelled = true;
    };
  }, [apiPatient]);

  const voiceInteractions = useMemo(() => {
    if (!patient) return [];
    return patient.interactions.filter(
      (i) => (i.channel || "").toLowerCase() === "voice" || (i.interaction_type || "").toLowerCase().includes("voice")
    );
  }, [patient]);

  const handleDischargeFile = async (text: string) => {
    if (!patient) return;
    setIntakeBusy(true);
    try {
      const res = await api.ingestDischarge({
        patient_name: patient.name,
        patient_phone: patient.phone,
        patient_dob: patient.dob,
        patient_email: patient.email,
        discharge_summary_text: text,
      });
      router.replace(`/patients/${res.patient_id}`);
    } catch {
      /* ignore */
    } finally {
      setIntakeBusy(false);
    }
  };

  const handleTrigger = async () => {
    const target = workflowTargetId;
    if (!target) return;
    setTriggerBusy(true);
    try {
      await api.triggerFollowup(target);
      await fetchPatient();
    } catch {
      /* ignore */
    } finally {
      setTriggerBusy(false);
    }
  };

  if (!patient) {
    if (!apiAttempted) {
      return (
        <div className={layoutRow}>
          <div className="flex flex-1 items-center justify-center px-4 py-16 text-[#888]">Loading…</div>
        </div>
      );
    }
    return (
      <div className={layoutRow}>
        <div className="flex flex-1 flex-col justify-center px-4 py-12 sm:px-8">
          <h1 className="text-xl font-bold text-[#1a1a1a]">Patient not found</h1>
          <p className="mt-2 text-sm text-[#888]">No matching demo profile and no API record for this ID.</p>
          <Link href="/" className="mt-4 text-sm font-medium text-[#2d6a2e] hover:underline">
            Back to Patient Management
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={layoutRow}>
      <div className="order-1 min-w-0 flex-1 space-y-5 px-4 py-5 sm:px-6 md:min-h-0 md:overflow-y-auto md:px-7 md:py-6">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#e8e8e8] bg-white px-2.5 py-1.5 text-[#555] transition-colors hover:bg-[#f8f9fa]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
          <span className="text-[#ccc]">/</span>
          <Link href="/" className="text-[#888] hover:text-[#2d6a2e]">
            Patients
          </Link>
          <span className="text-[#ccc]">/</span>
          <span className="font-medium text-[#1a1a1a]">{patient.name}</span>
        </div>

        <Tabs defaultValue="overview" className="space-y-5">
          <TabsList className={tabListClass}>
            <TabsTrigger value="overview" className={tabTriggerClass}>
              Overview
            </TabsTrigger>
            <TabsTrigger value="medical" className={tabTriggerClass}>
              Medical History
            </TabsTrigger>
            <TabsTrigger value="medications" className={tabTriggerClass}>
              Medications
            </TabsTrigger>
            <TabsTrigger value="followup" className={tabTriggerClass}>
              Follow-Up
            </TabsTrigger>
            <TabsTrigger value="appointments" className={tabTriggerClass}>
              Appointments
            </TabsTrigger>
            <TabsTrigger value="ai-calls" className={tabTriggerClass}>
              AI Call History
            </TabsTrigger>
            <TabsTrigger value="alerts" className={tabTriggerClass}>
              Alerts
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <Card className={cardClass}>
              <CardHeader>
                <CardTitle className="text-lg text-[#1a1a1a]">Admission summary</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <span className="text-[#888]">Reason for admission</span>
                  <p className="font-medium text-[#1a1a1a]">{demoRow?.reason ?? patient.discharge_summary?.diagnosis ?? "—"}</p>
                </div>
                <div>
                  <span className="text-[#888]">Admission date</span>
                  <p className="text-[#333]">{isLive ? "See EHR" : "— (demo)"}</p>
                </div>
                <div>
                  <span className="text-[#888]">Proposed discharge</span>
                  <p className="text-[#333]">{patient.discharge_summary?.discharge_date ?? "TBD"}</p>
                </div>
                <div>
                  <span className="text-[#888]">Length of stay</span>
                  <p className="text-[#333]">{demoRow ? "9 days (demo)" : "—"}</p>
                </div>
              </CardContent>
            </Card>

            <Card className={cardClass}>
              <CardHeader>
                <CardTitle className="text-lg text-[#1a1a1a]">Presenting symptoms</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-inside list-disc space-y-1 text-sm text-[#333]">
                  <li>Shortness of breath</li>
                  <li>Cough</li>
                  <li>Fatigue</li>
                  <li>Low-grade fever</li>
                </ul>
                <p className="mt-2 text-xs text-[#888]">Demo copy — replace with extracted vitals when integrated.</p>
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card className={cardClass}>
                <CardHeader>
                  <CardTitle className="text-base text-[#1a1a1a]">Diagnosis</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-[#333]">
                  <p>
                    <span className="text-[#888]">Primary: </span>
                    {patient.discharge_summary?.diagnosis ?? demoRow?.reason}
                  </p>
                  <p className="text-xs text-[#888]">Secondary considerations reviewed per protocol.</p>
                </CardContent>
              </Card>
              <Card className={cardClass}>
                <CardHeader>
                  <CardTitle className="text-base text-[#1a1a1a]">Treatment summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="list-inside list-disc space-y-1 text-sm text-[#333]">
                    <li>Antibiotics</li>
                    <li>Oxygen therapy</li>
                    <li>IV fluids</li>
                    <li>Bronchodilators</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            <Card className={cardClass}>
              <CardHeader>
                <CardTitle className="text-lg text-[#1a1a1a]">Latest vitals & labs (demo)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                  {[
                    { label: "Temp", value: "37.1°C", ok: true },
                    { label: "BP", value: "128/84", ok: true },
                    { label: "HR", value: "76", ok: true },
                    { label: "O₂ Sat", value: "96", ok: false },
                    { label: "SpO₂", value: "96%", ok: false },
                  ].map((v) => (
                    <div key={v.label} className="rounded-lg border border-[#eee] bg-[#fafafa] p-3 text-center">
                      <div className="text-xs text-[#888]">{v.label}</div>
                      <div className="mt-1 text-lg font-bold text-[#1a1a1a]">{v.value}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="medical" className="space-y-4">
            {patient.discharge_summary ? (
              <Card className={cardClass}>
                <CardHeader>
                  <CardTitle className="text-lg text-[#1a1a1a]">Discharge & clinical notes</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>
                    <span className="text-[#888]">Diagnosis</span>
                    <p className="font-medium text-[#1a1a1a]">{patient.discharge_summary.diagnosis}</p>
                  </div>
                  {patient.discharge_summary.procedures && (
                    <div>
                      <span className="text-[#888]">Procedures</span>
                      <p>{patient.discharge_summary.procedures}</p>
                    </div>
                  )}
                  {patient.discharge_summary.instructions && (
                    <div>
                      <span className="text-[#888]">Instructions</span>
                      <p className="whitespace-pre-wrap text-[#333]">{patient.discharge_summary.instructions}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className={cardClass}>
                <CardContent className="p-8 text-center text-[#888]">No discharge summary on file.</CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="medications" className="space-y-4">
            {patient.medications.length === 0 ? (
              <Card className={cardClass}>
                <CardContent className="p-8 text-center text-[#888]">No medications listed.</CardContent>
              </Card>
            ) : (
              <Card className={cardClass}>
                <CardHeader>
                  <CardTitle>Medications ({patient.medications.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-2">
                    {patient.medications.map((m) => (
                      <div key={m.id} className="flex flex-wrap justify-between gap-2 rounded-lg border border-[#eee] bg-[#fafafa] p-3">
                        <span className="font-medium">{m.name}</span>
                        <span className="text-sm text-[#888]">
                          {m.dosage} · {m.frequency}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="appointments" className="space-y-4">
            {patient.appointments.length === 0 ? (
              <Card className={cardClass}>
                <CardContent className="p-8 text-center text-[#888]">No appointments scheduled.</CardContent>
              </Card>
            ) : (
              patient.appointments.map((ap) => (
                <Card key={ap.id} className={cardClass}>
                  <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="font-medium capitalize">{ap.appointment_type}</p>
                      {ap.notes && <p className="mt-1 text-sm text-[#888]">{ap.notes}</p>}
                    </div>
                    <div className="text-left sm:text-right">
                      <p className="text-sm">
                        {ap.scheduled_at ? new Date(ap.scheduled_at).toLocaleString() : "TBD"}
                      </p>
                      <Badge variant="outline" className="mt-1">
                        {ap.status}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="followup" className="space-y-4">
            {patient.questionnaire ? (
              <Card className={cardClass}>
                <CardHeader>
                  <CardTitle>Follow-up questionnaire</CardTitle>
                  <p className="text-sm text-[#888]">{patient.questionnaire.diagnosis_context}</p>
                </CardHeader>
                <CardContent className="space-y-3">
                  {patient.questionnaire.questions.map((q, idx) => (
                    <div key={q.id} className="rounded-lg border border-[#eee] bg-[#fafafa] p-3">
                      <Badge variant="outline" className="mb-1 text-xs">
                        {q.question_type}
                      </Badge>
                      <p className="font-medium">{q.text}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : (
              <Card className={cardClass}>
                <CardContent className="p-8 text-center text-[#888]">
                  No questionnaire yet — generated after Brain intake completes.
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="ai-calls" className="space-y-4">
            {voiceInteractions.length === 0 ? (
              <Card className={cardClass}>
                <CardContent className="p-8 text-center text-[#888]">
                  No AI voice calls yet. After intake, use &quot;Trigger AI follow-up call&quot; — completed Twilio
                  voice sessions appear here.
                </CardContent>
              </Card>
            ) : (
              voiceInteractions.map((inter) => (
                <Card key={inter.id} className={cardClass}>
                  <CardHeader className="pb-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <CardTitle className="text-base capitalize">
                        {inter.interaction_type} · {inter.channel}
                      </CardTitle>
                      <span className="text-sm text-[#888]">{new Date(inter.created_at).toLocaleString()}</span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {inter.responses?.length ? (
                      <div className="space-y-2">
                        {inter.responses.map((r, idx) => (
                          <div key={idx} className="rounded-lg border border-[#eee] bg-[#fafafa] p-3 text-sm">
                            <p className="text-[#888]">{r.question_text}</p>
                            <p className="mt-1 font-medium">{r.answer}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-[#888]">Call completed — no structured responses stored.</p>
                    )}
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="alerts" className="space-y-4">
            {patient.alerts.length === 0 ? (
              <Card className={cardClass}>
                <CardContent className="p-8 text-center text-[#888]">No alerts.</CardContent>
              </Card>
            ) : (
              patient.alerts.map((a) => (
                <Card key={a.id} className={cardClass}>
                  <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:justify-between">
                    <div>
                      <div className="flex flex-wrap gap-2">
                        <SeverityBadge severity={a.severity} />
                        <Badge variant="outline" className="border-[#ddd] bg-[#fafafa]">
                          {a.alert_type}
                        </Badge>
                      </div>
                      <p className="mt-2 text-sm text-[#333]">{a.message}</p>
                      <p className="text-xs text-[#888]">{new Date(a.created_at).toLocaleString()}</p>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>
        </Tabs>
      </div>

      <PatientDetailRightRail
        patient={patient}
        demoRow={demoRow}
        isLive={isLive}
        intakeBusy={intakeBusy}
        triggerBusy={triggerBusy}
        canTrigger={Boolean(workflowTargetId && (isLive ? workflowTargetId === apiPatient?.id : true))}
        onDischargeFile={handleDischargeFile}
        onTriggerFollowup={handleTrigger}
      />
    </div>
  );
}
