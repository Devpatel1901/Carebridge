"use client";

import { useRouter } from "next/navigation";
import { useDoctor, type DoctorProfile } from "@/lib/doctor-context";

const DEMO_DOCTORS: DoctorProfile[] = [
  {
    id: "doc-001",
    name: "Dr. Priya Patel",
    specialty: "Cardiology",
    initials: "PP",
  },
  {
    id: "doc-002",
    name: "Dr. Sara Chen",
    specialty: "Internal Medicine",
    initials: "SC",
  },
  {
    id: "doc-003",
    name: "Dr. James Wilson",
    specialty: "General Practice",
    initials: "JW",
  },
];

const AVATAR_COLORS: Record<string, string> = {
  "doc-001": "from-[#7c3aed] to-[#a78bfa]",
  "doc-002": "from-[#0369a1] to-[#38bdf8]",
  "doc-003": "from-[#15803d] to-[#4ade80]",
};

export default function LoginPage() {
  const { setDoctor } = useDoctor();
  const router = useRouter();

  const handleSelect = (doc: DoctorProfile) => {
    setDoctor(doc);
    router.push("/");
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f8f9fa]">
      <div className="w-full max-w-lg px-4">
        {/* Logo */}
        <div className="mb-10 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#2d6a2e] shadow-lg">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-[#1a1a1a]">CareBridge</h1>
          <p className="text-sm text-[#888]">Select your profile to continue</p>
        </div>

        {/* Doctor cards */}
        <div className="space-y-3">
          {DEMO_DOCTORS.map((doc) => (
            <button
              key={doc.id}
              onClick={() => handleSelect(doc)}
              className="group flex w-full items-center gap-4 rounded-xl border border-[#e8e8e8] bg-white px-5 py-4 text-left shadow-sm transition-all hover:border-[#2d6a2e] hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[#2d6a2e]/30"
            >
              {/* Avatar */}
              <div
                className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${AVATAR_COLORS[doc.id]} text-sm font-bold text-white shadow`}
              >
                {doc.initials}
              </div>

              {/* Info */}
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-[#1a1a1a]">{doc.name}</p>
                <p className="text-sm text-[#888]">{doc.specialty}</p>
              </div>

              {/* Arrow */}
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#ccc"
                strokeWidth="2"
                className="shrink-0 transition-colors group-hover:stroke-[#2d6a2e]"
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          ))}
        </div>

        <p className="mt-8 text-center text-xs text-[#bbb]">
          Demo mode — no password required
        </p>
      </div>
    </div>
  );
}
