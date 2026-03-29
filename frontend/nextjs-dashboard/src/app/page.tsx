"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RiskBadge } from "@/components/risk-badge";
import { Badge } from "@/components/ui/badge";
import { api, PatientSummary } from "@/lib/api";
import { PatientManagementHeader, PatientStatCards } from "@/components/carebridge/patient-management-static";

export default function PatientsPage() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPatients = async () => {
    try {
      const data = await api.getPatients();
      setPatients(data);
    } catch {
      /* service may not be up yet */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
    const interval = setInterval(fetchPatients, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 px-4 py-5 sm:px-6 sm:py-6 lg:px-7">
      <PatientManagementHeader />
      <PatientStatCards />

      <div className="overflow-hidden rounded-[14px] border border-[#e8e8e8] bg-white shadow-sm">
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-[#888]">Loading...</div>
          ) : patients.length === 0 ? (
            <div className="p-8 text-center text-[#888]">
              No patients yet. Run <code className="rounded bg-[#f5f5f5] px-1.5 py-0.5 text-[#333]">python scripts/seed_data.py</code>{" "}
              to add one.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-[#eee] hover:bg-transparent">
                  <TableHead className="text-[12.5px] font-semibold text-[#888]">Name</TableHead>
                  <TableHead className="text-[12.5px] font-semibold text-[#888]">Phone</TableHead>
                  <TableHead className="text-[12.5px] font-semibold text-[#888]">Status</TableHead>
                  <TableHead className="text-[12.5px] font-semibold text-[#888]">Risk Level</TableHead>
                  <TableHead className="text-[12.5px] font-semibold text-[#888]">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {patients.map((p) => (
                  <TableRow
                    key={p.id}
                    className="border-[#f0f0f0] transition-colors duration-150 hover:bg-[#fafafa]"
                  >
                    <TableCell>
                      <Link
                        href={`/patients/${p.id}`}
                        className="font-semibold text-[#2563eb] hover:underline"
                      >
                        {p.name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-[13.5px] text-[#555]">{p.phone}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="border-[#ddd] bg-[#fafafa] text-[#333]">
                        {p.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <RiskBadge level={p.risk_level} />
                    </TableCell>
                    <TableCell className="text-sm text-[#888]">
                      {p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </div>
    </div>
  );
}
