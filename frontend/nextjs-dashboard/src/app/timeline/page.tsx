"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, PatientSummary, TimelineEntry } from "@/lib/api";

const eventTypeColors: Record<string, string> = {
  interaction: "bg-blue-900/50 text-blue-300 border-blue-700",
  alert: "bg-red-900/50 text-red-300 border-red-700",
  appointment: "bg-purple-900/50 text-purple-300 border-purple-700",
  audit: "bg-zinc-800 text-zinc-400 border-zinc-600",
};

export default function TimelinePage() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getPatients().then(setPatients).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedPatientId) {
      setEntries([]);
      return;
    }
    setLoading(true);
    const fetchTimeline = async () => {
      try {
        setEntries(await api.getTimeline(selectedPatientId));
      } catch { /* ignore */ }
      finally { setLoading(false); }
    };
    fetchTimeline();
    const interval = setInterval(fetchTimeline, 5000);
    return () => clearInterval(interval);
  }, [selectedPatientId]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Timeline</h1>

      <div className="flex items-center gap-4">
        <label className="text-zinc-400 text-sm">Patient:</label>
        <select
          value={selectedPatientId}
          onChange={(e) => setSelectedPatientId(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">Select a patient</option>
          {patients.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {!selectedPatientId ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-8 text-center text-zinc-500">
            Select a patient to view their timeline.
          </CardContent>
        </Card>
      ) : loading ? (
        <div className="p-8 text-center text-zinc-500">Loading...</div>
      ) : entries.length === 0 ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-8 text-center text-zinc-500">No events for this patient.</CardContent>
        </Card>
      ) : (
        <div className="relative space-y-0">
          <div className="absolute left-4 top-0 bottom-0 w-px bg-zinc-800" />
          {entries.map((entry) => (
            <div key={entry.id} className="relative pl-10 pb-6">
              <div className="absolute left-2.5 w-3 h-3 rounded-full bg-zinc-600 border-2 border-zinc-900 mt-1.5" />
              <Card className="bg-zinc-900 border-zinc-800">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className={eventTypeColors[entry.event_type] || eventTypeColors.audit}>
                      {entry.event_type}
                    </Badge>
                    <span className="text-zinc-500 text-xs">
                      {entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}
                    </span>
                  </div>
                  <p className="text-sm">{entry.summary}</p>
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
