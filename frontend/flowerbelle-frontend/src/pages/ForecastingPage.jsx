import React, { useState, useEffect } from 'react';
import { forecastingService } from '../services/forecastingService';
import { inventoryService } from '../services/inventoryService';
import { TrendingUp, AlertCircle, Calendar, Package } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import Loading from '../components/common/Loading';
import toast from 'react-hot-toast';

const ForecastingPage = () => {
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    fetchProducts();
    fetchRecommendations();
  }, []);

const fetchProducts = async () => {
  try {
    const response = await inventoryService.getProducts();
    console.log("Forecasting products response:", response.data); // 👈 Check actual structure

    const data = response.data;
    const normalizedProducts = Array.isArray(data)
      ? data
      : Array.isArray(data.results)
      ? data.results
      : Array.isArray(data.products)
      ? data.products
      : [];

    setProducts(normalizedProducts);
  } catch (error) {
    console.error('Error fetching products:', error);
    setProducts([]); // prevent map crash
  }
};


  const fetchRecommendations = async () => {
    try {
      const response = await forecastingService.getRecommendations({ status: 'PENDING' });
      setRecommendations(response.data);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
    }
  };

  const handleGenerateForecast = async () => {
    if (!selectedProduct) {
      toast.error('Please select a product');
      return;
    }

    setGenerating(true);
    try {
      await forecastingService.generateForecast({
        product_id: selectedProduct,
        forecast_days: 30,
        training_days: 90
      });

      // Fetch the generated forecast
      const response = await forecastingService.getForecastSummary(selectedProduct);
      setForecast(response.data);
      
      toast.success('Forecast generated successfully!');
      fetchRecommendations();
    } catch (error) {
      console.error('Forecast error:', error);
      toast.error(error.response?.data?.error || 'Failed to generate forecast');
    } finally {
      setGenerating(false);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'URGENT': return 'bg-red-100 text-red-800';
      case 'HIGH': return 'bg-orange-100 text-orange-800';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">Demand Forecasting</h2>
        <p className="text-gray-600">AI-powered demand prediction using Linear Regression</p>
      </div>

      {/* Forecast Generator */}
      <div className="card mb-6">
        <h3 className="text-lg font-semibold mb-4">Generate Forecast</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Product
            </label>
            <select
              value={selectedProduct || ''}
              onChange={(e) => setSelectedProduct(e.target.value)}
              className="input-field"
            >
              <option value="">Choose a product...</option>
              {products.map(product => (
                <option key={product.id} value={product.id}>
                  {product.name} ({product.sku}) - Stock: {product.current_stock}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleGenerateForecast}
              disabled={generating || !selectedProduct}
              className="w-full btn-primary flex items-center justify-center space-x-2"
            >
              {generating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <TrendingUp className="w-5 h-5" />
                  <span>Generate Forecast</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Forecast Results */}
        {forecast && (
          <div className="mt-6 border-t border-gray-200 pt-6">
            <h4 className="font-semibold mb-4">Forecast Results: {forecast.product_name}</h4>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-blue-600 mb-1">Current Stock</p>
                <p className="text-2xl font-bold text-blue-900">{forecast.current_stock}</p>
              </div>
              <div className="bg-purple-50 rounded-lg p-4">
                <p className="text-sm text-purple-600 mb-1">7-Day Forecast</p>
                <p className="text-2xl font-bold text-purple-900">{forecast.forecast_7_days}</p>
              </div>
              <div className="bg-pink-50 rounded-lg p-4">
                <p className="text-sm text-pink-600 mb-1">30-Day Forecast</p>
                <p className="text-2xl font-bold text-pink-900">{forecast.forecast_30_days}</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-sm text-green-600 mb-1">Days Until Stockout</p>
                <p className="text-2xl font-bold text-green-900">{forecast.days_until_stockout}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Trend Analysis</p>
                <div className="flex items-center space-x-2">
                  <TrendingUp className={`w-5 h-5 ${
                    forecast.trend === 'increasing' ? 'text-green-600' :
                    forecast.trend === 'decreasing' ? 'text-red-600' :
                    'text-gray-600'
                  }`} />
                  <span className="font-medium capitalize">{forecast.trend}</span>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Seasonal Impact</p>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  forecast.seasonal_impact === 'high' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'
                }`}>
                  {forecast.seasonal_impact}
                </span>
              </div>
            </div>

            {forecast.recommended_order > 0 && (
              <div className="mt-4 bg-primary-50 border border-primary-200 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <AlertCircle className="w-5 h-5 text-primary-600 mt-0.5" />
                  <div>
                    <p className="font-semibold text-primary-900">Recommendation</p>
                    <p className="text-primary-700">
                      Order <strong>{forecast.recommended_order} units</strong> to maintain adequate stock levels.
                      Priority: <span className="font-bold">{forecast.priority}</span>
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Stock Recommendations */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Stock Recommendations</h3>
        
        {recommendations.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Package className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p>No recommendations at this time</p>
            <p className="text-sm">Generate forecasts to receive stock recommendations</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recommendations.map((rec) => (
              <div key={rec.id} className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h4 className="font-semibold text-gray-900">{rec.product_name}</h4>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getPriorityColor(rec.priority)}`}>
                        {rec.priority_display}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{rec.reason}</p>
                    <div className="flex items-center space-x-4 text-sm">
                      <span className="text-gray-500">
                        Current Stock: <strong>{rec.current_stock}</strong>
                      </span>
                      <span className="text-primary-600">
                        Recommended Order: <strong>{rec.recommended_order_quantity} units</strong>
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => toast.info('Acknowledge functionality coming soon')}
                    className="btn-secondary text-sm"
                  >
                    Acknowledge
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ForecastingPage;