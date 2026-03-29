/** Nav icons — stroke is white when `active` (on green background), else gray. */

export function NavIconOverview({ active }: { active?: boolean }) {
  const stroke = active ? "#fff" : "#6b7280";
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

export function NavIconPatients({ active }: { active?: boolean }) {
  const stroke = active ? "#fff" : "#6b7280";
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
      <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 00-3-3.87" />
      <path d="M16 3.13a4 4 0 010 7.75" />
    </svg>
  );
}

export function NavIconAppointments({ active }: { active?: boolean }) {
  const stroke = active ? "#fff" : "#6b7280";
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

export function NavIconReports({ active }: { active?: boolean }) {
  const stroke = active ? "#fff" : "#6b7280";
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

export function NavIconMessages({ active }: { active?: boolean }) {
  const stroke = active ? "#fff" : "#6b7280";
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
    </svg>
  );
}

export function NavIconStaff({ active }: { active?: boolean }) {
  const stroke = active ? "#fff" : "#6b7280";
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4-4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}
