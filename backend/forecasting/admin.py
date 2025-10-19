from django.contrib import admin
from .models import (
    ForecastModel, ProductForecast, CategoryForecast,
    SeasonalPattern, StockRecommendation
)


@admin.register(ForecastModel)
class ForecastModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'model_type', 'status', 'is_active', 
                   'accuracy', 'r2_score', 'trained_at')
    list_filter = ('model_type', 'status', 'is_active', 'trained_at')
    search_fields = ('name', 'version')
    readonly_fields = ('trained_at', 'last_used')


@admin.register(ProductForecast)
class ProductForecastAdmin(admin.ModelAdmin):
    list_display = ('product', 'forecast_date', 'predicted_demand', 'actual_demand',
                   'confidence_lower', 'confidence_upper', 'is_accurate')
    list_filter = ('forecast_date', 'is_peak_season', 'product__category')
    search_fields = ('product__name', 'product__sku')
    readonly_fields = ('forecast_error', 'absolute_percentage_error', 'created_at')
    date_hierarchy = 'forecast_date'


@admin.register(CategoryForecast)
class CategoryForecastAdmin(admin.ModelAdmin):
    list_display = ('category', 'forecast_date', 'predicted_demand', 'actual_demand')
    list_filter = ('forecast_date', 'category')
    date_hierarchy = 'forecast_date'


@admin.register(SeasonalPattern)
class SeasonalPatternAdmin(admin.ModelAdmin):
    list_display = ('name', 'season_type', 'start_month', 'start_day',
                   'end_month', 'end_day', 'demand_multiplier', 'is_active')
    list_filter = ('season_type', 'is_active')
    search_fields = ('name', 'description')
    filter_horizontal = ('categories',)


@admin.register(StockRecommendation)
class StockRecommendationAdmin(admin.ModelAdmin):
    list_display = ('product', 'recommended_order_quantity', 'priority', 
                   'status', 'created_at')
    list_filter = ('priority', 'status', 'created_at')
    search_fields = ('product__name', 'product__sku', 'reason')
    readonly_fields = ('created_at', 'acknowledged_at')