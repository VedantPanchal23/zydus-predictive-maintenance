import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL;

const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }

    return Promise.reject(error);
  },
);

export const login = (username, password) =>
  api.post('/auth/login', new URLSearchParams({ username, password }), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

export const getEquipment = () => api.get('/api/equipment');
export const getEquipmentById = (id) => api.get(`/api/equipment/${id}`);
export const getEquipmentSensors = (id) => api.get(`/api/equipment/${id}/sensors`);
export const getEquipmentPrediction = (id) => api.get(`/api/equipment/${id}/prediction`);
export const getEquipmentHistory = (id) => api.get(`/api/equipment/${id}/history`);

export const getAlerts = (params) => api.get('/api/alerts', { params });
export const acknowledgeAlert = (id) => api.patch(`/api/alerts/${id}/acknowledge`);

export const getWorkOrders = (params) => api.get('/api/workorders', { params });
export const completeWorkOrder = (id) => api.patch(`/api/workorders/${id}/complete`);

export const getLogs = (params) => api.get('/api/logs', { params });
export const getDashboardSummary = () => api.get('/api/dashboard/summary');

export default api;
