"""
Inventory API Testing Script
Run this to test your inventory endpoints
Usage: python test_inventory_api.py
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def get_token():
    """Get authentication token"""
    print_info("Getting authentication token...")
    username = input("Enter username (default: admin): ").strip() or "admin"
    password = input("Enter password: ").strip()
    
    response = requests.post(
        f"{BASE_URL}/auth/login/",
        json={"username": username, "password": password}
    )
    
    if response.status_code == 200:
        token = response.json()['access']
        print_success("Authenticated successfully!")
        return token
    else:
        print_error("Authentication failed!")
        return None

def test_create_category(token):
    """Test creating a category"""
    print_info("\n1. Testing Create Category...")
    
    data = {
        "name": "Test Roses",
        "description": "Beautiful rose arrangements",
        "is_active": True
    }
    
    response = requests.post(
        f"{BASE_URL}/inventory/categories/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        category = response.json()
        print_success(f"Category created! ID: {category['id']}, Name: {category['name']}")
        return category['id']
    else:
        print_error(f"Failed: {response.json()}")
        return None

def test_list_categories(token):
    """Test listing categories"""
    print_info("\n2. Testing List Categories...")
    
    response = requests.get(
        f"{BASE_URL}/inventory/categories/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        categories = response.json()
        print_success(f"Categories retrieved! Total: {len(categories)}")
        for cat in categories:
            print(f"   - {cat['name']} (Products: {cat['product_count']})")
    else:
        print_error(f"Failed: {response.json()}")

def test_create_supplier(token):
    """Test creating a supplier"""
    print_info("\n3. Testing Create Supplier...")
    
    data = {
        "name": "Test Flower Wholesaler",
        "contact_person": "John Supplier",
        "phone": "09171234567",
        "email": "john@supplier.com",
        "address": "123 Flower Street, Manila",
        "is_active": True
    }
    
    response = requests.post(
        f"{BASE_URL}/inventory/suppliers/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        supplier = response.json()
        print_success(f"Supplier created! ID: {supplier['id']}, Name: {supplier['name']}")
        return supplier['id']
    else:
        print_error(f"Failed: {response.json()}")
        return None

def test_create_product(token, category_id, supplier_id):
    """Test creating a product"""
    print_info("\n4. Testing Create Product...")
    
    if not category_id:
        print_error("Cannot create product without category")
        return None
    
    data = {
        "sku": f"TEST-{int(requests.get(f'{BASE_URL}/inventory/products/', headers={'Authorization': f'Bearer {token}'}).json().__len__() + 1)}",
        "name": "Test Red Rose Bouquet",
        "description": "Beautiful red roses in a bouquet",
        "category": category_id,
        "supplier": supplier_id,
        "unit_price": 500.00,
        "cost_price": 300.00,
        "current_stock": 50,
        "reorder_level": 10,
        "is_active": True
    }
    
    response = requests.post(
        f"{BASE_URL}/inventory/products/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        product = response.json()
        print_success(f"Product created! ID: {product['id']}, SKU: {product['sku']}")
        print(f"   Name: {product['name']}")
        print(f"   Price: ₱{product['unit_price']}, Stock: {product['current_stock']}")
        return product['id']
    else:
        print_error(f"Failed: {response.json()}")
        return None

def test_list_products(token):
    """Test listing products"""
    print_info("\n5. Testing List Products...")
    
    response = requests.get(
        f"{BASE_URL}/inventory/products/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        products = response.json()
        print_success(f"Products retrieved! Total: {len(products)}")
        for prod in products[:5]:  # Show first 5
            print(f"   - {prod['sku']}: {prod['name']} | Stock: {prod['current_stock']} | Price: ₱{prod['unit_price']}")
    else:
        print_error(f"Failed: {response.json()}")

def test_stock_in(token, product_id):
    """Test stock in movement"""
    print_info("\n6. Testing Stock In...")
    
    if not product_id:
        print_error("Cannot test stock in without product")
        return
    
    data = {
        "product": product_id,
        "movement_type": "STOCK_IN",
        "quantity": 20,
        "reference_number": "PO-2025-001",
        "reason": "Restocking from supplier"
    }
    
    response = requests.post(
        f"{BASE_URL}/inventory/movements/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        movement = response.json()
        print_success("Stock in recorded!")
        print(f"   Product: {movement['product_name']}")
        print(f"   Quantity: {movement['quantity']}")
        print(f"   Stock: {movement['stock_before']} → {movement['stock_after']}")
    else:
        print_error(f"Failed: {response.json()}")

def test_stock_out(token, product_id):
    """Test stock out movement"""
    print_info("\n7. Testing Stock Out...")
    
    if not product_id:
        print_error("Cannot test stock out without product")
        return
    
    data = {
        "product": product_id,
        "movement_type": "STOCK_OUT",
        "quantity": 5,
        "reference_number": "WO-2025-001",
        "reason": "Store display"
    }
    
    response = requests.post(
        f"{BASE_URL}/inventory/movements/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        movement = response.json()
        print_success("Stock out recorded!")
        print(f"   Product: {movement['product_name']}")
        print(f"   Quantity: {movement['quantity']}")
        print(f"   Stock: {movement['stock_before']} → {movement['stock_after']}")
    else:
        print_error(f"Failed: {response.json()}")

def test_inventory_movements(token):
    """Test listing inventory movements"""
    print_info("\n8. Testing List Inventory Movements...")
    
    response = requests.get(
        f"{BASE_URL}/inventory/movements/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        movements = response.json()
        print_success(f"Movements retrieved! Total: {len(movements)}")
        for mov in movements[:5]:  # Show first 5
            print(f"   - {mov['movement_type_display']}: {mov['product_name']} | Qty: {mov['quantity']} | {mov['created_at'][:10]}")
    else:
        print_error(f"Failed: {response.json()}")

def test_low_stock_alerts(token):
    """Test listing low stock alerts"""
    print_info("\n9. Testing Low Stock Alerts...")
    
    response = requests.get(
        f"{BASE_URL}/inventory/alerts/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        alerts = response.json()
        print_success(f"Alerts retrieved! Total: {len(alerts)}")
        for alert in alerts[:5]:
            print(f"   - {alert['product_name']} | Stock: {alert['current_stock']}/{alert['reorder_level']} | Status: {alert['status_display']}")
    else:
        print_error(f"Failed: {response.json()}")

def test_inventory_report(token):
    """Test inventory report"""
    print_info("\n10. Testing Inventory Report...")
    
    response = requests.get(
        f"{BASE_URL}/inventory/reports/inventory/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        report = response.json()
        print_success("Inventory report generated!")
        print(f"   Total Products: {report['total_products']}")
        print(f"   Active Products: {report['active_products']}")
        print(f"   Total Stock Value: ₱{report['total_stock_value']:.2f}")
        print(f"   Low Stock Count: {report['low_stock_count']}")
        print(f"   Out of Stock: {report['out_of_stock_count']}")
    else:
        print_error(f"Failed: {response.json()}")

def main():
    """Main test runner"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Flowerbelle Inventory API Testing Script{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    # Get authentication token
    token = get_token()
    if not token:
        return
    
    # Run tests
    category_id = test_create_category(token)
    test_list_categories(token)
    
    supplier_id = test_create_supplier(token)
    
    product_id = test_create_product(token, category_id, supplier_id)
    test_list_products(token)
    
    if product_id:
        test_stock_in(token, product_id)
        test_stock_out(token, product_id)
    
    test_inventory_movements(token)
    test_low_stock_alerts(token)
    test_inventory_report(token)
    
    print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}Testing completed!{Colors.END}")
    print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Testing interrupted by user{Colors.END}")
    except Exception as e:
        print_error(f"\nError occurred: {str(e)}")