from rest_framework import serializers
from .models import (
    ForecastModel, ProductForecast, CategoryForecast,
    SeasonalPattern, StockRecommendation
)
from inventory.models import Product, Category


class ForecastModelSerializer(serializers.ModelSerializer):
    """Serializer for forecast models"""
    trained_by_name = serializers.CharField(source='trained_by.full_name', read_only=True)
    model_type_display = serializers.CharField(source='get_model_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ForecastModel
        fields = ('id', 'name', 'model_type', 'model_type_display', 'version',
                 'status', 'status_display', 'parameters', 'r2_score', 'mse',
                 'rmse', 'mae', 'accuracy', 'training_start_date', 'training_end_date',
                 'training_samples', 'is_active', 'trained_by', 'trained_by_name',
                 'trained_at', 'last_used')
        read_only_fields = ('id', 'trained_at', 'last_used')


class ProductForecastSerializer(serializers.ModelSerializer):
    """Serializer for product forecasts"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_current_stock = serializers.IntegerField(source='product.current_stock', read_only=True)
    is_accurate = serializers.ReadOnlyField()
    recommended_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductForecast
        fields = ('id', 'product', 'product_name', 'product_sku', 'product_current_stock',
                 'forecast_model', 'forecast_date', 'predicted_demand', 'confidence_lower',
                 'confidence_upper', 'confidence_level', 'actual_demand', 'forecast_error',
                 'absolute_percentage_error', 'is_peak_season', 'seasonal_factor',
                 'is_accurate', 'recommended_stock', 'created_at', 'updated_at')
        read_only_fields = ('id', 'forecast_error', 'absolute_percentage_error', 'created_at', 'updated_at')


class ProductForecastCreateSerializer(serializers.Serializer):
    """Serializer for creating forecasts"""
    product_id = serializers.IntegerField()
    forecast_days = serializers.IntegerField(default=30, min_value=1, max_value=90)
    training_days = serializers.IntegerField(default=90, min_value=30, max_value=365)
    
    def validate_product_id(self, value):
        try:
            Product.objects.get(id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or inactive")
        return value


class CategoryForecastSerializer(serializers.ModelSerializer):
    """Serializer for category forecasts"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = CategoryForecast
        fields = ('id', 'category', 'category_name', 'forecast_model', 'forecast_date',
                 'predicted_demand', 'confidence_lower', 'confidence_upper',
                 'actual_demand', 'created_at')
        read_only_fields = ('id', 'created_at')


class SeasonalPatternSerializer(serializers.ModelSerializer):
    """Serializer for seasonal patterns"""
    season_type_display = serializers.CharField(source='get_season_type_display', read_only=True)
    category_names = serializers.SerializerMethodField()
    
    class Meta:
        model = SeasonalPattern
        fields = ('id', 'name', 'season_type', 'season_type_display', 'start_month',
                 'start_day', 'end_month', 'end_day', 'demand_multiplier', 'categories',
                 'category_names', 'description', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_category_names(self, obj):
        return [cat.name for cat in obj.categories.all()]


class StockRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for stock recommendations"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.full_name', read_only=True)
    
    class Meta:
        model = StockRecommendation
        fields = ('id', 'product', 'product_name', 'product_sku', 'forecast',
                 'current_stock', 'recommended_order_quantity', 'reason', 'priority',
                 'priority_display', 'status', 'status_display', 'ordered_quantity',
                 'order_date', 'created_at', 'acknowledged_by', 'acknowledged_by_name',
                 'acknowledged_at')
        read_only_fields = ('id', 'created_at', 'acknowledged_at')


class ForecastSummarySerializer(serializers.Serializer):
    """Serializer for forecast summary"""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    product_sku = serializers.CharField()
    current_stock = serializers.IntegerField()
    
    # Next 7 days forecast
    forecast_7_days = serializers.IntegerField()
    forecast_30_days = serializers.IntegerField()
    
    # Recommendations
    recommended_order = serializers.IntegerField()
    days_until_stockout = serializers.IntegerField()
    priority = serializers.CharField()
    
    # Trend
    trend = serializers.CharField()  # 'increasing', 'decreasing', 'stable'
    seasonal_impact = serializers.CharField()


class ForecastAccuracySerializer(serializers.Serializer):
    """Serializer for forecast accuracy metrics"""
    model_id = serializers.IntegerField()
    model_name = serializers.CharField()
    
    total_forecasts = serializers.IntegerField()
    accurate_forecasts = serializers.IntegerField()
    accuracy_rate = serializers.FloatField()
    
    average_error = serializers.FloatField()
    average_percentage_error = serializers.FloatField()
    
    # By product category
    category_accuracy = serializers.ListField(child=serializers.DictField())


class TrainingResultSerializer(serializers.Serializer):
    """Serializer for training results"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    model = ForecastModelSerializer(required=False)
    metrics = serializers.DictField(required=False)
    training_info = serializers.DictField(required=False)


class BulkForecastSerializer(serializers.Serializer):
    """Serializer for bulk forecast generation"""
    category_id = serializers.IntegerField(required=False)
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    forecast_days = serializers.IntegerField(default=30, min_value=1, max_value=90)
    generate_recommendations = serializers.BooleanField(default=True)