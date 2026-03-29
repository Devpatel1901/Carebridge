import { useState } from "react";

const patients = [
  { id: "1024587", name: "Sarah Chen", age: 42, gender: "F", reason: "Head Trauma", status: "High Risk", ward: "ICU-3" },
  { id: "7658321", name: "Omar Farooq", age: 40, gender: "M", reason: "Heart Failure", status: "Discharged", ward: "R-18" },
  { id: "2156793", name: "David Lee", age: 67, gender: "M", reason: "Pneumonia", status: "Recovering", ward: "G-12" },
  { id: "3298461", name: "Ayesha Begum", age: 87, gender: "F", reason: "Post-Op Recovery", status: "Stable", ward: "R-14" },
  { id: "4532109", name: "Habib Chowdhury", age: 28, gender: "M", reason: "Post-Op Recovery", status: "Stable", ward: "ICU-3" },
  { id: "5874632", name: "Nasreen Akter", age: 55, gender: "F", reason: "Post Traumatic Stress", status: "High Risk", ward: "ICU-2" },
];

const schedule = [
  { time: "09:00", title: "Patient Review: Sarah Chen", sub: "Sarah Chen", color: "#3d7c3f" },
  { time: "10:30", title: "Consult with Dr. Wong", sub: null, color: "#a0b8a0" },
  { time: "11:45", title: "Trauma Ward Rounds", sub: null, color: "#a0b8a0" },
  { time: "13:30", title: "Next Consultation: David Lee", sub: "David Lee", color: "#3d7c3f" },
  { time: "15:00", title: "Surgery: Post-op Review", sub: null, color: "#a0b8a0" },
];

const navItems = [
  { icon: "overview", label: "Overview" },
  { icon: "patients", label: "Patients", active: true },
  { icon: "appointments", label: "Appointments" },
  { icon: "reports", label: "Reports" },
  { icon: "messages", label: "Messages" },
  { icon: "staff", label: "Staff Members" },
];

const filters = ["All", "Recovery", "High Risk", "Stable", "Discharged"];

const statusColors = {
  "High Risk": { bg: "#fce4e4", text: "#c0392b" },
  "Discharged": { bg: "#fdebd0", text: "#b8860b" },
  "Recovering": { bg: "#dbe8fd", text: "#1a4fd6" },
  "Stable": { bg: "#d5f5e3", text: "#27ae60" },
};

function NavIcon({ type }) {
  const s = { width: 20, height: 20, stroke: "#6b7280", strokeWidth: 1.8, fill: "none" };
  const sw = type === "patients" ? "#fff" : "#6b7280";
  switch (type) {
    case "overview":
      return (<svg viewBox="0 0 24 24" style={{ ...s, stroke: sw }}><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></svg>);
    case "patients":
      return (<svg viewBox="0 0 24 24" style={{ ...s, stroke: sw }}><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 00-3-3.87" /><path d="M16 3.13a4 4 0 010 7.75" /></svg>);
    case "appointments":
      return (<svg viewBox="0 0 24 24" style={{ ...s, stroke: sw }}><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>);
    case "reports":
      return (<svg viewBox="0 0 24 24" style={{ ...s, stroke: sw }}><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></svg>);
    case "messages":
      return (<svg viewBox="0 0 24 24" style={{ ...s, stroke: sw }}><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>);
    case "staff":
      return (<svg viewBox="0 0 24 24" style={{ ...s, stroke: sw }}><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4-4v2" /><circle cx="12" cy="7" r="4" /></svg>);
    default:
      return null;
  }
}

export default function CareBridgeDashboard() {
  const [activeFilter, setActiveFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");

  const marchDays = [];
  const startDay = 0; // March 1 2026 is Sunday
  for (let i = 0; i < startDay; i++) marchDays.push(null);
  for (let i = 1; i <= 31; i++) marchDays.push(i);

  const filteredPatients = patients.filter((p) => {
    const matchesFilter = activeFilter === "All" || p.status === activeFilter ||
      (activeFilter === "Recovery" && p.status === "Recovering");
    const matchesSearch = searchQuery === "" ||
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.id.includes(searchQuery) ||
      p.reason.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif", background: "#f8f9fa", color: "#1a1a1a", fontSize: 14 }}>
      {/* Sidebar */}
      <aside style={{ width: 185, background: "#fff", borderRight: "1px solid #e8e8e8", display: "flex", flexDirection: "column", justifyContent: "space-between", flexShrink: 0 }}>
        <div>
          {/* Logo */}
          <div style={{ padding: "18px 20px", display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#2d6a2e", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
            </div>
            <span style={{ fontWeight: 700, fontSize: 16, color: "#1a1a1a" }}>CareBridge</span>
          </div>

          {/* Nav Items */}
          <nav style={{ marginTop: 8 }}>
            {navItems.map((item) => (
              <div
                key={item.label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "11px 16px",
                  margin: "2px 10px",
                  borderRadius: 10,
                  cursor: "pointer",
                  background: item.active ? "#2d6a2e" : "transparent",
                  color: item.active ? "#fff" : "#555",
                  fontSize: 13.5,
                  fontWeight: item.active ? 600 : 400,
                  transition: "background 0.15s",
                }}
              >
                <NavIcon type={item.icon} />
                <span>{item.label}</span>
              </div>
            ))}
          </nav>
        </div>

        {/* Bottom Nav */}
        <div style={{ padding: "0 10px 20px" }}>
          {["Settings", "Help / Support", "Logout"].map((item) => (
            <div
              key={item}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "10px 16px",
                margin: "1px 0",
                borderRadius: 10,
                cursor: "pointer",
                color: "#555",
                fontSize: 13.5,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="1.8">
                {item === "Settings" && <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></>}
                {item === "Help / Support" && <><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></>}
                {item === "Logout" && <><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></>}
              </svg>
              <span>{item}</span>
            </div>
          ))}
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Top Bar */}
        <header style={{ background: "#fff", borderBottom: "1px solid #e8e8e8", padding: "12px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div style={{ position: "relative", width: 360 }}>
            <svg style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)" }} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
            <input
              placeholder="Search patients, staff, or inventory..."
              style={{ width: "100%", padding: "9px 12px 9px 38px", border: "1px solid #e0e0e0", borderRadius: 10, fontSize: 13.5, outline: "none", color: "#888", background: "#fafafa" }}
            />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <div style={{ position: "relative", cursor: "pointer" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="1.8"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" /></svg>
              <div style={{ position: "absolute", top: -2, right: -2, width: 8, height: 8, borderRadius: "50%", background: "#e74c3c", border: "2px solid #fff" }} />
            </div>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="1.8"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: 4 }}>
              <div style={{ width: 36, height: 36, borderRadius: "50%", background: "linear-gradient(135deg, #8B7355 0%, #A0926B 100%)", border: "2px solid #e0d9c8" }} />
              <span style={{ fontWeight: 500, fontSize: 14, color: "#333" }}>Dr. Sarah</span>
            </div>
          </div>
        </header>

        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          {/* Patient Management Area */}
          <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
            {/* Header Row */}
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 }}>
              <div>
                <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: "#1a1a1a" }}>Patient Management</h1>
                <p style={{ fontSize: 13.5, color: "#888", margin: "4px 0 0" }}>Manage, monitor, and review patients</p>
              </div>
              <button style={{
                display: "flex", alignItems: "center", gap: 8,
                background: "#2d6a2e", color: "#fff",
                border: "none", borderRadius: 10, padding: "10px 20px",
                fontSize: 14, fontWeight: 500, cursor: "pointer"
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                Add Patient
              </button>
            </div>

            {/* Stat Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
              {[
                { label: "Total Patients", value: 8 },
                { label: "Emergency", value: 1 },
                { label: "Recovery", value: 1 },
                { label: "High-Risk", value: 2 },
              ].map((stat) => (
                <div key={stat.label} style={{
                  background: "#fff", border: "1px solid #e8e8e8",
                  borderRadius: 12, padding: "18px 22px"
                }}>
                  <div style={{ fontSize: 13, color: "#777", marginBottom: 6, fontWeight: 600 }}>{stat.label}</div>
                  <div style={{ fontSize: 32, fontWeight: 700, color: "#1a1a1a" }}>{stat.value}</div>
                </div>
              ))}
            </div>

            {/* Patient Table Card */}
            <div style={{ background: "#fff", border: "1px solid #e8e8e8", borderRadius: 14, overflow: "hidden" }}>
              {/* Search */}
              <div style={{ padding: "18px 22px 14px" }}>
                <div style={{ position: "relative" }}>
                  <svg style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)" }} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by name, ID, or condition..."
                    style={{ width: "100%", padding: "10px 14px 10px 40px", border: "1px solid #e0e0e0", borderRadius: 10, fontSize: 13.5, outline: "none", color: "#555", background: "#fafafa" }}
                  />
                </div>
              </div>

              {/* Filter Tabs */}
              <div style={{ padding: "0 22px 14px", display: "flex", gap: 6 }}>
                {filters.map((f) => (
                  <button
                    key={f}
                    onClick={() => setActiveFilter(f)}
                    style={{
                      padding: "6px 16px",
                      borderRadius: 20,
                      border: activeFilter === f ? "none" : "1px solid #ddd",
                      background: activeFilter === f ? "#2d6a2e" : "#fff",
                      color: activeFilter === f ? "#fff" : "#555",
                      fontSize: 13,
                      cursor: "pointer",
                      fontWeight: activeFilter === f ? 500 : 400,
                    }}
                  >
                    {f}
                  </button>
                ))}
              </div>

              {/* Table */}
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderTop: "1px solid #eee" }}>
                    {["Patient ID", "Patient Name", "Reason", "Status", "Ward Number", "Action"].map((h) => (
                      <th key={h} style={{ padding: "12px 22px", textAlign: "left", fontSize: 12.5, fontWeight: 600, color: "#888", borderBottom: "1px solid #eee" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredPatients.map((p) => (
                    <tr key={p.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
                      <td style={{ padding: "16px 22px", fontSize: 13.5, color: "#555" }}>{p.id}</td>
                      <td style={{ padding: "16px 22px" }}>
                        <div style={{ fontWeight: 600, fontSize: 14, color: "#1a1a1a" }}>{p.name}</div>
                        <div style={{ fontSize: 12.5, color: "#999", marginTop: 2 }}>{p.name} ({p.age}y, {p.gender})</div>
                      </td>
                      <td style={{ padding: "16px 22px", fontSize: 13.5, color: "#555" }}>{p.reason}</td>
                      <td style={{ padding: "16px 22px" }}>
                        <span style={{
                          display: "inline-block",
                          padding: "4px 14px",
                          borderRadius: 20,
                          fontSize: 12.5,
                          fontWeight: 500,
                          background: statusColors[p.status]?.bg || "#eee",
                          color: statusColors[p.status]?.text || "#555",
                        }}>
                          {p.status}
                        </span>
                      </td>
                      <td style={{ padding: "16px 22px", fontSize: 13.5, color: "#555" }}>{p.ward}</td>
                      <td style={{ padding: "16px 22px" }}>
                        <button style={{
                          padding: "7px 18px",
                          borderRadius: 8,
                          border: "none",
                          background: "#2d6a2e",
                          color: "#fff",
                          fontSize: 13,
                          cursor: "pointer",
                          fontWeight: 500,
                        }}>
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Sidebar - Appointments */}
          <aside style={{ width: 310, background: "#fff", borderLeft: "1px solid #e8e8e8", padding: "24px 22px", overflow: "auto", flexShrink: 0 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 18px", color: "#1a1a1a" }}>Upcoming Appointments</h2>

            {/* Calendar Header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>Today</span>
              <div style={{ display: "flex", gap: 8 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" style={{ cursor: "pointer" }}><polyline points="15 18 9 12 15 6" /></svg>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" style={{ cursor: "pointer" }}><polyline points="9 18 15 12 9 6" /></svg>
              </div>
            </div>

            {/* Calendar Grid */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 0, textAlign: "center", marginBottom: 6 }}>
                {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((d) => (
                  <div key={d} style={{ fontSize: 12, color: "#999", padding: "4px 0", fontWeight: 500 }}>{d}</div>
                ))}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 0, textAlign: "center" }}>
                {marchDays.map((day, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "7px 0",
                      fontSize: 13,
                      color: day === 28 ? "#fff" : day ? "#444" : "transparent",
                      fontWeight: day === 28 ? 600 : 400,
                      background: day === 28 ? "#2d6a2e" : "transparent",
                      borderRadius: day === 28 ? "50%" : 0,
                      width: day === 28 ? 32 : "auto",
                      height: day === 28 ? 32 : "auto",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      margin: day === 28 ? "0 auto" : 0,
                    }}
                  >
                    {day || ""}
                  </div>
                ))}
              </div>
            </div>

            {/* Today's Schedule */}
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 16px", color: "#1a1a1a" }}>Today's Schedule</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {schedule.map((item, i) => (
                <div key={i} style={{ display: "flex", gap: 12, padding: "10px 0" }}>
                  <div style={{ width: 3, borderRadius: 2, background: item.color, flexShrink: 0, minHeight: 36 }} />
                  <div>
                    <div style={{ fontSize: 13.5, fontWeight: 500, color: "#1a1a1a" }}>
                      {item.time} - {item.title}
                    </div>
                    {item.sub && (
                      <div style={{ fontSize: 12.5, color: "#999", marginTop: 3 }}>{item.sub}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
