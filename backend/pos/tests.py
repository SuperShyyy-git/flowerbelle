"""
POS API Testing Script
Run this to test your POS endpoints
Usage: python test_pos_api.py
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

def get_products(token):
    """Get available products"""
    response = requests.get(
        f"{BASE_URL}/inventory/products/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        return response.json()
    return []

def test_get_cart(token):
    """Test getting cart"""
    print_info("\n1. Testing Get Cart...")
    
    response = requests.get(
        f"{BASE_URL}/pos/cart/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        cart = response.json()
        print_success("Cart retrieved!")
        print(f"   Cart ID: {cart['id']}")
        print(f"   Items: {cart['item_count']}")
        print(f"   Subtotal: ₱{cart['subtotal']}")
        return cart
    else:
        print_error(f"Failed: {response.json()}")
        return None

def test_add_to_cart(token, product_id):
    """Test adding item to cart"""
    print_info("\n2. Testing Add to Cart...")
    
    if not product_id:
        print_error("No product ID provided")
        return
    
    data = {
        "product_id": product_id,
        "quantity": 2
    }
    
    response = requests.post(
        f"{BASE_URL}/pos/cart/add/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 200:
        cart = response.json()['cart']
        print_success("Item added to cart!")
        print(f"   Total items: {cart['item_count']}")
        print(f"   Subtotal: ₱{cart['subtotal']}")
        
        for item in cart['cart_items']:
            print(f"   - {item['product_name']} x{item['quantity']} = ₱{item['line_total']}")
        
        return cart
    else:
        print_error(f"Failed: {response.json()}")
        return None

def test_update_cart_item(token, cart_item_id):
    """Test updating cart item quantity"""
    print_info("\n3. Testing Update Cart Item...")
    
    if not cart_item_id:
        print_error("No cart item ID provided")
        return
    
    data = {"quantity": 3}
    
    response = requests.patch(
        f"{BASE_URL}/pos/cart/items/{cart_item_id}/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 200:
        cart = response.json()['cart']
        print_success("Cart item updated!")
        print(f"   New subtotal: ₱{cart['subtotal']}")
    else:
        print_error(f"Failed: {response.json()}")

def test_direct_transaction(token, product_id):
    """Test creating transaction directly (without cart)"""
    print_info("\n4. Testing Direct Transaction...")
    
    if not product_id:
        print_error("No product ID provided")
        return None
    
    data = {
        "items": [
            {
                "product": product_id,
                "quantity": 1,
                "unit_price": 500.00,
                "discount": 0
            }
        ],
        "payment_method": "CASH",
        "amount_paid": 500.00,
        "tax": 0,
        "discount": 0,
        "customer_name": "Test Customer"
    }
    
    response = requests.post(
        f"{BASE_URL}/pos/transactions/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        transaction = response.json()
        print_success("Transaction created!")
        print(f"   Transaction #: {transaction['transaction_number']}")
        print(f"   Total: ₱{transaction['total_amount']}")
        print(f"   Items: {transaction['item_count']}")
        print(f"   Status: {transaction['status_display']}")
        return transaction['id']
    else:
        print_error(f"Failed: {response.json()}")
        return None

def test_checkout(token):
    """Test cart checkout"""
    print_info("\n5. Testing Checkout...")
    
    data = {
        "payment_method": "CASH",
        "amount_paid": 1000.00,
        "customer_name": "Juan Dela Cruz",
        "customer_phone": "09171234567"
    }
    
    response = requests.post(
        f"{BASE_URL}/pos/checkout/",
        headers={"Authorization": f"Bearer {token}"},
        json=data
    )
    
    if response.status_code == 201:
        transaction = response.json()['transaction']
        print_success("Checkout successful!")
        print(f"   Transaction #: {transaction['transaction_number']}")
        print(f"   Total: ₱{transaction['total_amount']}")
        print(f"   Paid: ₱{transaction['amount_paid']}")
        print(f"   Change: ₱{transaction['change_amount']}")
        return transaction['id']
    else:
        print_error(f"Failed: {response.json()}")
        return None

def test_list_transactions(token):
    """Test listing transactions"""
    print_info("\n6. Testing List Transactions...")
    
    response = requests.get(
        f"{BASE_URL}/pos/transactions/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        transactions = response.json()
        print_success(f"Transactions retrieved! Total: {len(transactions)}")
        for txn in transactions[:5]:  # Show first 5
            print(f"   - {txn['transaction_number']} | ₱{txn['total_amount']} | {txn['status_display']} | {txn['created_at'][:10]}")
    else:
        print_error(f"Failed: {response.json()}")

def test_transaction_detail(token, transaction_id):
    """Test getting transaction details"""
    print_info("\n7. Testing Transaction Detail...")
    
    if not transaction_id:
        print_error("No transaction ID provided")
        return
    
    response = requests.get(
        f"{BASE_URL}/pos/transactions/{transaction_id}/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        txn = response.json()
        print_success("Transaction details retrieved!")
        print(f"   Transaction #: {txn['transaction_number']}")
        print(f"   Total: ₱{txn['total_amount']}")
        print(f"   Payment: {txn['payment_method_display']}")
        print(f"   Customer: {txn['customer_name']}")
        print(f"   Items:")
        for item in txn['items']:
            print(f"      - {item['product_name']} x{item['quantity']} = ₱{item['line_total']}")
    else:
        print_error(f"Failed: {response.json()}")

def test_daily_sales(token):
    """Test daily sales report"""
    print_info("\n8. Testing Daily Sales Report...")
    
    response = requests.get(
        f"{BASE_URL}/pos/reports/daily/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        report = response.json()
        print_success("Daily sales report generated!")
        print(f"   Date: {report['date']}")
        print(f"   Total Sales: ₱{report['total_sales']}")
        print(f"   Transactions: {report['total_transactions']}")
        print(f"   Profit: ₱{report['total_profit']}")
    else:
        print_error(f"Failed: {response.json()}")

def test_sales_report(token):
    """Test comprehensive sales report"""
    print_info("\n9. Testing Sales Report...")
    
    response = requests.get(
        f"{BASE_URL}/pos/reports/sales/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        report = response.json()
        print_success("Sales report generated!")
        print(f"   Total Sales: ₱{report['total_sales']}")
        print(f"   Total Transactions: {report['total_transactions']}")
        print(f"   Total Profit: ₱{report['total_profit']}")
        print(f"   Average Transaction: ₱{report['average_transaction']}")
        print(f"   Cash Sales: ₱{report['cash_sales']}")
        print(f"   Card Sales: ₱{report['card_sales']}")
        print(f"   Digital Sales: ₱{report['digital_sales']}")
    else:
        print_error(f"Failed: {response.json()}")

def main():
    """Main test runner"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Flowerbelle POS API Testing Script{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    # Get authentication token
    token = get_token()
    if not token:
        return
    
    # Get available products
    products = get_products(token)
    if not products:
        print_error("No products available for testing")
        return
    
    product_id = products[0]['id']
    print_info(f"\nUsing product: {products[0]['name']} (ID: {product_id})")
    
    # Run tests
    cart = test_get_cart(token)
    cart = test_add_to_cart(token, product_id)
    
    if cart and cart['cart_items']:
        cart_item_id = cart['cart_items'][0]['id']
        test_update_cart_item(token, cart_item_id)
        transaction_id = test_checkout(token)
    else:
        transaction_id = test_direct_transaction(token, product_id)
    
    test_list_transactions(token)
    
    if transaction_id:
        test_transaction_detail(token, transaction_id)
    
    test_daily_sales(token)
    test_sales_report(token)
    
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