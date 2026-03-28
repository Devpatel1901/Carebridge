"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/severity-badge";
import { api, AlertItem } from "@/lib/api";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAlerts = async () => {
    try {
      setAlerts(await api.getAlerts());
    } catch { /* ignore */ }
    finally { setLoading(false); }
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
    } catch { /* ignore */ }
  };

  const unacked = alerts.filter((a) => !a.acknowledged);
  const acked = alerts.filter((a) => a.acknowledged);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Alerts</h1>
        <div className="flex gap-2">
          <Badge variant="outline" className="bg-red-900/30 text-red-300 border-red-700">
            {unacked.length} active
          </Badge>
          <Badge variant="outline" className="bg-zinc-800 text-zinc-400 border-zinc-600">
            {acked.length} acknowledged
          </Badge>
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-zinc-500">Loading...</div>
      ) : alerts.length === 0 ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-8 text-center text-zinc-500">
            No alerts. System is quiet.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {[...unacked, ...acked].map((alert) => (
            <Card
              key={alert.id}
              className={`border ${
                !alert.acknowledged
                  ? "bg-zinc-900 border-red-900/50"
                  : "bg-zinc-900/50 border-zinc-800 opacity-70"
              }`}
            >
              <CardContent className="p-4 flex items-start justify-between">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <SeverityBadge severity={alert.severity} />
                    <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-600">
                      {alert.alert_type}
                    </Badge>
                    {alert.patient_name && (
                      <Link href={`/patients/${alert.patient_id}`} className="text-blue-400 hover:underline text-sm">
                        {alert.patient_name}
                      </Link>
                    )}
                  </div>
                  <p className="text-sm">{alert.message}</p>
                  <p className="text-zinc-500 text-xs">
                    {alert.created_at ? new Date(alert.created_at).toLocaleString() : ""}
                  </p>
                </div>
                {!alert.acknowledged && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleAcknowledge(alert.id)}
                    className="bg-zinc-800 border-zinc-700 hover:bg-zinc-700 ml-4"
                  >
                    Acknowledge
                  </Button>
                )}
                {alert.acknowledged && (
                  <Badge variant="outline" className="bg-green-900/30 text-green-400 border-green-700 ml-4">
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
