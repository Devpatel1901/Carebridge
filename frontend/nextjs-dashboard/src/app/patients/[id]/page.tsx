"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/risk-badge";
import { SeverityBadge } from "@/components/severity-badge";
import { api, PatientDetail } from "@/lib/api";

export default function PatientDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [patient, setPatient] = useState<PatientDetail | null>(null);
  const [triggering, setTriggering] = useState(false);

  const fetchPatient = async () => {
    try {
      setPatient(await api.getPatient(id));
    } catch { /* ignore */ }
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
    } catch { /* ignore */ }
    setTriggering(false);
  };

  if (!patient) return <div className="p-8 text-zinc-500">Loading patient...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{patient.name}</h1>
          <p className="text-zinc-400 mt-1">{patient.phone} {patient.email && `· ${patient.email}`}</p>
        </div>
        <div className="flex items-center gap-3">
          <RiskBadge level={patient.risk_level} />
          <Button variant="outline" onClick={handleTriggerFollowup} disabled={triggering} className="bg-zinc-800 border-zinc-700 hover:bg-zinc-700">
            {triggering ? "Sending..." : "Trigger Follow-up SMS"}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="bg-zinc-800 border border-zinc-700">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="interactions">Interactions</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="appointments">Appointments</TabsTrigger>
          <TabsTrigger value="questionnaire">Questionnaire</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {patient.discharge_summary && (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg">Discharge Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="text-zinc-400 text-sm">Diagnosis</span>
                  <p className="font-medium">{patient.discharge_summary.diagnosis}</p>
                </div>
                {patient.discharge_summary.procedures && (
                  <div>
                    <span className="text-zinc-400 text-sm">Procedures</span>
                    <p>{patient.discharge_summary.procedures}</p>
                  </div>
                )}
                {patient.discharge_summary.instructions && (
                  <div>
                    <span className="text-zinc-400 text-sm">Instructions</span>
                    <p className="text-sm text-zinc-300 whitespace-pre-wrap">{patient.discharge_summary.instructions}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {patient.medications.length > 0 && (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg">Medications ({patient.medications.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2">
                  {patient.medications.map((m) => (
                    <div key={m.id} className="flex items-center justify-between p-3 bg-zinc-800 rounded-lg">
                      <span className="font-medium">{m.name}</span>
                      <span className="text-zinc-400 text-sm">{m.dosage} · {m.frequency}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="interactions" className="space-y-4">
          {patient.interactions.length === 0 ? (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="p-8 text-center text-zinc-500">
                No interactions yet.
              </CardContent>
            </Card>
          ) : (
            patient.interactions.map((inter) => (
              <Card key={inter.id} className="bg-zinc-900 border-zinc-800">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base capitalize">{inter.interaction_type} via {inter.channel}</CardTitle>
                    <span className="text-zinc-500 text-sm">{new Date(inter.created_at).toLocaleString()}</span>
                  </div>
                </CardHeader>
                <CardContent>
                  {inter.responses ? (
                    <div className="space-y-2">
                      {inter.responses.map((r, idx) => (
                        <div key={idx} className="p-3 bg-zinc-800 rounded-lg">
                          <p className="text-zinc-400 text-sm">{r.question_text}</p>
                          <p className="font-medium mt-1">{r.answer}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-zinc-500">No response data</p>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          {patient.alerts.length === 0 ? (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="p-8 text-center text-zinc-500">No alerts.</CardContent>
            </Card>
          ) : (
            patient.alerts.map((a) => (
              <Card key={a.id} className="bg-zinc-900 border-zinc-800">
                <CardContent className="p-4 flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={a.severity} />
                      <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-600">{a.alert_type}</Badge>
                    </div>
                    <p className="text-sm mt-2">{a.message}</p>
                    <p className="text-zinc-500 text-xs">{new Date(a.created_at).toLocaleString()}</p>
                  </div>
                  {a.acknowledged && (
                    <Badge variant="outline" className="bg-green-900/30 text-green-400 border-green-700">Acknowledged</Badge>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="appointments" className="space-y-4">
          {patient.appointments.length === 0 ? (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="p-8 text-center text-zinc-500">No appointments.</CardContent>
            </Card>
          ) : (
            patient.appointments.map((ap) => (
              <Card key={ap.id} className="bg-zinc-900 border-zinc-800">
                <CardContent className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium capitalize">{ap.appointment_type}</p>
                    {ap.notes && <p className="text-zinc-400 text-sm mt-1">{ap.notes}</p>}
                  </div>
                  <div className="text-right">
                    <p className="text-sm">{ap.scheduled_at ? new Date(ap.scheduled_at).toLocaleString() : "TBD"}</p>
                    <Badge variant="outline" className="mt-1 bg-zinc-800 text-zinc-300 border-zinc-600">{ap.status}</Badge>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="questionnaire" className="space-y-4">
          {patient.questionnaire ? (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg">Disease-Specific Follow-up Questions</CardTitle>
                <p className="text-zinc-400 text-sm">Context: {patient.questionnaire.diagnosis_context}</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {patient.questionnaire.questions.map((q, idx) => (
                    <div key={q.id} className="p-3 bg-zinc-800 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="bg-zinc-700 text-zinc-300 border-zinc-600 text-xs">{q.question_type}</Badge>
                        <span className="text-zinc-400 text-xs">Q{idx + 1}</span>
                      </div>
                      <p className="font-medium">{q.text}</p>
                      {q.relevance && <p className="text-zinc-500 text-xs mt-1">{q.relevance}</p>}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="p-8 text-center text-zinc-500">No questionnaire generated yet.</CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
