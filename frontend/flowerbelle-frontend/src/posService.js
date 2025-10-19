import api from './api';

export const posService = {
  // Transactions
  getTransactions: (params) => api.get('/pos/transactions/', { params }),
  getTransaction: (id) => api.get(`/pos/transactions/${id}/`),
  createTransaction: (data) => api.post('/pos/transactions/', data),
  voidTransaction: (id, reason) => api.post(`/pos/transactions/${id}/void/`, { reason }),

  // Cart
  getCart: () => api.get('/pos/cart/'),
  addToCart: (data) => api.post('/pos/cart/add/', data),
  updateCartItem: (id, quantity) => api.patch(`/pos/cart/items/${id}/`, { quantity }),
  removeCartItem: (id) => api.delete(`/pos/cart/items/${id}/remove/`),
  clearCart: () => api.delete('/pos/cart/'),
  checkout: (data) => api.post('/pos/checkout/', data),

  // Reports
  getDailySales: () => api.get('/pos/reports/daily/'),
  getSalesReport: (params) => api.get('/pos/reports/sales/', { params }),
};