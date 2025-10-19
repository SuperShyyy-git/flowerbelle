"""
Reports API Testing Script
Usage: python test_reports_api.py
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

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

def test_dashboard_overview(token):
    print_info("\n1. Testing Dashboard Overview...")
    
    response = requests.get(
        f"{BASE_URL}/reports/dashboard/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("Dashboard retrieved!")
        print(f"   Today's Sales: ₱{data['today_sales']}")
        print(f"   Today's Transactions: {data['today_transactions']}")
        print(f"   Today's Profit: ₱{data['today_profit']}")
        print(f"   Week Sales: ₱{data['week_sales']}")
        print(f"   Month Sales: ₱{data['month_sales']}")
        print(f"   Total Products: {data['total_products']}")
        print(f"   Low Stock Alerts: {data['low_stock_count']}")
        print(f"   Inventory Value: ₱{data['inventory_value']}")
    else:
        print_error(f"Failed: {response.json()}")

def test_sales_analytics(token):
    print_info("\n2. Testing Sales Analytics...")
    
    response = requests.get(
        f"{BASE_URL}/reports/analytics/sales/?period=month",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("Sales analytics retrieved!")
        print(f"   Period: {data['period']}")
        print(f"   Total Sales: ₱{data['total_sales']}")
        print(f"   Total Transactions: {data['total_transactions']}")
        print(f"   Total Profit: ₱{data['total_profit']}")
        print(f"   Profit Margin: {data['profit_margin']}%")
        print(f"   Sales Growth: {data['sales_growth']}%")
    else:
        print_error(f"Failed: {response.json()}")

def test_inventory_analytics(token):
    print_info("\n3. Testing Inventory Analytics...")
    
    response = requests.get(
        f"{BASE_URL}/reports/analytics/inventory/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("Inventory analytics retrieved!")
        print(f"   Total Products: {data['total_products']}")
        print(f"   Inventory Value: ₱{data['total_inventory_value']}")
        print(f"   Low Stock: {data['low_stock_count']}")
        print(f"   Out of Stock: {data['out_of_stock_count']}")
    else:
        print_error(f"Failed: {response.json()}")

def test_profit_loss(token):
    print_info("\n4. Testing Profit & Loss Report...")
    
    response = requests.get(
        f"{BASE_URL}/reports/profit-loss/?period=month",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("P&L report retrieved!")
        print(f"   Gross Sales: ₱{data['gross_sales']}")
        print(f"   Net Sales: ₱{data['net_sales']}")
        print(f"   COGS: ₱{data['cost_of_goods_sold']}")
        print(f"   Gross Profit: ₱{data['gross_profit']} ({data['gross_profit_margin']}%)")
        print(f"   Net Profit: ₱{data['net_profit']} ({data['net_profit_margin']}%)")
    else:
        print_error(f"Failed: {response.json()}")

def test_staff_performance(token):
    print_info("\n5. Testing Staff Performance...")
    
    response = requests.get(
        f"{BASE_URL}/reports/staff-performance/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Staff performance retrieved! ({len(data)} staff)")
        for staff in data:
            print(f"   - {staff['staff_name']}: ₱{staff['total_sales']} ({staff['total_transactions']} txns)")
    else:
        print_error(f"Failed: {response.json()}")

def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Flowerbelle Reports API Testing Script{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    token = get_token()
    if not token:
        return
    
    test_dashboard_overview(token)
    test_sales_analytics(token)
    test_inventory_analytics(token)
    test_profit_loss(token)
    test_staff_performance(token)
    
    print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}Testing completed!{Colors.END}")
    print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Testing interrupted{Colors.END}")
        