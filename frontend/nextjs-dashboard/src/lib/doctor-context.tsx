"use client";

import { createContext, useContext, useEffect, useState } from "react";

export interface DoctorProfile {
  id: string;
  name: string;
  specialty: string;
  initials: string;
}

interface DoctorContextValue {
  doctor: DoctorProfile | null;
  setDoctor: (doctor: DoctorProfile | null) => void;
  logout: () => void;
}

const DoctorContext = createContext<DoctorContextValue>({
  doctor: null,
  setDoctor: () => {},
  logout: () => {},
});

const STORAGE_KEY = "carebridge_doctor";

export function DoctorProvider({ children }: { children: React.ReactNode }) {
  const [doctor, setDoctorState] = useState<DoctorProfile | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) setDoctorState(JSON.parse(stored));
    } catch {}
    setHydrated(true);
  }, []);

  const setDoctor = (d: DoctorProfile | null) => {
    setDoctorState(d);
    if (d) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(d));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  };

  const logout = () => setDoctor(null);

  if (!hydrated) return null;

  return (
    <DoctorContext.Provider value={{ doctor, setDoctor, logout }}>
      {children}
    </DoctorContext.Provider>
  );
}

export function useDoctor() {
  return useContext(DoctorContext);
}
