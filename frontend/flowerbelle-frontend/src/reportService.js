import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api';

// Create axios instance with defaults
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to all requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    console.log(`📊 Reports API: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Handle responses and errors
api.interceptors.response.use(
  (response) => {
    console.log('✅ Reports Response:', response.data);
    return response;
  },
  (error) => {
    console.error('❌ Reports Error:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      url: error.config?.url,
    });

    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

export const reportService = { // Renamed from reportsService to match your component import
  // Get sales summary
  getSalesAnalytics: async (params = {}) => { // Renamed to match the call in ReportsPage.js
    try {
      const response = await api.get('/reports/sales-summary/', { params });
      return response; // Return full response to get .data in component
    } catch (error) {
      console.error('Error getting sales summary:', error);
      throw error;
    }
  },

  // Get inventory report
  getInventoryAnalytics: async (params = {}) => { // Renamed to match the call in ReportsPage.js
    try {
      const response = await api.get('/reports/inventory/', { params });
      return response; // Return full response to get .data in component
    } catch (error) {
      console.error('Error getting inventory report:', error);
      throw error;
    }
  },

  // Export report
  exportReport: async (reportType, format = 'pdf', params = {}) => {
    try {
      const response = await api.get(`/reports/export/${reportType}/`, {
        params: { ...params, format },
        responseType: 'blob',
      });
      
      // ✅ FIX: Use setTimeout(0) to execute the DOM manipulation 
      // outside of React's render/update cycle to prevent 'reading style' error.
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${reportType}-report.${format}`);
      
      setTimeout(() => {
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url); // Clean up the object URL
      }, 0);
      
      return response.data;
    } catch (error) {
      console.error('Error exporting report:', error);
      throw error;
    }
  },
  // ... (other functions remain the same)
};

export default reportService;