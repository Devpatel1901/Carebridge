"use client";

import { Badge } from "@/components/ui/badge";

const severityColors: Record<string, string> = {
  low: "bg-blue-50 text-blue-900 border-blue-200",
  medium: "bg-amber-50 text-amber-900 border-amber-200",
  high: "bg-orange-50 text-orange-900 border-orange-200",
  critical: "bg-red-50 text-red-800 border-red-200",
};

export function SeverityBadge({ severity }: { severity: string }) {
  const s = severity.toLowerCase();
  return (
    <Badge variant="outline" className={severityColors[s] || "border-[#ddd] bg-[#f5f5f5] text-[#555]"}>
      {s.toUpperCase()}
    </Badge>
  );
}
