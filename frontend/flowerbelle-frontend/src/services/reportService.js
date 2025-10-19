import api from './api';

export const reportService = {
  getDashboard: () => api.get('/reports/dashboard/'),
  getSalesAnalytics: (params) => api.get('/reports/analytics/sales/', { params }),
  getInventoryAnalytics: () => api.get('/reports/analytics/inventory/'),
  getProfitLoss: (params) => api.get('/reports/profit-loss/', { params }),
  getStaffPerformance: (params) => api.get('/reports/staff-performance/', { params }),
};