
const API_BASE = "/api";
const TOKEN_KEY = "access_token";
const ACTIVE_RESUME_KEY = "careerpilot.activeResumeId";
const ACTIVE_JOB_KEY = "careerpilot.activeJobId";

const Auth = {
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("resume_analyzer_token");
    localStorage.removeItem(ACTIVE_RESUME_KEY);
    localStorage.removeItem(ACTIVE_JOB_KEY);
  },
  isLoggedIn() {
    return !!this.getToken();
  },
};

async function apiRequest(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = Auth.getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    
  }

  if (!res.ok) {
    const message = (data && data.detail) || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

async function api(method, path, body = null) {
  const normalizedPath = path.startsWith("/api") ? path.slice("/api".length) : path;
  return apiRequest(normalizedPath, { method, body, auth: true });
}


async function apiUpload(path, formData) {
  const headers = {};
  const token = Auth.getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  let data = null;
  try {
    data = await res.json();
  } catch (_) { }

  if (!res.ok) {
    const message = (data && data.detail) || `Upload failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

function showMessage(el, text, type = "error") {
  el.textContent = text;
  el.className = `message ${type}`;
}

function hideMessage(el) {
  el.textContent = "";
  el.className = "message";
}

const AppState = {
  getResumeId() {
    const value = Number.parseInt(localStorage.getItem(ACTIVE_RESUME_KEY) || "", 10);
    return Number.isInteger(value) && value > 0 ? value : null;
  },
  setResumeId(value) {
    const parsed = Number.parseInt(value, 10);
    if (Number.isInteger(parsed) && parsed > 0) localStorage.setItem(ACTIVE_RESUME_KEY, String(parsed));
    else localStorage.removeItem(ACTIVE_RESUME_KEY);
  },
  getJobId() {
    const value = Number.parseInt(localStorage.getItem(ACTIVE_JOB_KEY) || "", 10);
    return Number.isInteger(value) && value > 0 ? value : null;
  },
  setJobId(value) {
    const parsed = Number.parseInt(value, 10);
    if (Number.isInteger(parsed) && parsed > 0) localStorage.setItem(ACTIVE_JOB_KEY, String(parsed));
    else localStorage.removeItem(ACTIVE_JOB_KEY);
  },
  clearJobId() {
    localStorage.removeItem(ACTIVE_JOB_KEY);
  },
};
