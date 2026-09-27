import axios from 'axios';

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
if (import.meta.env.PROD && !configuredApiUrl) {
  throw new Error('VITE_API_URL must be configured for production builds.');
}
const API_BASE_URL = configuredApiUrl || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const guestApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth endpoints
export const authAPI = {
  login: (email, password) => api.post('/api/auth/login', { email, password }),
};

// Dashboard endpoints
export const dashboardAPI = {
  getManager: () => api.get('/api/dashboard/manager'),
  getFrontDesk: () => api.get('/api/dashboard/front-desk'),
  getDepartment: () => api.get('/api/dashboard/department'),
  getStaff: () => api.get('/api/dashboard/staff'),
};

// Department catalog
export const departmentsAPI = {
  getAll: () => api.get('/api/departments'),
};

// Room and front-desk actions
export const frontDeskAPI = {
  getRooms: () => api.get('/api/rooms'),
  getRoomStatusTransitions: () => api.get('/api/rooms/status-transitions'),
  updateRoomStatus: (id, status) => api.patch(`/api/rooms/${id}/status`, { status }),
  checkIn: (bookingId) => api.post(`/api/front-desk/bookings/${bookingId}/check-in`),
  checkOut: (bookingId) => api.post(`/api/front-desk/bookings/${bookingId}/check-out`),
};

// Forecast endpoints
export const forecastAPI = {
  getOccupancy: (days = 7) => api.get(`/api/forecast/occupancy?days=${days}`),
  getWorkload: () => api.get('/api/forecast/workload'),
  getDepartment: (days = 7) => api.get(`/api/forecast/department?days=${days}`),
};

// Recommendations endpoints
export const recommendationsAPI = {
  getAll: (status = null) => api.get('/api/recommendations', { params: { status } }),
  generate: () => api.post('/api/recommendations/generate'),
  approve: (id) => api.post(`/api/recommendations/${id}/approve`),
  reject: (id, data) => api.post(`/api/recommendations/${id}/reject`, data),
  modify: (id, data) => api.post(`/api/recommendations/${id}/modify`, data),
  recordOutcome: (id, data) => api.post(`/api/recommendations/${id}/outcome`, data),
  getOutcomes: (id) => api.get(`/api/recommendations/${id}/outcomes`),
};

// Tasks endpoints
export const tasksAPI = {
  getAll: (params) => api.get('/api/tasks', { params }),
  create: (data) => api.post('/api/tasks', data),
  assign: (id, assignedTo) => api.patch(`/api/tasks/${id}/assign`, { assigned_to: assignedTo }),
  updateStatus: (id, status, blockerReason = null) => api.patch(`/api/tasks/${id}/status`, {
    status,
    ...(blockerReason ? { blocker_reason: blockerReason } : {}),
  }),
  escalate: (id, blockerReason, escalateToUserId = null) =>
    api.patch(`/api/tasks/${id}/escalate`, {
      blocker_reason: blockerReason,
      escalate_to_user_id: escalateToUserId
    }),
};

// Inventory endpoints
export const inventoryAPI = {
  getItems: () => api.get('/api/inventory'),
  getStockouts: () => api.get('/api/inventory/stockouts'),
  getPurchaseOrders: () => api.get('/api/inventory/purchase-orders'),
  createPurchaseOrder: (data) => api.post('/api/inventory/purchase-orders', data),
  receivePurchaseOrder: (id) => api.patch(`/api/inventory/purchase-orders/${id}/receive`),
};

// Guest requests endpoints
export const guestRequestsAPI = {
  create: (data) => api.post('/api/guest-requests', data),
  createInternal: (data) => api.post('/api/guest-requests/internal', data),
  getAll: (status) => api.get('/api/guest-requests', { params: { status } }),
  updateStatus: (id, status) => api.patch(`/api/guest-requests/${id}/status`, { status }),
};

// Activity log endpoints
export const activityLogAPI = {
  getAll: (limit = 100, actionType = null) =>
    api.get('/api/activity-log', { params: { limit, action_type: actionType } }),
};

// Demo endpoints
export const demoAPI = {
  reset: () => api.post('/api/demo/reset'),
  seedPhase1: () => api.post('/api/demo/seed-phase1'),
};

// Phase 1: Real-time Weather endpoints
export const weatherAPI = {
  getCurrent: () => api.get('/api/weather/current'),
  getForecast: (hours = 24) => api.get(`/api/weather/forecast?hours=${hours}`),
  getSnapshot: () => api.get('/api/weather/snapshot'),
  getRiskAnalysis: () => api.get('/api/weather/risk-analysis'),
};

// Phase 1: Digital Twin & What-If Simulation endpoints
export const digitalTwinAPI = {
  getState: () => api.get('/api/digital-twin/state'),
  getOperationalSnapshot: () => api.get('/api/digital-twin/operational-snapshot'),
  simulate: (data) => api.post('/api/digital-twin/simulate', data),
  getImpactAnalysis: () => api.get('/api/digital-twin/impact-analysis'),
};

export const guestIntelligenceAPI = {
  login: (email, password) => guestApi.post('/api/guest-intelligence/guest-login', { email, password }),
  createSession: (roomNumber, guestName) => guestApi.post('/api/guest-intelligence/session', {
    room_number: roomNumber,
    guest_name: guestName,
  }),
  getProfile: (token) => guestApi.get('/api/guest-intelligence/profiles/me', {
    headers: { Authorization: `Bearer ${token}` },
  }),
  getRecommendations: (token, limit = 5) => guestApi.get('/api/guest-intelligence/recommendations', {
    params: { limit },
    headers: { Authorization: `Bearer ${token}` },
  }),
  getActivities: (token) => guestApi.get('/api/guest-intelligence/activities', {
    headers: { Authorization: `Bearer ${token}` },
  }),
  getMyRequests: (token) => guestApi.get('/api/guest-intelligence/requests/me', {
    headers: { Authorization: `Bearer ${token}` },
  }),
  createMyRequest: (token, data) => guestApi.post('/api/guest-intelligence/requests', data, {
    headers: { Authorization: `Bearer ${token}` },
  }),
  recordInteraction: (token, data) => guestApi.post('/api/guest-intelligence/interactions', data, {
    headers: { Authorization: `Bearer ${token}` },
  }),
  submitFeedback: (token, data) => guestApi.post('/api/guest-intelligence/feedback', data, {
    headers: { Authorization: `Bearer ${token}` },
  }),
  getManagerOverview: () => api.get('/api/guest-intelligence/manager/overview'),
  getManagerActivities: () => api.get('/api/guest-intelligence/manager/activities'),
  createActivity: (data) => api.post('/api/guest-intelligence/manager/activities', data),
  updateActivity: (id, data) => api.patch(`/api/guest-intelligence/manager/activities/${id}`, data),
};

export default api;

