"""
Forecasting API Testing Script
Usage: python test_forecasting_api.py
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def get_token():
    username = input("Enter username (default: admin): ").strip() or "admin"
    password = input("Enter password: ").strip()
    
    response = requests.post(
        f"{BASE_URL}/auth/login/",
        json={"username": username, "password": password}
    )
    
    if response.status_code == 200:
        print_success("Authenticated successfully!")
        return response.json()['access']
    else:
        print_error("Authentication failed!")
        return None

def get_products(token):
    response = requests.get(
        f"{BASE_URL}/inventory/products/",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    return []

def test_train_model(token, product_id):
    print_info("\n1. Testing Model Training...")
    
    data = {
        "product_id": product_id,
        "training_days": 90,
        "forecast_days": 30
    }
    
    response = requests.post(
        f"{BASE_URL}/forecasting/train/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        result = response.json()
        print_success("Model trained successfully!")
        if result.get('model'):
            model = result['model']
            print(f"   Model: {model['name']}")
            print(f"   Accuracy: {model['accuracy']:.2f}%")
            print(f"   R² Score: {model['r2_score']:.4f}")
            print(f"   RMSE: {model['rmse']:.2f}")
            return model['id']
    else:
        print_error(f"Failed: {response.json()}")
    return None

def test_generate_forecast(token, product_id):
    print_info("\n2. Testing Forecast Generation...")
    
    data = {
        "product_id": product_id,
        "forecast_days": 30,
        "training_days": 90
    }
    
    response = requests.post(
        f"{BASE_URL}/forecasting/generate/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        result = response.json()
        print_success(f"{result['message']}")
        
        if result['forecasts']:
            print(f"   Sample forecasts:")
            for forecast in result['forecasts'][:5]:
                print(f"   - {forecast['forecast_date']}: {forecast['predicted_demand']} units "
                      f"(confidence: {forecast['confidence_lower']}-{forecast['confidence_upper']})")
    else:
        print_error(f"Failed: {response.json()}")

def test_forecast_summary(token, product_id):
    print_info("\n3. Testing Forecast Summary...")
    
    response = requests.get(
        f"{BASE_URL}/forecasting/forecasts/summary/{product_id}/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("Forecast summary retrieved!")
        print(f"   Product: {data['product_name']} ({data['product_sku']})")
        print(f"   Current Stock: {data['current_stock']}")
        print(f"   7-day Forecast: {data['forecast_7_days']} units")
        print(f"   30-day Forecast: {data['forecast_30_days']} units")
        print(f"   Days Until Stockout: {data['days_until_stockout']}")
        print(f"   Trend: {data['trend']}")
        print(f"   Seasonal Impact: {data['seasonal_impact']}")
        if data['recommended_order'] > 0:
            print(f"   Recommended Order: {data['recommended_order']} units ({data['priority']} priority)")
    else:
        print_error(f"Failed: {response.json()}")

def test_list_forecasts(token, product_id):
    print_info("\n4. Testing List Forecasts...")
    
    response = requests.get(
        f"{BASE_URL}/forecasting/forecasts/?product_id={product_id}&days=7",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        forecasts = response.json()
        print_success(f"Retrieved {len(forecasts)} forecasts")
        for forecast in forecasts:
            peak_indicator = " 🔥" if forecast['is_peak_season'] else ""
            print(f"   {forecast['forecast_date']}: {forecast['predicted_demand']} units{peak_indicator}")
    else:
        print_error(f"Failed: {response.json()}")

def test_seasonal_patterns(token):
    print_info("\n5. Testing Seasonal Patterns...")
    
    # Create a seasonal pattern
    data = {
        "name": "Valentine's Day Season",
        "season_type": "HOLIDAY",
        "start_month": 2,
        "start_day": 1,
        "end_month": 2,
        "end_day": 14,
        "demand_multiplier": 2.5,
        "description": "High demand for roses during Valentine's season",
        "is_active": True
    }
    
    response = requests.post(
        f"{BASE_URL}/forecasting/seasonal-patterns/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        pattern = response.json()
        print_success("Seasonal pattern created!")
        print(f"   Name: {pattern['name']}")
        print(f"   Period: {pattern['start_month']}/{pattern['start_day']} - {pattern['end_month']}/{pattern['end_day']}")
        print(f"   Multiplier: {pattern['demand_multiplier']}x")
    else:
        # Pattern might already exist
        print_warning("Pattern creation skipped (may already exist)")
    
    # List patterns
    response = requests.get(
        f"{BASE_URL}/forecasting/seasonal-patterns/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        patterns = response.json()
        print_success(f"Retrieved {len(patterns)} seasonal patterns")
        for pattern in patterns:
            print(f"   - {pattern['name']}: {pattern['demand_multiplier']}x demand")

def test_recommendations(token):
    print_info("\n6. Testing Stock Recommendations...")
    
    response = requests.get(
        f"{BASE_URL}/forecasting/recommendations/?status=PENDING",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        recommendations = response.json()
        print_success(f"Retrieved {len(recommendations)} recommendations")
        for rec in recommendations[:5]:
            print(f"   - {rec['product_name']}: Order {rec['recommended_order_quantity']} units")
            print(f"     Priority: {rec['priority_display']}")
            print(f"     Reason: {rec['reason'][:80]}...")
    else:
        print_error(f"Failed: {response.json()}")

def test_model_accuracy(token):
    print_info("\n7. Testing Model Accuracy...")
    
    response = requests.get(
        f"{BASE_URL}/forecasting/models/accuracy/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        results = response.json()
        if results:
            print_success(f"Retrieved accuracy for {len(results)} model(s)")
            for result in results:
                print(f"   Model: {result['model_name']}")
                print(f"   Total Forecasts: {result['total_forecasts']}")
                print(f"   Accuracy Rate: {result['accuracy_rate']:.2f}%")
                print(f"   Avg Error: {result['average_error']:.2f}")
        else:
            print_warning("No accuracy data available yet (need actual sales data)")
    else:
        print_error(f"Failed: {response.json()}")

def test_list_models(token):
    print_info("\n8. Testing List Models...")
    
    response = requests.get(
        f"{BASE_URL}/forecasting/models/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        models = response.json()
        print_success(f"Retrieved {len(models)} model(s)")
        for model in models:
            print(f"   - {model['name']} (v{model['version']})")
            print(f"     Status: {model['status_display']}, Accuracy: {model['accuracy']:.2f}%")
    else:
        print_error(f"Failed: {response.json()}")

def main():
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}Flowerbelle Forecasting API Testing Script{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}")
    
    token = get_token()
    if not token:
        return
    
    # Get products
    products = get_products(token)
    if not products:
        print_error("No products available for testing")
        return
    
    product_id = products[0]['id']
    print_info(f"\nUsing product: {products[0]['name']} (ID: {product_id})")
    
    # Run tests
    test_train_model(token, product_id)
    test_generate_forecast(token, product_id)
    test_forecast_summary(token, product_id)
    test_list_forecasts(token, product_id)
    test_seasonal_patterns(token)
    test_recommendations(token)
    test_model_accuracy(token)
    test_list_models(token)
    
    print(f"\n{Colors.GREEN}{'='*70}{Colors.END}")
    print(f"{Colors.GREEN}Testing completed!{Colors.END}")
    print(f"{Colors.GREEN}{'='*70}{Colors.END}\n")
    
    print_info("\nNote: To see accurate forecasts, ensure you have:")
    print("  1. At least 14 days of sales history")
    print("  2. Multiple transactions for the product")
    print("  3. Varied sales patterns over time")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Testing interrupted{Colors.END}")
    except Exception as e:
        print_error(f"\nError occurred: {str(e)}")