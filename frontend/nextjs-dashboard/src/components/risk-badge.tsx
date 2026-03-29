"use client";

import { Badge } from "@/components/ui/badge";

const riskColors: Record<string, string> = {
  low: "bg-green-50 text-green-800 border-green-200",
  medium: "bg-amber-50 text-amber-900 border-amber-200",
  high: "bg-orange-50 text-orange-900 border-orange-200",
  critical: "bg-red-50 text-red-800 border-red-200",
};

export function RiskBadge({ level }: { level: string | null }) {
  const l = (level || "unknown").toLowerCase();
  return (
    <Badge variant="outline" className={riskColors[l] || "border-[#ddd] bg-[#f5f5f5] text-[#555]"}>
      {l.toUpperCase()}
    </Badge>
  );
}
