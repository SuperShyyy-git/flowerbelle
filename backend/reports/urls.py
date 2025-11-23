from django.urls import path
from .views import (
    DashboardOverviewView, 
    DashboardMetricsHistoryView,
    SalesAnalyticsView, 
    InventoryAnalyticsView,
    SimpleInventoryListView,
    ProfitLossReportView, 
    StaffPerformanceView,
    ReportExportView, 
    ReportExportListView, 
    SimpleReportExport,  # ✅ NEW: Simple export view
    TestExportView
)

app_name = 'reports'

urlpatterns = [
    # TEST ENDPOINT
    path('export/test/', TestExportView.as_view(), name='export-test'),
    
    # ✅ NEW SIMPLE EXPORT ROUTES (these will work!)
    path('export/sales/', SimpleReportExport.as_view(), {'report_type': 'sales'}, name='export-sales'),
    path('export/inventory/', SimpleReportExport.as_view(), {'report_type': 'inventory'}, name='export-inventory'),
    path('export/profit/', SimpleReportExport.as_view(), {'report_type': 'profit'}, name='export-profit'),
    path('export/staff/', SimpleReportExport.as_view(), {'report_type': 'staff'}, name='export-staff'),
    
    # ANALYTICS & DASHBOARD
    path('sales-summary/', SalesAnalyticsView.as_view(), name='sales-summary'),
    path('dashboard/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('dashboard/history/', DashboardMetricsHistoryView.as_view(), name='dashboard-history'),
    path('analytics/inventory/', InventoryAnalyticsView.as_view(), name='inventory-analytics'),
    path('inventory/stock-list/', SimpleInventoryListView.as_view(), name='inventory-stock-list'),
    path('profit-loss/', ProfitLossReportView.as_view(), name='profit-loss'),
    path('staff-performance/', StaffPerformanceView.as_view(), name='staff-performance'),
    
    # EXPORT MANAGEMENT
    path('exports/', ReportExportListView.as_view(), name='export-list'),
    path('export/', ReportExportView.as_view(), name='report-export'),
]