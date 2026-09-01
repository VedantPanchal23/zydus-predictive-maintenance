import axios from "axios";

const api = axios.create({
  baseURL: "/",
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: attach JWT Bearer token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("zydus_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 unauthorized
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const isAuthEndpoint = error.config.url.includes("/auth/login");
      if (!isAuthEndpoint) {
        localStorage.removeItem("zydus_token");
        localStorage.removeItem("zydus_user");
        if (window.location.pathname !== "/login") {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// -- Auth Endpoints ------------------------------------------
export async function loginUser(username, password) {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  const res = await api.post("/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return res.data;
}

export async function getCurrentUser() {
  const res = await api.get("/auth/me");
  return res.data;
}

// -- Equipment & Telemetry Endpoints -------------------------
export async function getEquipmentList() {
  const res = await api.get("/api/equipment");
  return res.data;
}

export async function getEquipmentDetail(id) {
  const res = await api.get(`/api/equipment/${id}`);
  return res.data;
}

export async function getEquipmentSensors(id, limit = 100) {
  const res = await api.get(`/api/equipment/${id}/sensors?limit=${limit}`);
  return res.data;
}

export async function getEquipmentPrediction(id) {
  const res = await api.get(`/api/equipment/${id}/prediction`);
  return res.data;
}

export async function getEquipmentHistory(id, limit = 50) {
  const res = await api.get(`/api/equipment/${id}/history?limit=${limit}`);
  return res.data;
}

export async function getDashboardSummary() {
  const res = await api.get("/api/dashboard/summary");
  return res.data;
}

// -- Alerts & Work Orders -----------------------------------
export async function getAlerts() {
  const res = await api.get("/api/alerts");
  return res.data;
}

export async function acknowledgeAlert(alertId) {
  const res = await api.patch(`/api/alerts/${alertId}/acknowledge`);
  return res.data;
}

export async function getWorkOrders() {
  const res = await api.get("/api/workorders");
  return res.data;
}

export async function completeWorkOrder(workOrderId, eSignData) {
  const res = await api.patch(`/api/workorders/${workOrderId}/complete`, eSignData);
  return res.data;
}

// -- 21 CFR Part 11 Audit Trail ------------------------------
export async function getAuditLogs(params = {}) {
  const res = await api.get("/api/audit-logs", { params });
  return res.data;
}

export async function verifyAuditChain(limit = 1000) {
  const res = await api.get(`/api/audit-logs/verify?limit=${limit}`);
  return res.data;
}

export async function exportGxPCertificate() {
  const res = await api.get("/api/audit-logs/export/certificate");
  return res.data;
}

// -- Telemetry DLQ ------------------------------------------
export async function getDlqRecords(limit = 100) {
  const res = await api.get(`/api/telemetry/dlq?limit=${limit}`);
  return res.data;
}

// -- Chaos & Fault Injection --------------------------------
export async function injectChaosFault(payload) {
  const res = await api.post("/api/chaos/inject", payload);
  return res.data;
}
