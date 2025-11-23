"""
Quick API Testing Script (Corrected and Enhanced)
Run this to test your authentication endpoints
Usage: python test_api.py
"""

import requests
import json
import time # 💡 Added for unique timestamp

BASE_URL = "http://127.0.0.1:8000/api/auth"

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

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def api_request(method, url, headers=None, json_data=None):
    """Utility function to handle requests and network errors."""
    try:
        if method == 'GET':
            return requests.get(url, headers=headers)
        elif method == 'POST':
            return requests.post(url, headers=headers, json=json_data)
    except requests.exceptions.ConnectionError:
        print_error(f"Connection failed: Is the Django server running at {BASE_URL.split('/api')[0]}?")
        return None
    except Exception as e:
        print_error(f"An unexpected error occurred during API call: {e}")
        return None
    return None # Should not be reached

def test_login():
    """Test login endpoint"""
    print_info("\n1. Testing Login...")
    
    username = input("Enter username (default: admin): ").strip() or "admin"
    password = input("Enter password: ").strip()
    
    response = api_request(
        'POST',
        f"{BASE_URL}/login/",
        json_data={"username": username, "password": password}
    )
    
    if response is None:
        return None, None
    
    if response.status_code == 200:
        data = response.json()
        print_success("Login successful!")
        print(f"   Access Token: {data['access'][:50]}...")
        print(f"   Refresh Token: {data['refresh'][:50]}...")
        print(f"   User: {data['user']['username']} ({data['user']['role']})")
        return data['access'], data['refresh']
    else:
        print_error(f"Login failed: {response.json()}")
        return None, None

def test_current_user(token):
    """Test getting current user info"""
    print_info("\n2. Testing Get Current User...")
    
    response = api_request(
        'GET',
        f"{BASE_URL}/me/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response is None:
        return
    
    if response.status_code == 200:
        data = response.json()
        print_success("Current user retrieved!")
        print(f"   Username: {data['username']}")
        print(f"   Role: {data['role']}")
    else:
        print_error(f"Failed (Status {response.status_code}): {response.json()}")

def test_list_users(token):
    """Test listing all users (Owner only)"""
    print_info("\n3. Testing List Users (Owner only)...")
    
    response = api_request(
        'GET',
        f"{BASE_URL}/users/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response is None:
        return
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Users retrieved! Total: {len(data)}")
        for user in data:
            print(f"   - {user['username']} ({user['role']}) - Active: {user['is_active']}")
    elif response.status_code == 403:
        print_warning("Access denied (403 Forbidden) - Only owners can list users")
    else:
        print_error(f"Failed (Status {response.status_code}): {response.json()}")

def test_create_user(token):
    """Test creating a new user (Owner only) using unique data"""
    print_info("\n4. Testing Create User (Owner only)...")
    
    create = input("Do you want to create a test user? (y/n): ").strip().lower()
    if create != 'y':
        print_warning("Skipped creating user")
        return
    
    # 💡 Use a timestamp to ensure unique username/email every run
    timestamp = str(int(time.time()))
    
    new_user = {
        "username": f"teststaff_{timestamp}",
        "email": f"staff_{timestamp}@flowerbelle.com",
        "full_name": "Test Staff Member",
        "role": "STAFF",
        "phone": "09171234567",
        "password": "testpass123",
        "password_confirm": "testpass123"
    }
    
    response = api_request(
        'POST',
        f"{BASE_URL}/users/",
        headers={"Authorization": f"Bearer {token}"},
        json_data=new_user
    )

    if response is None:
        return
    
    if response.status_code == 201:
        data = response.json()
        print_success("User created successfully!")
        print(f"   Username: {data['username']}")
        print(f"   Role: {data['role']}")
    elif response.status_code == 403:
        print_warning("Access denied (403 Forbidden) - Only owners can create users")
    else:
        print_error(f"Failed (Status {response.status_code}): {response.json()}")

def test_change_password(token):
    """Test changing password"""
    print_info("\n5. Testing Change Password...")
    
    change = input("Do you want to test password change? (y/n): ").strip().lower()
    if change != 'y':
        print_warning("Skipped password change")
        return
    
    old_pass = input("Enter current password: ").strip()
    new_pass = input("Enter new password: ").strip()
    confirm_pass = input("Confirm new password: ").strip()
    
    response = api_request(
        'POST',
        f"{BASE_URL}/change-password/",
        headers={"Authorization": f"Bearer {token}"},
        json_data={
            "old_password": old_pass,
            "new_password": new_pass,
            "new_password_confirm": confirm_pass
        }
    )
    
    if response is None:
        return
        
    if response.status_code == 200:
        print_success("Password changed successfully!")
        print_warning("Note: You'll need to login again with the new password")
    else:
        print_error(f"Failed (Status {response.status_code}): {response.json()}")

def test_audit_logs(token):
    """Test getting audit logs (Owner only)"""
    print_info("\n6. Testing Audit Logs (Owner only)...")
    
    response = api_request(
        'GET',
        f"{BASE_URL}/audit-logs/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response is None:
        return
        
    if response.status_code == 200:
        data = response.json()
        print_success(f"Audit logs retrieved! Total: {len(data)}")
        for log in data[:5]:  # Show last 5
            print(f"   - {log['user_name']} | {log['action']} | {log['timestamp']}")
    elif response.status_code == 403:
        print_warning("Access denied (403 Forbidden) - Only owners can view audit logs")
    else:
        print_error(f"Failed (Status {response.status_code}): {response.json()}")

def test_refresh_token(refresh_token):
    """💡 NEW: Test token refresh endpoint"""
    print_info("\n7. Testing Token Refresh...")
    
    response = api_request(
        'POST',
        f"{BASE_URL}/token/refresh/",
        json_data={"refresh": refresh_token}
    )
    
    if response is None:
        return None
        
    if response.status_code == 200:
        data = response.json()
        print_success("Token refresh successful! New access token retrieved.")
        return data['access']
    else:
        print_error(f"Token refresh failed (Status {response.status_code}): {response.json()}")
        return None

def test_logout(token):
    """Test logout"""
    print_info("\n8. Testing Logout...")
    
    response = api_request(
        'POST',
        f"{BASE_URL}/logout/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response is None:
        return
        
    if response.status_code == 200:
        print_success("Logged out successfully!")
    else:
        print_error(f"Failed (Status {response.status_code}): {response.json()}")

def main():
    """Main test runner"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Flowerbelle API Testing Script{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    print_warning("\nMake sure the Django server is running on http://127.0.0.1:8000")
    input("Press Enter to continue...")
    
    # 1. Test login first
    access_token, refresh_token = test_login()
    
    if not access_token:
        print_error("\nCannot continue without valid token. Exiting...")
        return
    
    # 2. Run initial tests
    test_current_user(access_token)
    test_list_users(access_token)
    test_create_user(access_token)
    
    # 3. Test token refresh (Simulate token expiring after a few requests)
    if refresh_token:
        print_info("\n-- Simulating Token Expiration and Refresh --")
        new_access_token = test_refresh_token(refresh_token)
        
        if new_access_token:
            access_token = new_access_token # Use the new token for subsequent tests
            print_success("Switched to new access token for remaining tests.")
        else:
            print_warning("Refresh failed. Using original token for remaining tests (may fail).")

    # 4. Run final tests
    test_audit_logs(access_token)
    test_change_password(access_token)
    test_logout(access_token)
    
    print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}Testing completed!{Colors.END}")
    print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Testing interrupted by user{Colors.END}")
    except Exception as e:
        print_error(f"\nAn unexpected runtime error occurred: {str(e)}")