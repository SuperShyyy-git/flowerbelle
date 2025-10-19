from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import User, AuditLog
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()


class UserModelTest(TestCase):
    """Test User model"""
    
    def setUp(self):
        """Set up test data"""
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
    
    def test_create_user(self):
        """Test creating a user"""
        self.assertEqual(self.owner.username, 'owner')
        self.assertEqual(self.owner.email, 'owner@test.com')
        self.assertTrue(self.owner.check_password('testpass123'))
    
    def test_user_roles(self):
        """Test user role properties"""
        self.assertTrue(self.owner.is_owner)
        self.assertFalse(self.owner.is_staff_member)
        
        self.assertFalse(self.staff.is_owner)
        self.assertTrue(self.staff.is_staff_member)
    
    def test_user_str(self):
        """Test user string representation"""
        self.assertEqual(str(self.owner), 'owner (Owner)')
        self.assertEqual(str(self.staff), 'staff (Staff)')


class AuthenticationAPITest(APITestCase):
    """Test authentication endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            full_name='Test User',
            password='testpass123',
            role='STAFF'
        )
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')
        self.me_url = reverse('accounts:current-user')
    
    def test_login_success(self):
        """Test successful login"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_missing_fields(self):
        """Test login with missing fields"""
        data = {'username': 'testuser'}
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_current_user(self):
        """Test getting current user info"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.me_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@test.com')
    
    def test_get_current_user_unauthenticated(self):
        """Test getting current user without authentication"""
        response = self.client.get(self.me_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_logout(self):
        """Test logout"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserManagementAPITest(APITestCase):
    """Test user management endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
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
        
        self.user_list_url = reverse('accounts:user-list')
    
    def test_list_users_as_owner(self):
        """Test listing users as owner"""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.user_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_list_users_as_staff(self):
        """Test listing users as staff (should fail)"""
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.user_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_user_as_owner(self):
        """Test creating user as owner"""
        self.client.force_authenticate(user=self.owner)
        
        data = {
            'username': 'newstaff',
            'email': 'newstaff@test.com',
            'full_name': 'New Staff',
            'role': 'STAFF',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        
        response = self.client.post(self.user_list_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'newstaff')
        
        # Verify user was created
        user_exists = User.objects.filter(username='newstaff').exists()
        self.assertTrue(user_exists)
    
    def test_create_user_password_mismatch(self):
        """Test creating user with password mismatch"""
        self.client.force_authenticate(user=self.owner)
        
        data = {
            'username': 'newstaff',
            'email': 'newstaff@test.com',
            'full_name': 'New Staff',
            'role': 'STAFF',
            'password': 'newpass123',
            'password_confirm': 'differentpass'
        }
        
        response = self.client.post(self.user_list_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_user_as_owner(self):
        """Test updating user as owner"""
        self.client.force_authenticate(user=self.owner)
        
        url = reverse('accounts:user-detail', kwargs={'pk': self.staff.id})
        data = {'full_name': 'Updated Staff Name'}
        
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify update
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.full_name, 'Updated Staff Name')
    
    def test_delete_user_as_owner(self):
        """Test deleting (deactivating) user as owner"""
        self.client.force_authenticate(user=self.owner)
        
        url = reverse('accounts:user-detail', kwargs={'pk': self.staff.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify user is deactivated
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)


class ChangePasswordAPITest(APITestCase):
    """Test password change endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            full_name='Test User',
            password='oldpass123',
            role='STAFF'
        )
        self.url = reverse('accounts:change-password')
    
    def test_change_password_success(self):
        """Test successful password change"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))
    
    def test_change_password_wrong_old_password(self):
        """Test password change with wrong old password"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'old_password': 'wrongpass',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_change_password_mismatch(self):
        """Test password change with new passwords not matching"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'differentpass'
        }
        
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuditLogTest(TestCase):
    """Test audit log functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            full_name='Test User',
            password='testpass123',
            role='STAFF'
        )
    
    def test_create_audit_log(self):
        """Test creating audit log"""
        log = AuditLog.objects.create(
            user=self.user,
            action='CREATE',
            table_name='products',
            record_id=1,
            new_values={'name': 'Rose Bouquet'},
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'CREATE')
        self.assertEqual(log.table_name, 'products')
    
    def test_audit_log_str(self):
        """Test audit log string representation"""
        log = AuditLog.objects.create(
            user=self.user,
            action='UPDATE',
            table_name='products',
            record_id=1
        )
        
        self.assertIn('testuser', str(log))
        self.assertIn('UPDATE', str(log))
        self.assertIn('products', str(log))
