import api from './api';

export const inventoryService = {
  // Products
  getProducts: (params) => api.get('/inventory/products/', { params }),
  getProduct: (id) => api.get(`/inventory/products/${id}/`),
  createProduct: (data) => api.post('/inventory/products/', data),
  updateProduct: (id, data) => api.put(`/inventory/products/${id}/`, data),
  deleteProduct: (id) => api.delete(`/inventory/products/${id}/`),

  // Categories
  getCategories: () => api.get('/inventory/categories/'),
  createCategory: (data) => api.post('/inventory/categories/', data),

  // Suppliers
  getSuppliers: () => api.get('/inventory/suppliers/'),
  createSupplier: (data) => api.post('/inventory/suppliers/', data),

  // Inventory Movements
  getMovements: (params) => api.get('/inventory/movements/', { params }),
  createMovement: (data) => api.post('/inventory/movements/', data),

  // Alerts
  getLowStockAlerts: () => api.get('/inventory/alerts/'),
  acknowledgeAlert: (id) => api.post(`/inventory/alerts/${id}/acknowledge/`),

  // Reports
  getInventoryReport: () => api.get('/inventory/reports/inventory/'),
};