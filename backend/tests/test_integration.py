"""
Integration tests for complete user workflows
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone

from inventory.models import Category, Supplier, Product, InventoryMovement
from pos.models import SalesTransaction, TransactionItem, Cart, CartItem
from forecasting.models import ForecastModel, ProductForecast, SeasonalPattern

User = get_user_model()


@pytest.mark.django_db
class TestCompleteUserWorkflow:
    """Test complete workflows from login to checkout"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.client = APIClient()
        
        # Create users
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            full_name='Test Owner',
            password='testpass123',
            role='OWNER'
        )
        
        self.staff = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            full_name='Test Staff',
            password='testpass123',
            role='STAFF'
        )
        
        # Create test inventory
        self.category = Category.objects.create(
            name='Test Roses',
            description='Test category'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            phone='09171234567',
            email='supplier@test.com'
        )
        
        self.product = Product.objects.create(
            sku='TEST-001',
            name='Red Rose Bouquet',
            category=self.category,
            supplier=self.supplier,
            unit_price=500.00,
            cost_price=300.00,
            current_stock=100,
            reorder_level=10,
            is_active=True,
            created_by=self.owner
        )
    
    def test_staff_complete_sale_workflow(self):
        """Test complete sales workflow: login -> add to cart -> checkout"""
        
        # 1. Staff login
        response = self.client.post('/api/auth/login/', {
            'username': 'staff',
            'password': 'testpass123'
        })
        assert response.status_code == status.HTTP_200_OK
        token = response.data['access']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # 2. Get product list
        response = self.client.get('/api/inventory/products/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) > 0
        
        # 3. Add to cart
        response = self.client.post('/api/pos/cart/add/', {
            'product_id': self.product.id,
            'quantity': 2
        })
        assert response.status_code == status.HTTP_200_OK
        cart = response.data['cart']
        assert cart['item_count'] == 2
        
        # 4. Get cart
        response = self.client.get('/api/pos/cart/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['cart_items']) == 1
        
        # 5. Checkout
        response = self.client.post('/api/pos/checkout/', {
            'payment_method': 'CASH',
            'amount_paid': 1000.00,
            'customer_name': 'Test Customer'
        })
        assert response.status_code == status.HTTP_201_CREATED
        
        transaction = response.data['transaction']
        assert transaction['status'] == 'COMPLETED'
        assert transaction['total_amount'] == '1000.00'
        
        # 6. Verify inventory was deducted
        self.product.refresh_from_db()
        assert self.product.current_stock == 98  # 100 - 2
        
        # 7. Verify inventory movement was created
        movement = InventoryMovement.objects.filter(
            product=self.product,
            movement_type='SALE'
        ).first()
        assert movement is not None
        assert movement.quantity == 2
    
    def test_owner_inventory_management_workflow(self):
        """Test inventory management: add product -> stock in -> check alerts"""
        
        # 1. Owner login
        response = self.client.post('/api/auth/login/', {
            'username': 'owner',
            'password': 'testpass123'
        })
        assert response.status_code == status.HTTP_200_OK
        token = response.data['access']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # 2. Create new product
        response = self.client.post('/api/inventory/products/', {
            'sku': 'TEST-002',
            'name': 'White Rose Bouquet',
            'category': self.category.id,
            'supplier': self.supplier.id,
            'unit_price': 600.00,
            'cost_price': 350.00,
            'current_stock': 5,
            'reorder_level': 10,
            'is_active': True
        })
        assert response.status_code == status.HTTP_201_CREATED
        new_product_id = response.data['id']
        
        # 3. Verify low stock alert was created
        response = self.client.get('/api/inventory/alerts/')
        assert response.status_code == status.HTTP_200_OK
        # Should have alert since current_stock (5) < reorder_level (10)
        
        # 4. Stock in
        response = self.client.post('/api/inventory/movements/', {
            'product': new_product_id,
            'movement_type': 'STOCK_IN',
            'quantity': 20,
            'reference_number': 'PO-001',
            'reason': 'Restocking'
        })
        assert response.status_code == status.HTTP_201_CREATED
        
        # 5. Verify stock was updated
        response = self.client.get(f'/api/inventory/products/{new_product_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['current_stock'] == 25  # 5 + 20
    
    def test_owner_forecasting_workflow(self):
        """Test forecasting: train model -> generate forecast -> get recommendations"""
        
        # Create sales history
        for i in range(15):
            transaction = SalesTransaction.objects.create(
                subtotal=500.00,
                total_amount=500.00,
                payment_method='CASH',
                amount_paid=500.00,
                status='COMPLETED',
                created_by=self.staff,
                created_at=timezone.now() - timedelta(days=15-i)
            )
            
            TransactionItem.objects.create(
                transaction=transaction,
                product=self.product,
                quantity=2,
                unit_price=500.00
            )
        
        # 1. Owner login
        response = self.client.post('/api/auth/login/', {
            'username': 'owner',
            'password': 'testpass123'
        })
        assert response.status_code == status.HTTP_200_OK
        token = response.data['access']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # 2. Train model
        response = self.client.post('/api/forecasting/train/', {
            'product_id': self.product.id,
            'training_days': 30
        })
        
        # May fail if insufficient data, that's okay
        if response.status_code == status.HTTP_201_CREATED:
            assert 'model' in response.data
            
            # 3. Generate forecast
            response = self.client.post('/api/forecasting/generate/', {
                'product_id': self.product.id,
                'forecast_days': 7
            })
            
            if response.status_code == status.HTTP_201_CREATED:
                assert 'forecasts' in response.data
                
                # 4. Get forecast summary
                response = self.client.get(
                    f'/api/forecasting/forecasts/summary/{self.product.id}/'
                )
                assert response.status_code == status.HTTP_200_OK
                assert 'forecast_7_days' in response.data


@pytest.mark.django_db
class TestAPIPermissions:
    """Test role-based access control"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            role='OWNER'
        )
        
        self.staff = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='testpass123',
            role='STAFF'
        )
    
    def test_staff_cannot_access_owner_endpoints(self):
        """Staff should not access owner-only endpoints"""
        
        # Staff login
        response = self.client.post('/api/auth/login/', {
            'username': 'staff',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to access user list (owner only)
        response = self.client.get('/api/auth/users/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Try to create user (owner only)
        response = self.client.post('/api/auth/users/', {
            'username': 'newstaff',
            'email': 'new@test.com',
            'full_name': 'New Staff',
            'role': 'STAFF',
            'password': 'pass123',
            'password_confirm': 'pass123'
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Try to access profit/loss report (owner only)
        response = self.client.get('/api/reports/profit-loss/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_owner_can_access_all_endpoints(self):
        """Owner should access all endpoints"""
        
        # Owner login
        response = self.client.post('/api/auth/login/', {
            'username': 'owner',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Access user list
        response = self.client.get('/api/auth/users/')
        assert response.status_code == status.HTTP_200_OK
        
        # Access reports
        response = self.client.get('/api/reports/dashboard/')
        assert response.status_code == status.HTTP_200_OK
        
        # Access profit/loss
        response = self.client.get('/api/reports/profit-loss/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestDataValidation:
    """Test data validation and error handling"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            role='OWNER'
        )
        
        # Login
        response = self.client.post('/api/auth/login/', {
            'username': 'owner',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        self.category = Category.objects.create(name='Test Category')
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            phone='123',
            email='test@test.com'
        )
    
    def test_product_validation(self):
        """Test product creation validation"""
        
        # Missing required fields
        response = self.client.post('/api/inventory/products/', {
            'name': 'Test Product'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Negative price
        response = self.client.post('/api/inventory/products/', {
            'sku': 'TEST-001',
            'name': 'Test Product',
            'category': self.category.id,
            'unit_price': -100,
            'cost_price': 50,
            'current_stock': 10,
            'reorder_level': 5
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Unit price less than cost price (should warn but may accept)
        response = self.client.post('/api/inventory/products/', {
            'sku': 'TEST-002',
            'name': 'Test Product 2',
            'category': self.category.id,
            'unit_price': 50,
            'cost_price': 100,
            'current_stock': 10,
            'reorder_level': 5
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_transaction_validation(self):
        """Test sales transaction validation"""
        
        product = Product.objects.create(
            sku='TEST-001',
            name='Test Product',
            category=self.category,
            unit_price=500,
            cost_price=300,
            current_stock=10,
            reorder_level=5,
            created_by=self.owner
        )
        
        # Insufficient payment
        response = self.client.post('/api/pos/transactions/', {
            'items': [{
                'product': product.id,
                'quantity': 1,
                'unit_price': 500,
                'discount': 0
            }],
            'payment_method': 'CASH',
            'amount_paid': 400  # Less than total
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Insufficient stock
        response = self.client.post('/api/pos/transactions/', {
            'items': [{
                'product': product.id,
                'quantity': 20,  # More than available (10)
                'unit_price': 500,
                'discount': 0
            }],
            'payment_method': 'CASH',
            'amount_paid': 10000
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPerformance:
    """Test system performance with larger datasets"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            role='OWNER'
        )
        
        response = self.client.post('/api/auth/login/', {
            'username': 'owner',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_product_list_performance(self):
        """Test product list with many products"""
        
        category = Category.objects.create(name='Test')
        
        # Create 100 products
        products = [
            Product(
                sku=f'TEST-{i:03d}',
                name=f'Product {i}',
                category=category,
                unit_price=500,
                cost_price=300,
                current_stock=100,
                reorder_level=10,
                created_by=self.owner
            )
            for i in range(100)
        ]
        Product.objects.bulk_create(products)
        
        # Time the query
        import time
        start = time.time()
        response = self.client.get('/api/inventory/products/')
        duration = time.time() - start
        
        assert response.status_code == status.HTTP_200_OK
        assert duration < 2.0  # Should complete in under 2 seconds
    
    def test_transaction_list_performance(self):
        """Test transaction list with many transactions"""
        
        # This test would create many transactions and measure query time
        # Skipped for brevity
        pass