from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone  # MOVED TO TOP
from .models import User, AuditLog
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    ChangePasswordSerializer, LoginSerializer, AuditLogSerializer
)
from .permissions import IsOwner
from .utils import create_audit_log


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {"detail": "Use POST with username and password to log in."},
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        create_audit_log(
            user=user,
            action='LOGIN',
            table_name='users',
            request=request
        )
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })


class LogoutView(APIView):
    """Handle user logout"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        create_audit_log(
            user=request.user,
            action='LOGOUT',
            table_name='users',
            request=request
        )
        
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """Get current authenticated user details"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UserListCreateView(generics.ListCreateAPIView):
    """List all users or create a new user (Owner only)"""
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer
    
    def perform_create(self, serializer):
        user = serializer.save()
        
        create_audit_log(
            user=self.request.user,
            action='CREATE',
            table_name='users',
            record_id=user.id,
            new_values=UserSerializer(user).data,
            request=self.request
        )


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a user (Owner only)"""
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
    
    def perform_update(self, serializer):
        old_data = UserSerializer(self.get_object()).data
        user = serializer.save()
        
        create_audit_log(
            user=self.request.user,
            action='UPDATE',
            table_name='users',
            record_id=user.id,
            old_values=old_data,
            new_values=UserSerializer(user).data,
            request=self.request
        )
    
    def perform_destroy(self, instance):
        # Soft delete - deactivate instead of deleting
        instance.is_active = False
        instance.save()
        
        create_audit_log(
            user=self.request.user,
            action='DELETE',
            table_name='users',
            record_id=instance.id,
            description=f"Deactivated user: {instance.username}",
            request=self.request
        )


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'Incorrect password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        update_session_auth_hash(request, user)
        
        create_audit_log(
            user=user,
            action='UPDATE',
            table_name='users',
            record_id=user.id,
            description='Password changed',
            request=request
        )
        
        return Response({'message': 'Password changed successfully'})


class AuditLogListView(generics.ListAPIView):
    """List all audit logs (Owner only)"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        """Filter by user if user_id is provided"""
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset