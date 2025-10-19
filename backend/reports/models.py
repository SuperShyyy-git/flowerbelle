from django.db import models
from django.utils import timezone
from accounts.models import User


class ReportSchedule(models.Model):
    """Schedule automated reports"""
    
    REPORT_TYPES = (
        ('SALES_DAILY', 'Daily Sales Report'),
        ('SALES_WEEKLY', 'Weekly Sales Report'),
        ('SALES_MONTHLY', 'Monthly Sales Report'),
        ('INVENTORY_MONTHLY', 'Monthly Inventory Report'),
        ('PROFIT_LOSS', 'Profit & Loss Report'),
    )
    
    FREQUENCY_CHOICES = (
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    )
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    recipients = models.TextField(help_text='Comma-separated email addresses')
    is_active = models.BooleanField(default=True)
    
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField()
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'report_schedules'
        verbose_name = 'Report Schedule'
        verbose_name_plural = 'Report Schedules'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class ReportExport(models.Model):
    """Track exported reports"""
    
    EXPORT_FORMATS = (
        ('PDF', 'PDF'),
        ('CSV', 'CSV'),
        ('EXCEL', 'Excel'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    
    report_type = models.CharField(max_length=50)
    export_format = models.CharField(max_length=10, choices=EXPORT_FORMATS)
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.IntegerField(null=True, blank=True, help_text='Size in bytes')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True)
    
    # Report parameters
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    filters = models.JSONField(null=True, blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_exports')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'report_exports'
        verbose_name = 'Report Export'
        verbose_name_plural = 'Report Exports'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report_type} - {self.export_format} ({self.get_status_display()})"


class DashboardMetric(models.Model):
    """Store dashboard metrics for historical tracking"""
    
    date = models.DateField(unique=True)
    
    # Sales metrics
    daily_sales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    daily_transactions = models.IntegerField(default=0)
    daily_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Inventory metrics
    total_products = models.IntegerField(default=0)
    low_stock_count = models.IntegerField(default=0)
    out_of_stock_count = models.IntegerField(default=0)
    inventory_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Customer metrics
    new_customers = models.IntegerField(default=0)
    returning_customers = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dashboard_metrics'
        verbose_name = 'Dashboard Metric'
        verbose_name_plural = 'Dashboard Metrics'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"Metrics for {self.date}"
    
    @classmethod
    def generate_for_date(cls, date):
        """Generate metrics for a specific date"""
        from pos.models import SalesTransaction
        from inventory.models import Product
        from django.db.models import Sum, Count, F
        
        # Sales metrics
        transactions = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__date=date
        )
        
        daily_sales = transactions.aggregate(total=Sum('total_amount'))['total'] or 0
        daily_transactions = transactions.count()
        daily_profit = sum(t.profit for t in transactions)
        
        # Inventory metrics
        total_products = Product.objects.filter(is_active=True).count()
        low_stock_count = Product.objects.filter(
            current_stock__lte=F('reorder_level'),
            is_active=True
        ).count()
        out_of_stock_count = Product.objects.filter(
            current_stock=0,
            is_active=True
        ).count()
        inventory_value = Product.objects.filter(is_active=True).aggregate(
            total=Sum(F('current_stock') * F('cost_price'))
        )['total'] or 0
        
        # Create or update metric
        metric, created = cls.objects.update_or_create(
            date=date,
            defaults={
                'daily_sales': daily_sales,
                'daily_transactions': daily_transactions,
                'daily_profit': daily_profit,
                'total_products': total_products,
                'low_stock_count': low_stock_count,
                'out_of_stock_count': out_of_stock_count,
                'inventory_value': inventory_value,
            }
        )
        
        return metric