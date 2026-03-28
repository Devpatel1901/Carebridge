"use client";

import { Badge } from "@/components/ui/badge";

const severityColors: Record<string, string> = {
  low: "bg-blue-900/50 text-blue-300 border-blue-700",
  medium: "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  high: "bg-orange-900/50 text-orange-300 border-orange-700",
  critical: "bg-red-900/50 text-red-300 border-red-700",
};

export function SeverityBadge({ severity }: { severity: string }) {
  const s = severity.toLowerCase();
  return (
    <Badge variant="outline" className={severityColors[s] || "bg-zinc-800 text-zinc-400 border-zinc-600"}>
      {s.toUpperCase()}
    </Badge>
  );
}
