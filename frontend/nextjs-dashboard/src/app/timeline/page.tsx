"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, PatientSummary, TimelineEntry } from "@/lib/api";

const eventTypeColors: Record<string, string> = {
  interaction: "bg-blue-50 text-blue-900 border-blue-200",
  alert: "bg-red-50 text-red-800 border-red-200",
  appointment: "bg-purple-50 text-purple-900 border-purple-200",
  audit: "border-[#ddd] bg-[#f5f5f5] text-[#555]",
};

const cardClass = "border border-[#e8e8e8] bg-white shadow-sm";

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
      } catch {
        /* ignore */
      } finally {
        setLoading(false);
      }
    };
    fetchTimeline();
    const interval = setInterval(fetchTimeline, 5000);
    return () => clearInterval(interval);
  }, [selectedPatientId]);

  return (
    <div className="space-y-6 px-7 py-6">
      <h1 className="text-[22px] font-bold text-[#1a1a1a]">Timeline</h1>

      <div className="flex flex-wrap items-center gap-4">
        <label className="text-sm text-[#888]">Patient:</label>
        <select
          value={selectedPatientId}
          onChange={(e) => setSelectedPatientId(e.target.value)}
          className="rounded-lg border border-[#e0e0e0] bg-[#fafafa] px-3 py-2 text-sm text-[#333] outline-none focus:ring-2 focus:ring-[#2d6a2e]/25"
        >
          <option value="">Select a patient</option>
          {patients.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {!selectedPatientId ? (
        <Card className={cardClass}>
          <CardContent className="p-8 text-center text-[#888]">Select a patient to view their timeline.</CardContent>
        </Card>
      ) : loading ? (
        <div className="p-8 text-center text-[#888]">Loading...</div>
      ) : entries.length === 0 ? (
        <Card className={cardClass}>
          <CardContent className="p-8 text-center text-[#888]">No events for this patient.</CardContent>
        </Card>
      ) : (
        <div className="relative space-y-0">
          <div className="absolute bottom-0 left-4 top-0 w-px bg-[#e8e8e8]" />
          {entries.map((entry) => (
            <div key={entry.id} className="relative pb-6 pl-10">
              <div className="absolute left-2.5 top-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white bg-[#ccc] shadow-sm" />
              <Card className={cardClass}>
                <CardContent className="p-4">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className={eventTypeColors[entry.event_type] || eventTypeColors.audit}>
                      {entry.event_type}
                    </Badge>
                    <span className="text-xs text-[#888]">
                      {entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}
                    </span>
                  </div>
                  <p className="text-sm text-[#333]">{entry.summary}</p>
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
