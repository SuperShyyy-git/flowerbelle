from django.urls import path
from .views import (
    # Dashboard
    DashboardOverviewView, DashboardMetricsHistoryView,
    # Analytics
    SalesAnalyticsView, InventoryAnalyticsView,
    # Reports
    ProfitLossReportView, StaffPerformanceView,
    # Export
    ReportExportView, ReportExportListView
)

app_name = 'reports'

urlpatterns = [
    # Dashboard
    path('dashboard/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('dashboard/history/', DashboardMetricsHistoryView.as_view(), name='dashboard-history'),
    
    # Analytics
    path('analytics/sales/', SalesAnalyticsView.as_view(), name='sales-analytics'),
    path('analytics/inventory/', InventoryAnalyticsView.as_view(), name='inventory-analytics'),
    
    # Reports
    path('profit-loss/', ProfitLossReportView.as_view(), name='profit-loss'),
    path('staff-performance/', StaffPerformanceView.as_view(), name='staff-performance'),
    
    # Export
    path('export/', ReportExportView.as_view(), name='report-export'),
    path('exports/', ReportExportListView.as_view(), name='export-list'),
]