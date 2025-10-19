from django.urls import path
from .views import (
    # Training
    TrainModelView,
    # Forecast Generation
    GenerateForecastView, BulkGenerateForecastView,
    # Forecast Retrieval
    ProductForecastListView, ForecastSummaryView,
    # Recommendations
    StockRecommendationListView, AcknowledgeRecommendationView,
    # Seasonal Patterns
    SeasonalPatternListCreateView, SeasonalPatternDetailView,
    # Model Management
    ForecastModelListView, ForecastAccuracyView
)

app_name = 'forecasting'

urlpatterns = [
    # Training
    path('train/', TrainModelView.as_view(), name='train-model'),
    
    # Forecast Generation
    path('generate/', GenerateForecastView.as_view(), name='generate-forecast'),
    path('generate/bulk/', BulkGenerateForecastView.as_view(), name='bulk-generate-forecast'),
    
    # Forecast Retrieval
    path('forecasts/', ProductForecastListView.as_view(), name='forecast-list'),
    path('forecasts/summary/<int:product_id>/', ForecastSummaryView.as_view(), name='forecast-summary'),
    
    # Recommendations
    path('recommendations/', StockRecommendationListView.as_view(), name='recommendation-list'),
    path('recommendations/<int:pk>/acknowledge/', AcknowledgeRecommendationView.as_view(), name='recommendation-acknowledge'),
    
    # Seasonal Patterns
    path('seasonal-patterns/', SeasonalPatternListCreateView.as_view(), name='seasonal-pattern-list'),
    path('seasonal-patterns/<int:pk>/', SeasonalPatternDetailView.as_view(), name='seasonal-pattern-detail'),
    
    # Model Management
    path('models/', ForecastModelListView.as_view(), name='model-list'),
    path('models/accuracy/', ForecastAccuracyView.as_view(), name='model-accuracy'),
]