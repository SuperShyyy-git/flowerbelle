from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow users with the 'OWNER' role to access certain views
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'OWNER'


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow users with the 'OWNER' role full access, 
    while other authenticated users can only read.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.role == 'OWNER'


class IsUserAdmin(permissions.BasePermission):
    """
    Custom permission to allow users with the 'OWNER' role or Django's 'is_staff' 
    status full CRUD access over user management endpoints.
    """
    def has_permission(self, request, view):
        # Check if user is authenticated and has the 'OWNER' role OR is a staff member
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'OWNER' or request.user.is_staff)
        )