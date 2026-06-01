// Tiny API helper. Day 2+ will add the real Case/Party/SeizedItem calls here.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function getHealth() {
  const res = await fetch(`${API_BASE}/api/health/`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export { API_BASE };
