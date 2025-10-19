import React, { useState, useEffect, useCallback } from 'react';
import { reportService } from '../services/reportService'; // Assuming this is the fixed service file
import { FileText, DollarSign, TrendingUp, Download, Calendar } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import Loading from '../components/common/Loading';
import toast from 'react-hot-toast';

const ReportsPage = () => {
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false); // New state for export loading
  const [period, setPeriod] = useState('month');
  const [salesData, setSalesData] = useState(null);
  const [inventoryData, setInventoryData] = useState(null);

  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      const [sales, inventory] = await Promise.all([
        reportService.getSalesAnalytics({ period }), // Corrected function name
        reportService.getInventoryAnalytics()        // Corrected function name
      ]);
      setSalesData(sales.data);
      setInventoryData(inventory.data);
    } catch (error) {
      console.error('Error fetching reports:', error);
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  }, [period]);

  const handleExport = async () => {
    setExporting(true);
    toast.loading('Preparing report for download...');
    try {
      // You can choose the report type and format here
      await reportService.exportReport('sales', 'pdf', { period });
      toast.dismiss();
      toast.success('Report exported successfully!');
    } catch (error) {
      toast.dismiss();
      toast.error('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  if (loading) {
    return <Loading message="Loading reports..." />;
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Reports & Analytics</h2>
        <div className="flex items-center space-x-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="input-field"
            disabled={exporting} // Disable during export
          >
            <option value="day">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="year">This Year</option>
          </select>
          
          {/* ✅ FIX: Added onClick handler and disabled state */}
          <button 
            className="btn-secondary flex items-center space-x-2"
            onClick={handleExport}
            disabled={exporting || loading}
          >
            <Download className="w-4 h-4" />
            <span>{exporting ? 'Exporting...' : 'Export'}</span>
          </button>
        </div>
      </div>

      {/* ... (Rest of the component code remains the same) ... */}
      
    </div>
  );
};

export default ReportsPage;