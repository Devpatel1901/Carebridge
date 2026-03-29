"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/severity-badge";
import { api, AlertItem } from "@/lib/api";

const cardClass = "border border-[#e8e8e8] bg-white shadow-sm";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAlerts = async () => {
    try {
      setAlerts(await api.getAlerts());
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAcknowledge = async (id: string) => {
    try {
      await api.acknowledgeAlert(id);
      fetchAlerts();
    } catch {
      /* ignore */
    }
  };

  const unacked = alerts.filter((a) => !a.acknowledged);
  const acked = alerts.filter((a) => a.acknowledged);

  return (
    <div className="space-y-6 px-7 py-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-[22px] font-bold text-[#1a1a1a]">Alerts</h1>
        <div className="flex gap-2">
          <Badge variant="outline" className="border-red-200 bg-red-50 text-red-800">
            {unacked.length} active
          </Badge>
          <Badge variant="outline" className="border-[#ddd] bg-[#fafafa] text-[#555]">
            {acked.length} acknowledged
          </Badge>
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-[#888]">Loading...</div>
      ) : alerts.length === 0 ? (
        <Card className={cardClass}>
          <CardContent className="p-8 text-center text-[#888]">No alerts. System is quiet.</CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {[...unacked, ...acked].map((alert) => (
            <Card
              key={alert.id}
              className={`${cardClass} ${
                !alert.acknowledged ? "border-red-200/80" : "opacity-90"
              }`}
            >
              <CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={alert.severity} />
                    <Badge variant="outline" className="border-[#ddd] bg-[#fafafa] text-[#333]">
                      {alert.alert_type}
                    </Badge>
                    {alert.patient_name && (
                      <Link href={`/patients/${alert.patient_id}`} className="text-sm text-[#2563eb] hover:underline">
                        {alert.patient_name}
                      </Link>
                    )}
                  </div>
                  <p className="text-sm text-[#333]">{alert.message}</p>
                  <p className="text-xs text-[#888]">
                    {alert.created_at ? new Date(alert.created_at).toLocaleString() : ""}
                  </p>
                </div>
                {!alert.acknowledged && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleAcknowledge(alert.id)}
                    className="shrink-0 rounded-[10px] border-[#e0e0e0] bg-[#fafafa] hover:bg-[#f0f0f0] sm:ml-4"
                  >
                    Acknowledge
                  </Button>
                )}
                {alert.acknowledged && (
                  <Badge variant="outline" className="shrink-0 border-green-200 bg-green-50 text-green-800 sm:ml-4">
                    Acknowledged
                  </Badge>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
