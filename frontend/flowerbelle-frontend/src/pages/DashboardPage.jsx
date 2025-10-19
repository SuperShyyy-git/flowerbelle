import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { reportService } from '../services/reportService';
import { 
  DollarSign, ShoppingBag, Package, AlertTriangle, 
  TrendingUp, TrendingDown, Users, Calendar 
} from 'lucide-react';
import Loading from '../components/common/Loading';
import { Link } from 'react-router-dom';

const DashboardPage = () => {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await reportService.getDashboard();
      setDashboard(response.data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loading message="Loading dashboard..." />;
  }

  const stats = [
    {
      title: "Today's Sales",
      value: `₱${dashboard?.today_sales?.toLocaleString() || 0}`,
      change: "+12%",
      trend: "up",
      icon: DollarSign,
      color: "text-green-600",
      bgColor: "bg-green-100"
    },
    {
      title: "Transactions",
      value: dashboard?.today_transactions || 0,
      change: "+5",
      trend: "up",
      icon: ShoppingBag,
      color: "text-blue-600",
      bgColor: "bg-blue-100"
    },
    {
      title: "Low Stock Items",
      value: dashboard?.low_stock_count || 0,
      change: "Need attention",
      trend: "warning",
      icon: AlertTriangle,
      color: "text-red-600",
      bgColor: "bg-red-100"
    },
    {
      title: "Total Products",
      value: dashboard?.total_products || 0,
      change: "Active items",
      trend: "neutral",
      icon: Package,
      color: "text-purple-600",
      bgColor: "bg-purple-100"
    }
  ];

  return (
    <div>
      {/* Welcome Message */}
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.full_name}! 👋
        </h2>
        <p className="text-gray-600 mt-2">
          Here's what's happening with your flower shop today.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="stat-card">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 ${stat.bgColor} rounded-lg flex items-center justify-center`}>
                  <Icon className={`w-6 h-6 ${stat.color}`} />
                </div>
                {stat.trend === 'up' && <TrendingUp className="w-5 h-5 text-green-500" />}
                {stat.trend === 'down' && <TrendingDown className="w-5 h-5 text-red-500" />}
                {stat.trend === 'warning' && <AlertTriangle className="w-5 h-5 text-red-500" />}
              </div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">{stat.title}</h3>
              <p className="text-3xl font-bold text-gray-900 mb-2">{stat.value}</p>
              <p className={`text-sm ${
                stat.trend === 'up' ? 'text-green-600' : 
                stat.trend === 'warning' ? 'text-red-600' : 
                'text-gray-600'
              }`}>
                {stat.change}
              </p>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="mb-6 card">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link to="/pos" className="btn-primary text-center">
            New Sale
          </Link>
          <Link to="/inventory" className="btn-secondary text-center">
            View Products
          </Link>
          {user?.role === 'OWNER' && (
            <>
              <Link to="/reports" className="btn-secondary text-center">
                Reports
              </Link>
              <Link to="/forecasting" className="btn-secondary text-center">
                Forecasting
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Weekly Overview & Top Products */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* This Week */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center">
            <Calendar className="w-5 h-5 mr-2" />
            This Week
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Sales</span>
              <span className="text-xl font-bold">₱{dashboard?.week_sales?.toLocaleString() || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Transactions</span>
              <span className="text-xl font-bold">{dashboard?.week_transactions || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Profit</span>
              <span className="text-xl font-bold text-green-600">
                ₱{dashboard?.week_profit?.toLocaleString() || 0}
              </span>
            </div>
          </div>
        </div>

        {/* Top Products */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Top Selling Products</h3>
          <div className="space-y-3">
            {dashboard?.top_products?.slice(0, 5).map((product, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-primary-700 font-bold">
                    {index + 1}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{product.product__name}</p>
                    <p className="text-sm text-gray-500">{product.total_quantity} sold</p>
                  </div>
                </div>
                <span className="font-semibold text-gray-900">
                  ₱{product.total_sales?.toLocaleString()}
                </span>
              </div>
            )) || (
              <p className="text-gray-500 text-center py-4">No sales data yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Recent Transactions */}
      <div className="mt-6 card">
        <h3 className="text-lg font-semibold mb-4">Recent Transactions</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Transaction #
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Amount
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Staff
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {dashboard?.recent_transactions?.slice(0, 5).map((txn) => (
                <tr key={txn.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {txn.transaction_number}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ₱{parseFloat(txn.total_amount).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {txn.created_by__full_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(txn.created_at).toLocaleString()}
                  </td>
                </tr>
              )) || (
                <tr>
                  <td colSpan="4" className="px-6 py-4 text-center text-gray-500">
                    No transactions yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;