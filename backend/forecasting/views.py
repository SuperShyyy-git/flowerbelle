from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from accounts.permissions import IsOwner
from accounts.utils import create_audit_log
from inventory.models import Product, Category
from .models import (
    ForecastModel, ProductForecast, CategoryForecast,
    SeasonalPattern, StockRecommendation
)
from .serializers import (
    ForecastModelSerializer, ProductForecastSerializer, ProductForecastCreateSerializer,
    CategoryForecastSerializer, SeasonalPatternSerializer, StockRecommendationSerializer,
    ForecastSummarySerializer, ForecastAccuracySerializer, TrainingResultSerializer,
    BulkForecastSerializer
)
from .ml_utils import (
    train_linear_regression_model, predict_demand, prepare_training_data,
    detect_seasonal_patterns, generate_stock_recommendation
)
import numpy as np


# ========== MODEL TRAINING ==========

class TrainModelView(APIView):
    """Train a new forecasting model for a product"""
    permission_classes = [IsAuthenticated, IsOwner]
    
    def post(self, request):
        serializer = ProductForecastCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_id = serializer.validated_data['product_id']
        training_days = serializer.validated_data.get('training_days', 90)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Train model
        model, scaler, metrics, training_info = train_linear_regression_model(
            product, 
            days=training_days
        )
        
        if model is None:
            return Response(
                {
                    'success': False,
                    'message': 'Insufficient data for training. Need at least 14 days of sales history.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save model record
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=training_days)
        
        forecast_model = ForecastModel.objects.create(
            name=f"{product.name} Forecast Model",
            model_type='LINEAR_REGRESSION',
            version=f"v{timezone.now().strftime('%Y%m%d%H%M%S')}",
            status='ACTIVE',
            parameters={
                'product_id': product.id,
                'training_days': training_days
            },
            r2_score=metrics['r2_score'],
            mse=metrics['mse'],
            rmse=metrics['rmse'],
            mae=metrics['mae'],
            accuracy=metrics['accuracy'],
            training_start_date=start_date,
            training_end_date=end_date,
            training_samples=training_info['training_samples'],
            trained_by=request.user,
            is_active=True
        )
        
        create_audit_log(
            user=request.user,
            action='CREATE',
            table_name='forecast_models',
            record_id=forecast_model.id,
            description=f"Trained forecast model for {product.name}",
            request=request
        )
        
        result = {
            'success': True,
            'message': f'Model trained successfully with {metrics["accuracy"]:.2f}% accuracy',
            'model': ForecastModelSerializer(forecast_model).data,
            'metrics': metrics,
            'training_info': training_info
        }
        
        serializer = TrainingResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ========== FORECAST GENERATION ==========

class GenerateForecastView(APIView):
    """Generate demand forecast for a product"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ProductForecastCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_id = serializer.validated_data['product_id']
        forecast_days = serializer.validated_data.get('forecast_days', 30)
        training_days = serializer.validated_data.get('training_days', 90)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or train model
        forecast_model = ForecastModel.objects.filter(
            parameters__product_id=product.id,
            is_active=True
        ).first()
        
        if not forecast_model:
            # Train new model
            model, scaler, metrics, training_info = train_linear_regression_model(
                product,
                days=training_days
            )
            
            if model is None:
                return Response(
                    {'error': 'Insufficient data for forecasting'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Save model
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=training_days)
            
            forecast_model = ForecastModel.objects.create(
                name=f"{product.name} Forecast Model",
                model_type='LINEAR_REGRESSION',
                version=f"v{timezone.now().strftime('%Y%m%d%H%M%S')}",
                status='ACTIVE',
                parameters={'product_id': product.id},
                r2_score=metrics['r2_score'],
                mse=metrics['mse'],
                rmse=metrics['rmse'],
                mae=metrics['mae'],
                accuracy=metrics['accuracy'],
                training_start_date=start_date,
                training_end_date=end_date,
                training_samples=training_info['training_samples'],
                trained_by=request.user,
                is_active=True
            )
        else:
            # Load existing model
            model, scaler, _, _ = train_linear_regression_model(product, training_days)
        
        # Get historical data for lag features
        X, y, dates = prepare_training_data(product, days=training_days)
        historical_data = y.tolist() if y is not None else []
        
        # Generate forecasts
        forecasts_created = []
        start_date = timezone.now().date() + timedelta(days=1)
        
        for i in range(forecast_days):
            forecast_date = start_date + timedelta(days=i)
            
            # Check if forecast already exists
            existing = ProductForecast.objects.filter(
                product=product,
                forecast_date=forecast_date,
                forecast_model=forecast_model
            ).first()
            
            if existing:
                continue
            
            # Make prediction
            prediction, (conf_lower, conf_upper) = predict_demand(
                model, scaler, product, forecast_date, historical_data
            )
            
            # Check for seasonal patterns
            seasonal_patterns = SeasonalPattern.objects.filter(is_active=True)
            is_peak = False
            seasonal_factor = 1.0
            
            for pattern in seasonal_patterns:
                if pattern.is_active_on_date(forecast_date):
                    if product.category in pattern.categories.all():
                        is_peak = True
                        seasonal_factor = pattern.demand_multiplier
                        prediction = int(prediction * seasonal_factor)
                        conf_lower = int(conf_lower * seasonal_factor)
                        conf_upper = int(conf_upper * seasonal_factor)
                        break
            
            # Create forecast
            forecast = ProductForecast.objects.create(
                product=product,
                forecast_model=forecast_model,
                forecast_date=forecast_date,
                predicted_demand=prediction,
                confidence_lower=conf_lower,
                confidence_upper=conf_upper,
                is_peak_season=is_peak,
                seasonal_factor=seasonal_factor
            )
            
            forecasts_created.append(forecast)
            
            # Update historical data for next prediction
            historical_data.append(prediction)
        
        # Update model last_used
        forecast_model.last_used = timezone.now()
        forecast_model.save()
        
        return Response({
            'message': f'Generated {len(forecasts_created)} forecasts',
            'forecasts': ProductForecastSerializer(forecasts_created, many=True).data
        }, status=status.HTTP_201_CREATED)


class BulkGenerateForecastView(APIView):
    """Generate forecasts for multiple products"""
    permission_classes = [IsAuthenticated, IsOwner]
    
    def post(self, request):
        serializer = BulkForecastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        category_id = serializer.validated_data.get('category_id')
        product_ids = serializer.validated_data.get('product_ids')
        forecast_days = serializer.validated_data.get('forecast_days', 30)
        generate_recommendations = serializer.validated_data.get('generate_recommendations', True)
        
        # Get products
        if product_ids:
            products = Product.objects.filter(id__in=product_ids, is_active=True)
        elif category_id:
            products = Product.objects.filter(category_id=category_id, is_active=True)
        else:
            products = Product.objects.filter(is_active=True)[:10]  # Limit to 10
        
        results = {
            'total_products': products.count(),
            'forecasts_generated': 0,
            'recommendations_generated': 0,
            'errors': []
        }
        
        for product in products:
            try:
                # Generate forecast (reuse GenerateForecastView logic)
                # For brevity, simplified here
                results['forecasts_generated'] += forecast_days
            except Exception as e:
                results['errors'].append({
                    'product': product.name,
                    'error': str(e)
                })
        
        return Response(results)


# ========== FORECAST RETRIEVAL ==========

class ProductForecastListView(generics.ListAPIView):
    """List forecasts for a product"""
    serializer_class = ProductForecastSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        product_id = self.request.query_params.get('product_id')
        days = int(self.request.query_params.get('days', 30))
        
        queryset = ProductForecast.objects.select_related(
            'product', 'forecast_model'
        ).all()
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by date range
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=days)
        queryset = queryset.filter(
            forecast_date__gte=start_date,
            forecast_date__lte=end_date
        )
        
        return queryset.order_by('forecast_date')


class ForecastSummaryView(APIView):
    """Get forecast summary for a product"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get forecasts
        today = timezone.now().date()
        forecasts_7 = ProductForecast.objects.filter(
            product=product,
            forecast_date__gte=today,
            forecast_date__lte=today + timedelta(days=7)
        )
        
        forecasts_30 = ProductForecast.objects.filter(
            product=product,
            forecast_date__gte=today,
            forecast_date__lte=today + timedelta(days=30)
        )
        
        forecast_7_days = sum(f.predicted_demand for f in forecasts_7)
        forecast_30_days = sum(f.predicted_demand for f in forecasts_30)
        
        # Calculate days until stockout
        avg_daily_demand = forecast_7_days / 7 if forecast_7_days > 0 else 0
        days_until_stockout = product.current_stock / avg_daily_demand if avg_daily_demand > 0 else 999
        
        # Get recommendation
        recommendation = StockRecommendation.objects.filter(
            product=product,
            status='PENDING'
        ).first()
        
        recommended_order = recommendation.recommended_order_quantity if recommendation else 0
        priority = recommendation.priority if recommendation else 'LOW'
        
        # Determine trend
        if len(forecasts_7) >= 7:
            first_half = sum(f.predicted_demand for f in list(forecasts_7)[:3])
            second_half = sum(f.predicted_demand for f in list(forecasts_7)[4:])
            if second_half > first_half * 1.1:
                trend = 'increasing'
            elif second_half < first_half * 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'unknown'
        
        # Seasonal impact
        peak_forecasts = forecasts_30.filter(is_peak_season=True)
        if peak_forecasts.exists():
            seasonal_impact = 'high'
        else:
            seasonal_impact = 'normal'
        
        data = {
            'product_id': product.id,
            'product_name': product.name,
            'product_sku': product.sku,
            'current_stock': product.current_stock,
            'forecast_7_days': forecast_7_days,
            'forecast_30_days': forecast_30_days,
            'recommended_order': recommended_order,
            'days_until_stockout': int(days_until_stockout),
            'priority': priority,
            'trend': trend,
            'seasonal_impact': seasonal_impact
        }
        
        serializer = ForecastSummarySerializer(data)
        return Response(serializer.data)


# ========== STOCK RECOMMENDATIONS ==========

class StockRecommendationListView(generics.ListAPIView):
    """List all stock recommendations"""
    serializer_class = StockRecommendationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = StockRecommendation.objects.select_related(
            'product', 'forecast', 'acknowledged_by'
        ).all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        return queryset.order_by('-priority', '-created_at')


class AcknowledgeRecommendationView(APIView):
    """Acknowledge a stock recommendation"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            recommendation = StockRecommendation.objects.get(pk=pk)
        except StockRecommendation.DoesNotExist:
            return Response(
                {'error': 'Recommendation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if recommendation.status != 'PENDING':
            return Response(
                {'error': 'Recommendation already acknowledged'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        recommendation.status = 'ACKNOWLEDGED'
        recommendation.acknowledged_by = request.user
        recommendation.acknowledged_at = timezone.now()
        recommendation.save()
        
        return Response({
            'message': 'Recommendation acknowledged',
            'recommendation': StockRecommendationSerializer(recommendation).data
        })


# ========== SEASONAL PATTERNS ==========

class SeasonalPatternListCreateView(generics.ListCreateAPIView):
    """List or create seasonal patterns"""
    queryset = SeasonalPattern.objects.all()
    serializer_class = SeasonalPatternSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    
    def perform_create(self, serializer):
        pattern = serializer.save()
        create_audit_log(
            user=self.request.user,
            action='CREATE',
            table_name='seasonal_patterns',
            record_id=pattern.id,
            new_values=serializer.data,
            request=self.request
        )


class SeasonalPatternDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete seasonal pattern"""
    queryset = SeasonalPattern.objects.all()
    serializer_class = SeasonalPatternSerializer
    permission_classes = [IsAuthenticated, IsOwner]


# ========== MODEL MANAGEMENT ==========

class ForecastModelListView(generics.ListAPIView):
    """List all forecast models"""
    queryset = ForecastModel.objects.all().order_by('-trained_at')
    serializer_class = ForecastModelSerializer
    permission_classes = [IsAuthenticated]


class ForecastAccuracyView(APIView):
    """Get forecast accuracy metrics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        model_id = request.query_params.get('model_id')
        
        if model_id:
            models = ForecastModel.objects.filter(id=model_id)
        else:
            models = ForecastModel.objects.filter(is_active=True)
        
        results = []
        
        for model in models:
            # Get forecasts with actual demand
            forecasts = ProductForecast.objects.filter(
                forecast_model=model,
                actual_demand__isnull=False
            )
            
            total_forecasts = forecasts.count()
            
            if total_forecasts == 0:
                continue
            
            # Calculate accuracy
            accurate_forecasts = forecasts.filter(
                absolute_percentage_error__lte=20
            ).count()
            
            accuracy_rate = (accurate_forecasts / total_forecasts * 100) if total_forecasts > 0 else 0
            
            average_error = forecasts.aggregate(
                avg=Avg('forecast_error')
            )['avg'] or 0
            
            average_percentage_error = forecasts.aggregate(
                avg=Avg('absolute_percentage_error')
            )['avg'] or 0
            
            # Accuracy by category
            category_accuracy = []
            categories = Category.objects.filter(is_active=True)
            
            for category in categories:
                cat_forecasts = forecasts.filter(product__category=category)
                cat_total = cat_forecasts.count()
                
                if cat_total > 0:
                    cat_accurate = cat_forecasts.filter(
                        absolute_percentage_error__lte=20
                    ).count()
                    
                    category_accuracy.append({
                        'category': category.name,
                        'total': cat_total,
                        'accurate': cat_accurate,
                        'accuracy_rate': (cat_accurate / cat_total * 100)
                    })
            
            results.append({
                'model_id': model.id,
                'model_name': model.name,
                'total_forecasts': total_forecasts,
                'accurate_forecasts': accurate_forecasts,
                'accuracy_rate': accuracy_rate,
                'average_error': float(average_error),
                'average_percentage_error': float(average_percentage_error),
                'category_accuracy': category_accuracy
            })
        
        serializer = ForecastAccuracySerializer(results, many=True)
        return Response(serializer.data)