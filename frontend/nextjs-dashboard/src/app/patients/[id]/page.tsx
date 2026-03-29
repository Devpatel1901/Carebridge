"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/risk-badge";
import { SeverityBadge } from "@/components/severity-badge";
import { api, PatientDetail } from "@/lib/api";
import { AppointmentsSidebar } from "@/components/carebridge/appointments-sidebar";
import {
  PatientManagementHeader,
  PatientStatCards,
  PatientStaticTableCard,
} from "@/components/carebridge/patient-management-static";

const tabListClass =
  "inline-flex h-auto w-full flex-wrap gap-1 rounded-lg bg-[#f0f0f0] p-1 text-[#555] sm:w-fit";
const tabTriggerClass =
  "rounded-md px-3 py-2 text-sm font-medium text-[#555] transition-colors hover:text-[#1a1a1a] data-active:bg-[#2d6a2e] data-active:text-white data-active:shadow-sm";

const cardClass = "border border-[#e8e8e8] bg-white shadow-sm";

export default function PatientDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [patient, setPatient] = useState<PatientDetail | null>(null);
  const [triggering, setTriggering] = useState(false);

  const fetchPatient = async () => {
    try {
      setPatient(await api.getPatient(id));
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    fetchPatient();
    const interval = setInterval(fetchPatient, 5000);
    return () => clearInterval(interval);
  }, [id]);

  const handleTriggerFollowup = async () => {
    setTriggering(true);
    try {
      await api.triggerFollowup(id);
    } catch {
      /* ignore */
    }
    setTriggering(false);
  };

  if (!patient) {
    return (
      <div className="flex min-h-[50vh] flex-1 flex-col lg:min-h-0 lg:flex-row lg:items-stretch">
        <div className="order-1 flex flex-1 items-center justify-center px-4 py-10 text-[#888] sm:px-7 sm:py-12">
          Loading patient...
        </div>
        <AppointmentsSidebar />
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col lg:flex-row lg:items-stretch">
      <div className="order-1 min-w-0 flex-1 space-y-6 px-4 py-5 sm:px-6 sm:py-6 lg:min-h-0 lg:overflow-y-auto lg:px-7">
        <PatientManagementHeader />
        <PatientStatCards />
        <PatientStaticTableCard highlightPatientId={id} />

        <section className="space-y-4 pt-2">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-xl font-bold text-[#1a1a1a]">{patient.name}</h2>
              <p className="mt-1 text-[13.5px] text-[#888]">
                {patient.phone} {patient.email && `· ${patient.email}`}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <RiskBadge level={patient.risk_level} />
              <Button
                variant="outline"
                onClick={handleTriggerFollowup}
                disabled={triggering}
                className="rounded-[10px] border-[#e0e0e0] bg-[#fafafa] text-[#1a1a1a] hover:bg-[#f0f0f0]"
              >
                {triggering ? "Sending..." : "Trigger Follow-up SMS"}
              </Button>
            </div>
          </div>

          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList className={tabListClass}>
              <TabsTrigger value="overview" className={tabTriggerClass}>
                Overview
              </TabsTrigger>
              <TabsTrigger value="interactions" className={tabTriggerClass}>
                Interactions
              </TabsTrigger>
              <TabsTrigger value="alerts" className={tabTriggerClass}>
                Alerts
              </TabsTrigger>
              <TabsTrigger value="appointments" className={tabTriggerClass}>
                Appointments
              </TabsTrigger>
              <TabsTrigger value="questionnaire" className={tabTriggerClass}>
                Questionnaire
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4">
              {patient.discharge_summary && (
                <Card className={cardClass}>
                  <CardHeader>
                    <CardTitle className="text-lg text-[#1a1a1a]">Discharge Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <span className="text-sm text-[#888]">Diagnosis</span>
                      <p className="font-medium text-[#1a1a1a]">{patient.discharge_summary.diagnosis}</p>
                    </div>
                    {patient.discharge_summary.procedures && (
                      <div>
                        <span className="text-sm text-[#888]">Procedures</span>
                        <p className="text-[#333]">{patient.discharge_summary.procedures}</p>
                      </div>
                    )}
                    {patient.discharge_summary.instructions && (
                      <div>
                        <span className="text-sm text-[#888]">Instructions</span>
                        <p className="mt-1 whitespace-pre-wrap text-sm text-[#333]">
                          {patient.discharge_summary.instructions}
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {patient.medications.length > 0 && (
                <Card className={cardClass}>
                  <CardHeader>
                    <CardTitle className="text-lg text-[#1a1a1a]">
                      Medications ({patient.medications.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-2">
                      {patient.medications.map((m) => (
                        <div
                          key={m.id}
                          className="flex items-center justify-between rounded-lg border border-[#eee] bg-[#fafafa] p-3"
                        >
                          <span className="font-medium text-[#1a1a1a]">{m.name}</span>
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

            <TabsContent value="interactions" className="space-y-4">
              {patient.interactions.length === 0 ? (
                <Card className={cardClass}>
                  <CardContent className="p-8 text-center text-[#888]">No interactions yet.</CardContent>
                </Card>
              ) : (
                patient.interactions.map((inter) => (
                  <Card key={inter.id} className={cardClass}>
                    <CardHeader className="pb-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <CardTitle className="text-base capitalize text-[#1a1a1a]">
                          {inter.interaction_type} via {inter.channel}
                        </CardTitle>
                        <span className="text-sm text-[#888]">{new Date(inter.created_at).toLocaleString()}</span>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {inter.responses ? (
                        <div className="space-y-2">
                          {inter.responses.map((r, idx) => (
                            <div key={idx} className="rounded-lg border border-[#eee] bg-[#fafafa] p-3">
                              <p className="text-sm text-[#888]">{r.question_text}</p>
                              <p className="mt-1 font-medium text-[#1a1a1a]">{r.answer}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-[#888]">No response data</p>
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
                    <CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-start sm:justify-between">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <SeverityBadge severity={a.severity} />
                          <Badge
                            variant="outline"
                            className="border-[#ddd] bg-[#fafafa] text-[#333]"
                          >
                            {a.alert_type}
                          </Badge>
                        </div>
                        <p className="mt-2 text-sm text-[#333]">{a.message}</p>
                        <p className="text-xs text-[#888]">{new Date(a.created_at).toLocaleString()}</p>
                      </div>
                      {a.acknowledged && (
                        <Badge
                          variant="outline"
                          className="shrink-0 border-green-200 bg-green-50 text-green-800"
                        >
                          Acknowledged
                        </Badge>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>

            <TabsContent value="appointments" className="space-y-4">
              {patient.appointments.length === 0 ? (
                <Card className={cardClass}>
                  <CardContent className="p-8 text-center text-[#888]">No appointments.</CardContent>
                </Card>
              ) : (
                patient.appointments.map((ap) => (
                  <Card key={ap.id} className={cardClass}>
                    <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="font-medium capitalize text-[#1a1a1a]">{ap.appointment_type}</p>
                        {ap.notes && <p className="mt-1 text-sm text-[#888]">{ap.notes}</p>}
                      </div>
                      <div className="text-left sm:text-right">
                        <p className="text-sm text-[#333]">
                          {ap.scheduled_at ? new Date(ap.scheduled_at).toLocaleString() : "TBD"}
                        </p>
                        <Badge variant="outline" className="mt-1 border-[#ddd] bg-[#fafafa] text-[#333]">
                          {ap.status}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>

            <TabsContent value="questionnaire" className="space-y-4">
              {patient.questionnaire ? (
                <Card className={cardClass}>
                  <CardHeader>
                    <CardTitle className="text-lg text-[#1a1a1a]">Disease-Specific Follow-up Questions</CardTitle>
                    <p className="text-sm text-[#888]">Context: {patient.questionnaire.diagnosis_context}</p>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {patient.questionnaire.questions.map((q, idx) => (
                        <div key={q.id} className="rounded-lg border border-[#eee] bg-[#fafafa] p-3">
                          <div className="mb-1 flex flex-wrap items-center gap-2">
                            <Badge variant="outline" className="border-[#ddd] bg-white text-xs text-[#555]">
                              {q.question_type}
                            </Badge>
                            <span className="text-xs text-[#888]">Q{idx + 1}</span>
                          </div>
                          <p className="font-medium text-[#1a1a1a]">{q.text}</p>
                          {q.relevance && <p className="mt-1 text-xs text-[#888]">{q.relevance}</p>}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card className={cardClass}>
                  <CardContent className="p-8 text-center text-[#888]">No questionnaire generated yet.</CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </section>
      </div>

      <AppointmentsSidebar />
    </div>
  );
}
