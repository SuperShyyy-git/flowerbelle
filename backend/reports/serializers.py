from rest_framework import serializers
from .models import ReportSchedule, ReportExport, DashboardMetric


class DashboardMetricSerializer(serializers.ModelSerializer):
    """Serializer for dashboard metrics"""
    
    class Meta:
        model = DashboardMetric
        fields = ('id', 'date', 'daily_sales', 'daily_transactions', 'daily_profit',
                 'total_products', 'low_stock_count', 'out_of_stock_count',
                 'inventory_value', 'new_customers', 'returning_customers')


class DashboardOverviewSerializer(serializers.Serializer):
    """Serializer for dashboard overview"""
    # Today's metrics
    today_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    today_transactions = serializers.IntegerField()
    today_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    today_items_sold = serializers.IntegerField()
    
    # This week
    week_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    week_transactions = serializers.IntegerField()
    week_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # This month
    month_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    month_transactions = serializers.IntegerField()
    month_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Inventory
    total_products = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()
    inventory_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Alerts
    pending_alerts = serializers.IntegerField()
    
    # Top products
    top_products = serializers.ListField(child=serializers.DictField())
    
    # Recent transactions
    recent_transactions = serializers.ListField(child=serializers.DictField())


class SalesAnalyticsSerializer(serializers.Serializer):
    """Serializer for sales analytics"""
    period = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    
    total_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_transactions = serializers.IntegerField()
    total_items_sold = serializers.IntegerField()
    total_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_transaction = serializers.DecimalField(max_digits=10, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Growth comparison
    sales_growth = serializers.DecimalField(max_digits=10, decimal_places=2)
    transaction_growth = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # By payment method
    payment_breakdown = serializers.ListField(child=serializers.DictField())
    
    # By category
    category_breakdown = serializers.ListField(child=serializers.DictField())
    
    # Top products
    top_products = serializers.ListField(child=serializers.DictField())
    
    # Hourly distribution
    hourly_sales = serializers.ListField(child=serializers.DictField())
    
    # Daily trend
    daily_trend = serializers.ListField(child=serializers.DictField())


class InventoryAnalyticsSerializer(serializers.Serializer):
    """Serializer for inventory analytics"""
    total_products = serializers.IntegerField()
    active_products = serializers.IntegerField()
    total_inventory_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    low_stock_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()
    expired_products = serializers.IntegerField()
    
    # Stock turnover
    average_stock_age = serializers.IntegerField()
    fast_moving_products = serializers.ListField(child=serializers.DictField())
    slow_moving_products = serializers.ListField(child=serializers.DictField())
    
    # By category
    category_distribution = serializers.ListField(child=serializers.DictField())
    
    # Stock movements
    stock_in_total = serializers.IntegerField()
    stock_out_total = serializers.IntegerField()
    adjustments_total = serializers.IntegerField()


class ProfitLossSerializer(serializers.Serializer):
    """Serializer for profit & loss report"""
    period = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    
    # Revenue
    gross_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    discounts = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Cost of goods sold
    cost_of_goods_sold = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Gross profit
    gross_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    gross_profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Operating expenses (placeholder for future expansion)
    operating_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Net profit
    net_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Breakdown
    profit_by_category = serializers.ListField(child=serializers.DictField())
    profit_by_product = serializers.ListField(child=serializers.DictField())


class StaffPerformanceSerializer(serializers.Serializer):
    """Serializer for staff performance report"""
    staff_id = serializers.IntegerField()
    staff_name = serializers.CharField()
    
    total_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_transactions = serializers.IntegerField()
    total_items_sold = serializers.IntegerField()
    average_transaction = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Performance metrics
    transactions_per_day = serializers.DecimalField(max_digits=10, decimal_places=2)
    best_selling_day = serializers.DateField()
    best_selling_day_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for report schedules"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = ('id', 'name', 'report_type', 'report_type_display', 'frequency',
                 'frequency_display', 'recipients', 'is_active', 'last_run', 'next_run',
                 'created_by', 'created_by_name', 'created_at')
        read_only_fields = ('id', 'last_run', 'created_by', 'created_at')


class ReportExportSerializer(serializers.ModelSerializer):
    """Serializer for report exports"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    export_format_display = serializers.CharField(source='get_export_format_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ReportExport
        fields = ('id', 'report_type', 'export_format', 'export_format_display',
                 'file_path', 'file_size', 'status', 'status_display', 'error_message',
                 'start_date', 'end_date', 'filters', 'created_by', 'created_by_name',
                 'created_at', 'completed_at')
        read_only_fields = ('id', 'file_path', 'file_size', 'status', 'error_message',
                           'created_by', 'created_at', 'completed_at')


class ExportRequestSerializer(serializers.Serializer):
    """Serializer for export requests"""
    report_type = serializers.CharField()
    export_format = serializers.ChoiceField(choices=['PDF', 'CSV', 'EXCEL'])
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    filters = serializers.JSONField(required=False)