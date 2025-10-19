from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from inventory.models import Product, Category
from accounts.models import User


class ForecastModel(models.Model):
    """Store trained forecasting models"""
    
    MODEL_TYPES = (
        ('LINEAR_REGRESSION', 'Linear Regression'),
    )
    
    STATUS_CHOICES = (
        ('TRAINING', 'Training'),
        ('ACTIVE', 'Active'),
        ('DEPRECATED', 'Deprecated'),
        ('FAILED', 'Failed'),
    )
    
    name = models.CharField(max_length=200)
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES, default='LINEAR_REGRESSION')
    version = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TRAINING')
    
    # Model parameters (stored as JSON)
    parameters = models.JSONField(default=dict, help_text='Model hyperparameters')
    
    # Model metrics
    r2_score = models.FloatField(null=True, blank=True, help_text='R-squared score')
    mse = models.FloatField(null=True, blank=True, help_text='Mean Squared Error')
    rmse = models.FloatField(null=True, blank=True, help_text='Root Mean Squared Error')
    mae = models.FloatField(null=True, blank=True, help_text='Mean Absolute Error')
    accuracy = models.FloatField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Model accuracy percentage'
    )
    
    # Training data info
    training_start_date = models.DateField()
    training_end_date = models.DateField()
    training_samples = models.IntegerField(default=0)
    
    # Model file path (if saving serialized model)
    model_file_path = models.CharField(max_length=500, blank=True)
    
    # Tracking
    is_active = models.BooleanField(default=False)
    trained_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='trained_models')
    trained_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'forecast_models'
        verbose_name = 'Forecast Model'
        verbose_name_plural = 'Forecast Models'
        ordering = ['-trained_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_status_display()})"
    
    def activate(self):
        """Set this model as active and deactivate others"""
        ForecastModel.objects.filter(is_active=True).update(is_active=False)
        self.is_active = True
        self.status = 'ACTIVE'
        self.save()


class ProductForecast(models.Model):
    """Store demand forecasts for products"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='forecasts')
    forecast_model = models.ForeignKey(ForecastModel, on_delete=models.CASCADE, related_name='forecasts')
    
    # Forecast details
    forecast_date = models.DateField(help_text='Date for which demand is predicted')
    predicted_demand = models.IntegerField(validators=[MinValueValidator(0)])
    
    # Confidence intervals
    confidence_lower = models.IntegerField(validators=[MinValueValidator(0)])
    confidence_upper = models.IntegerField(validators=[MinValueValidator(0)])
    confidence_level = models.FloatField(default=95.0, help_text='Confidence level (e.g., 95%)')
    
    # Actual demand (filled after the forecast date)
    actual_demand = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    
    # Accuracy metrics (calculated after actual demand is known)
    forecast_error = models.IntegerField(null=True, blank=True)
    absolute_percentage_error = models.FloatField(null=True, blank=True)
    
    # Seasonal factors
    is_peak_season = models.BooleanField(default=False)
    seasonal_factor = models.FloatField(default=1.0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_forecasts'
        verbose_name = 'Product Forecast'
        verbose_name_plural = 'Product Forecasts'
        ordering = ['-forecast_date']
        unique_together = ['product', 'forecast_date', 'forecast_model']
        indexes = [
            models.Index(fields=['product', 'forecast_date']),
            models.Index(fields=['forecast_date']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.forecast_date}: {self.predicted_demand} units"
    
    def calculate_accuracy(self):
        """Calculate forecast accuracy after actual demand is known"""
        if self.actual_demand is not None:
            self.forecast_error = self.actual_demand - self.predicted_demand
            
            if self.actual_demand > 0:
                self.absolute_percentage_error = (
                    abs(self.forecast_error) / self.actual_demand * 100
                )
            
            self.save()
    
    @property
    def is_accurate(self):
        """Check if forecast is within 20% of actual demand"""
        if self.absolute_percentage_error is not None:
            return self.absolute_percentage_error <= 20
        return None
    
    @property
    def recommended_stock(self):
        """Calculate recommended stock level"""
        # Add safety stock (confidence upper bound)
        return self.confidence_upper


class CategoryForecast(models.Model):
    """Store aggregate forecasts for product categories"""
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='forecasts')
    forecast_model = models.ForeignKey(ForecastModel, on_delete=models.CASCADE, related_name='category_forecasts')
    
    forecast_date = models.DateField()
    predicted_demand = models.IntegerField(validators=[MinValueValidator(0)])
    confidence_lower = models.IntegerField(validators=[MinValueValidator(0)])
    confidence_upper = models.IntegerField(validators=[MinValueValidator(0)])
    
    actual_demand = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'category_forecasts'
        verbose_name = 'Category Forecast'
        verbose_name_plural = 'Category Forecasts'
        ordering = ['-forecast_date']
        unique_together = ['category', 'forecast_date', 'forecast_model']
    
    def __str__(self):
        return f"{self.category.name} - {self.forecast_date}: {self.predicted_demand} units"


class SeasonalPattern(models.Model):
    """Store identified seasonal patterns"""
    
    SEASON_TYPES = (
        ('HOLIDAY', 'Holiday'),
        ('MONTHLY', 'Monthly Pattern'),
        ('WEEKLY', 'Weekly Pattern'),
        ('SPECIAL', 'Special Event'),
    )
    
    name = models.CharField(max_length=200, help_text='e.g., Valentine\'s Day, Mother\'s Day')
    season_type = models.CharField(max_length=20, choices=SEASON_TYPES)
    
    # Date range (month-day format, e.g., 02-14 for Feb 14)
    start_month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    start_day = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    end_month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    end_day = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    
    # Impact
    demand_multiplier = models.FloatField(
        default=1.0,
        help_text='Expected demand increase (e.g., 2.5 = 250% of normal)'
    )
    
    # Affected categories
    categories = models.ManyToManyField(Category, related_name='seasonal_patterns', blank=True)
    
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'seasonal_patterns'
        verbose_name = 'Seasonal Pattern'
        verbose_name_plural = 'Seasonal Patterns'
        ordering = ['start_month', 'start_day']
    
    def __str__(self):
        return f"{self.name} ({self.start_month}/{self.start_day} - {self.end_month}/{self.end_day})"
    
    def is_active_on_date(self, date):
        """Check if this seasonal pattern is active on a given date"""
        from datetime import date as date_type
        
        start = date_type(date.year, self.start_month, self.start_day)
        end = date_type(date.year, self.end_month, self.end_day)
        
        # Handle year-crossing seasons (e.g., Dec-Jan)
        if start > end:
            return date >= start or date <= end
        else:
            return start <= date <= end


class StockRecommendation(models.Model):
    """AI-generated stock recommendations"""
    
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('ORDERED', 'Ordered'),
        ('COMPLETED', 'Completed'),
        ('IGNORED', 'Ignored'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_recommendations')
    forecast = models.ForeignKey(ProductForecast, on_delete=models.CASCADE, related_name='recommendations')
    
    # Recommendation details
    current_stock = models.IntegerField()
    recommended_order_quantity = models.IntegerField(validators=[MinValueValidator(0)])
    reason = models.TextField(help_text='Why this recommendation was made')
    
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Order info (if acted upon)
    ordered_quantity = models.IntegerField(null=True, blank=True)
    order_date = models.DateField(null=True, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='acknowledged_recommendations'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'stock_recommendations'
        verbose_name = 'Stock Recommendation'
        verbose_name_plural = 'Stock Recommendations'
        ordering = ['-created_at', '-priority']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['product', 'status']),
        ]
    
    def __str__(self):
        return f"{self.product.name}: Order {self.recommended_order_quantity} units ({self.get_priority_display()})"