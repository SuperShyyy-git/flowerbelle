from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, AuditLog 


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (Read-only/Default)"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name', 'role', 'phone', 
                  'is_active', 'date_joined', 'last_login')
        read_only_fields = ('id', 'date_joined', 'last_login')


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users"""
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ('username', 'email', 'full_name', 'role', 'phone', 'password', 'password_confirm')
    
    def validate(self, data):
        """Validate password match"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data
    
    def create(self, validated_data):
        """Create user with hashed password"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information (used by Admin/Owner)"""
    
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    
    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone', 'is_active', 'role', 'password') 
    
    def update(self, instance, validated_data):
        """Custom update logic to hash the password if it's provided."""
        
        password = validated_data.pop('password', None)
        
        if password:
            instance.set_password(password)
        
        return super().update(instance, validated_data)


# 🌟 NEW SERIALIZER FOR STAFF SELF-EDIT
class UserSelfEditSerializer(serializers.ModelSerializer):
    """Serializer for staff/user self-editing (profile update)"""
    
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    
    class Meta:
        model = User
        # Restrict fields staff can change themselves
        fields = ('email', 'full_name', 'phone', 'password') 
        # Note: role and is_active are omitted
    
    def update(self, instance, validated_data):
        """Custom update logic to hash the password if it's provided."""
        
        password = validated_data.pop('password', None)
        
        if password:
            instance.set_password(password)
        
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def validate(self, data):
        """Validate new passwords match"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "New passwords do not match"})
        return data


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate(self, data):
        """Validate credentials and return user"""
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled")
                data['user'] = user
                return data
            else:
                raise serializers.ValidationError("Invalid username or password")
        else:
            raise serializers.ValidationError("Must include username and password")


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = ('id', 'user', 'user_name', 'action', 'table_name', 'record_id',
                  'old_values', 'new_values', 'ip_address', 'timestamp', 'description')
        read_only_fields = fields