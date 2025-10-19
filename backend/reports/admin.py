from django.contrib import admin
from .models import ReportSchedule, ReportExport, DashboardMetric


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'frequency', 'is_active', 'last_run', 'next_run')
    list_filter = ('report_type', 'frequency', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('last_run', 'created_at', 'updated_at')


@admin.register(ReportExport)
class ReportExportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'export_format', 'status', 'file_size', 'created_by', 'created_at')
    list_filter = ('report_type', 'export_format', 'status', 'created_at')
    search_fields = ('report_type',)
    readonly_fields = ('file_size', 'created_at', 'completed_at')


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    list_display = ('date', 'daily_sales', 'daily_transactions', 'daily_profit', 
                   'total_products', 'low_stock_count', 'inventory_value')
    list_filter = ('date',)
    date_hierarchy = 'date'
    ordering = ('-date',)