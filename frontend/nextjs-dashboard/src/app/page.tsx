"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Patients</h1>
        <Badge variant="outline" className="text-zinc-400">
          {patients.length} total
        </Badge>
      </div>

      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-zinc-500">Loading...</div>
          ) : patients.length === 0 ? (
            <div className="p-8 text-center text-zinc-500">
              No patients yet. Run <code className="text-zinc-300">python scripts/seed_data.py</code> to add one.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800 hover:bg-transparent">
                  <TableHead className="text-zinc-400">Name</TableHead>
                  <TableHead className="text-zinc-400">Phone</TableHead>
                  <TableHead className="text-zinc-400">Status</TableHead>
                  <TableHead className="text-zinc-400">Risk Level</TableHead>
                  <TableHead className="text-zinc-400">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {patients.map((p) => (
                  <TableRow key={p.id} className="border-zinc-800 hover:bg-zinc-800/50">
                    <TableCell>
                      <Link href={`/patients/${p.id}`} className="text-blue-400 hover:underline font-medium">
                        {p.name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-zinc-400">{p.phone}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-600">
                        {p.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <RiskBadge level={p.risk_level} />
                    </TableCell>
                    <TableCell className="text-zinc-500 text-sm">
                      {p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
