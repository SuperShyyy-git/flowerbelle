import api from './api';

export const forecastingService = {
  trainModel: (data) => api.post('/forecasting/train/', data),
  generateForecast: (data) => api.post('/forecasting/generate/', data),
  getForecasts: (params) => api.get('/forecasting/forecasts/', { params }),
  getForecastSummary: (productId) => api.get(`/forecasting/forecasts/summary/${productId}/`),
  getRecommendations: (params) => api.get('/forecasting/recommendations/', { params }),
  acknowledgeRecommendation: (id) => api.post(`/forecasting/recommendations/${id}/acknowledge/`),
  getSeasonalPatterns: () => api.get('/forecasting/seasonal-patterns/'),
  createSeasonalPattern: (data) => api.post('/forecasting/seasonal-patterns/', data),
};