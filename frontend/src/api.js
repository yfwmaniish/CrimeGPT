// API client for CrimeGPT. Token auth: the token is stored in localStorage and
// sent as `Authorization: Token <token>` on every request.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const TOKEN_KEY = "crimegpt_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// Error carrying the HTTP status + parsed body, so the UI can react (e.g. 403).
export class ApiError extends Error {
  constructor(status, data) {
    super(typeof data === "string" ? data : data?.detail || "Request failed");
    this.status = status;
    this.data = data;
  }
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (auth && token) headers["Authorization"] = `Token ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export async function login(username, password) {
  const data = await request("/api/auth/login/", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
  setToken(data.token);
  return data; // { token, username, role, role_display, can_generate_documents }
}

export function logout() {
  setToken(null);
}

export function me() {
  return request("/api/auth/me/");
}

export function createCase(payload) {
  return request("/api/cases/", { method: "POST", body: payload });
}

export function generateSeizureReceipt(caseId) {
  return request(`/api/cases/${caseId}/documents/seizure/`, { method: "POST" });
}

// Generate any document type, optionally as PDF. docType is the URL segment
// (seizure, remand, custody, medical, panchanama, faceid, chargesheet).
export function generateDocument(caseId, docType, asPdf = false) {
  const q = asPdf ? "?format=pdf" : "";
  return request(`/api/cases/${caseId}/documents/${docType}/${q}`, { method: "POST" });
}

export function suggestSections(caseId, n = 6) {
  return request(`/api/cases/${caseId}/suggest-sections/?n=${n}`, { method: "POST" });
}

export function confirmSection(caseId, caseSectionId, confirmed) {
  return request(`/api/cases/${caseId}/sections/${caseSectionId}/confirm/`, {
    method: "POST",
    body: { confirmed },
  });
}

export function getDiary(caseId) {
  return request(`/api/cases/${caseId}/diary/`);
}

export function addDiaryEvent(caseId, { event_type, description, timestamp }) {
  const body = { event_type, description };
  if (timestamp) body.timestamp = timestamp;
  return request(`/api/cases/${caseId}/diary/`, { method: "POST", body });
}

export { API_BASE };
