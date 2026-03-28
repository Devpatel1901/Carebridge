"use client";

import { Badge } from "@/components/ui/badge";

const riskColors: Record<string, string> = {
  low: "bg-green-900/50 text-green-300 border-green-700",
  medium: "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  high: "bg-orange-900/50 text-orange-300 border-orange-700",
  critical: "bg-red-900/50 text-red-300 border-red-700",
};

export function RiskBadge({ level }: { level: string | null }) {
  const l = (level || "unknown").toLowerCase();
  return (
    <Badge variant="outline" className={riskColors[l] || "bg-zinc-800 text-zinc-400 border-zinc-600"}>
      {l.toUpperCase()}
    </Badge>
  );
}
