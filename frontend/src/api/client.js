import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor: attach token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ─── AUTH ────────────────────────────────────────────────────────────────────
export const authAPI = {
  login: (username, password) =>
    apiClient.post('/auth/login', { username, password }),
  getMe: () => apiClient.get('/auth/me'),
}

// ─── VEHICLES ────────────────────────────────────────────────────────────────
export const vehiclesAPI = {
  getAll: (params) => apiClient.get('/vehicles', { params }),
  create: (data) => apiClient.post('/vehicles', data),
  update: (id, data) => apiClient.put(`/vehicles/${id}`, data),
  delete: (id) => apiClient.delete(`/vehicles/${id}`),
  getExpiring: () => apiClient.get('/vehicles/expiring'),
}

// ─── BARGES ──────────────────────────────────────────────────────────────────
export const bargesAPI = {
  getAll: (params) => apiClient.get('/barges', { params }),
  create: (data) => apiClient.post('/barges', data),
  update: (id, data) => apiClient.put(`/barges/${id}`, data),
  delete: (id) => apiClient.delete(`/barges/${id}`),
}

// ─── DRIVERS ─────────────────────────────────────────────────────────────────
export const driversAPI = {
  getAll: (params) => apiClient.get('/drivers', { params }),
  create: (data) => apiClient.post('/drivers', data),
  update: (id, data) => apiClient.put(`/drivers/${id}`, data),
  delete: (id) => apiClient.delete(`/drivers/${id}`),
}

// ─── TRIPS ───────────────────────────────────────────────────────────────────
export const tripsAPI = {
  getAll: (params) => apiClient.get('/trips', { params }),
  create: (data) => apiClient.post('/trips', data),
  update: (id, data) => apiClient.put(`/trips/${id}`, data),
  delete: (id) => apiClient.delete(`/trips/${id}`),
  exportExcel: (params) =>
    apiClient.get('/trips/export', {
      params,
      responseType: 'blob',
    }),
}

// ─── FUEL ────────────────────────────────────────────────────────────────────
export const fuelAPI = {
  getAll: (params) => apiClient.get('/fuel', { params }),
  create: (data) => apiClient.post('/fuel', data),
  update: (id, data) => apiClient.put(`/fuel/${id}`, data),
  delete: (id) => apiClient.delete(`/fuel/${id}`),
  getSummary: (params) => apiClient.get('/fuel/summary', { params }),
}

// ─── DASHBOARD ───────────────────────────────────────────────────────────────
export const dashboardAPI = {
  getStats: () => apiClient.get('/dashboard/stats'),
}

export default apiClient
