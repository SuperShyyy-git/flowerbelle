"""
Machine Learning Utilities for Demand Forecasting
Fixed version with proper error handling and flexible imports
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import pickle


def get_transaction_model():
    """
    Import the SalesTransaction model from pos app
    """
    try:
        from pos.models import SalesTransaction
        print(f"✅ Found SalesTransaction model in pos.models")
        return SalesTransaction
    except ImportError as e:
        raise ImportError(
            f"Could not import SalesTransaction from pos.models: {str(e)}"
        )


def prepare_training_data(product, days=90):
    """
    Prepare training data from product sales history
    Returns: X (features), y (targets), dates
    """
    try:
        SalesTransaction = get_transaction_model()
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get daily sales data from TransactionItem
        # We need to import TransactionItem to access the items
        from pos.models import TransactionItem
        
        # Query TransactionItem and aggregate by date
        from django.db.models.functions import TruncDate
        
        sales_data = TransactionItem.objects.filter(
            product=product,
            transaction__created_at__date__gte=start_date,
            transaction__created_at__date__lte=end_date,
            transaction__status='COMPLETED'  # Only count completed transactions
        ).annotate(
            date=TruncDate('transaction__created_at')
        ).values('date').annotate(
            total_quantity=Sum('quantity')
        ).order_by('date')
        
        # Convert to list
        sales_list = list(sales_data)
        
        if len(sales_list) < 14:  # Need at least 2 weeks of data
            print(f"⚠️ Insufficient sales data: only {len(sales_list)} days found")
            return None, None, None
        
        # Create DataFrame with proper error handling
        dates = []
        quantities = []
        
        for record in sales_list:
            dates.append(record['date'])
            quantities.append(record['total_quantity'])
        
        # Create pandas DataFrame safely
        df = pd.DataFrame({
            'date': dates,
            'quantity': quantities
        })
        
        # Fill missing dates with 0
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').reindex(date_range, fill_value=0).reset_index()
        df.columns = ['date', 'quantity']
        
        # Create features
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Create lag features (previous days' sales)
        df['lag_1'] = df['quantity'].shift(1).fillna(0)
        df['lag_7'] = df['quantity'].shift(7).fillna(0)
        df['rolling_mean_7'] = df['quantity'].rolling(window=7, min_periods=1).mean()
        df['rolling_mean_14'] = df['quantity'].rolling(window=14, min_periods=1).mean()
        
        # Remove NaN values
        df = df.fillna(0)
        
        # Prepare features and target
        feature_columns = [
            'day_of_week', 'day_of_month', 'month', 'is_weekend',
            'lag_1', 'lag_7', 'rolling_mean_7', 'rolling_mean_14'
        ]
        
        X = df[feature_columns].values
        y = df['quantity'].values
        dates = df['date'].values
        
        print(f"✅ Prepared {len(X)} samples for training")
        return X, y, dates
        
    except ImportError as ie:
        print(f"❌ Import error: {str(ie)}")
        print("Please check that pos.models contains SalesTransaction and TransactionItem")
        return None, None, None
    except Exception as e:
        print(f"❌ Error preparing training data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None


def train_linear_regression_model(product, days=90):
    """
    Train a linear regression model for demand forecasting
    Returns: model, scaler, metrics, training_info
    """
    try:
        # Prepare data
        X, y, dates = prepare_training_data(product, days)
        
        if X is None or len(X) < 14:
            print(f"⚠️ Cannot train model: insufficient data")
            return None, None, None, None
        
        # Split into train/test
        split_index = int(len(X) * 0.8)
        X_train, X_test = X[:split_index], X[split_index:]
        y_train, y_test = y[:split_index], y[split_index:]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        model = LinearRegression()
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test_scaled)
        
        # Calculate metrics
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Calculate accuracy (within 20% of actual)
        percentage_errors = np.abs((y_test - y_pred) / (y_test + 1)) * 100
        accuracy = np.mean(percentage_errors <= 20) * 100
        
        metrics = {
            'mse': float(mse),
            'rmse': float(rmse),
            'mae': float(mae),
            'r2_score': float(r2),
            'accuracy': float(accuracy)
        }
        
        training_info = {
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'features_used': 8,
            'training_period_days': days
        }
        
        print(f"✅ Model trained successfully - Accuracy: {accuracy:.2f}%")
        return model, scaler, metrics, training_info
        
    except Exception as e:
        print(f"❌ Error training model: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None, None


def predict_demand(model, scaler, product, forecast_date, historical_data=None):
    """
    Predict demand for a specific date
    Returns: prediction, confidence_interval
    """
    try:
        # Create features for the forecast date
        day_of_week = forecast_date.weekday()
        day_of_month = forecast_date.day
        month = forecast_date.month
        is_weekend = 1 if day_of_week in [5, 6] else 0
        
        # Use historical data for lag features
        if historical_data and len(historical_data) > 0:
            lag_1 = historical_data[-1] if len(historical_data) >= 1 else 0
            lag_7 = historical_data[-7] if len(historical_data) >= 7 else 0
            rolling_mean_7 = np.mean(historical_data[-7:]) if len(historical_data) >= 7 else 0
            rolling_mean_14 = np.mean(historical_data[-14:]) if len(historical_data) >= 14 else 0
        else:
            # Use product's average daily sales as fallback
            lag_1 = product.current_stock / 30  # Rough estimate
            lag_7 = lag_1
            rolling_mean_7 = lag_1
            rolling_mean_14 = lag_1
        
        # Create feature array
        features = np.array([[
            day_of_week, day_of_month, month, is_weekend,
            lag_1, lag_7, rolling_mean_7, rolling_mean_14
        ]])
        
        # Scale features
        features_scaled = scaler.transform(features)
        
        # Make prediction
        prediction = model.predict(features_scaled)[0]
        
        # Ensure non-negative prediction
        prediction = max(0, int(prediction))
        
        # Calculate confidence interval (±20%)
        conf_lower = max(0, int(prediction * 0.8))
        conf_upper = int(prediction * 1.2)
        
        return prediction, (conf_lower, conf_upper)
        
    except Exception as e:
        print(f"❌ Error making prediction: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return fallback prediction
        fallback = int(product.current_stock / 30)
        return fallback, (int(fallback * 0.8), int(fallback * 1.2))


def detect_seasonal_patterns(product, days=365):
    """
    Detect seasonal patterns in sales data
    Returns: list of seasonal periods
    """
    try:
        from pos.models import TransactionItem
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get monthly sales from TransactionItem
        monthly_sales = TransactionItem.objects.filter(
            product=product,
            transaction__created_at__date__gte=start_date,
            transaction__created_at__date__lte=end_date,
            transaction__status='COMPLETED'
        ).extra(
            select={'month': "EXTRACT(month FROM transaction__created_at)"}
        ).values('month').annotate(
            total_quantity=Sum('quantity')
        )
        
        if not monthly_sales:
            return []
        
        # Find peaks (months with sales > average)
        sales_list = list(monthly_sales)
        avg_sales = np.mean([s['total_quantity'] for s in sales_list])
        
        peaks = [
            {'month': s['month'], 'sales': s['total_quantity']}
            for s in sales_list
            if s['total_quantity'] > avg_sales * 1.5
        ]
        
        return peaks
        
    except Exception as e:
        print(f"❌ Error detecting seasonal patterns: {str(e)}")
        return []


def generate_stock_recommendation(product, forecast):
    """
    Generate stock recommendation based on forecast
    Returns: recommendation dict
    """
    try:
        current_stock = product.current_stock
        reorder_point = product.reorder_point or 0
        predicted_demand = forecast.predicted_demand
        
        # Calculate days until stockout
        if predicted_demand > 0:
            days_until_stockout = current_stock / predicted_demand
        else:
            days_until_stockout = 999
        
        # Determine priority
        if days_until_stockout < 7:
            priority = 'CRITICAL'
            action = 'URGENT_ORDER'
        elif days_until_stockout < 14:
            priority = 'HIGH'
            action = 'ORDER_SOON'
        elif current_stock < reorder_point:
            priority = 'MEDIUM'
            action = 'REORDER'
        else:
            priority = 'LOW'
            action = 'MONITOR'
        
        # Calculate recommended order quantity
        # Order enough for 30 days + safety stock
        safety_stock = int(predicted_demand * 7)  # 1 week safety stock
        recommended_order = max(0, (predicted_demand * 30) - current_stock + safety_stock)
        
        reason = f"Current stock: {current_stock}, Predicted demand: {predicted_demand}/day"
        if days_until_stockout < 999:
            reason += f", Days until stockout: {int(days_until_stockout)}"
        
        return {
            'priority': priority,
            'action': action,
            'recommended_order_quantity': int(recommended_order),
            'reason': reason,
            'days_until_stockout': int(days_until_stockout) if days_until_stockout < 999 else None
        }
        
    except Exception as e:
        print(f"❌ Error generating recommendation: {str(e)}")
        return {
            'priority': 'LOW',
            'action': 'MONITOR',
            'recommended_order_quantity': 0,
            'reason': 'Unable to generate recommendation',
            'days_until_stockout': None
        }