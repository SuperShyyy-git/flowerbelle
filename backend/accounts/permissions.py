from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners to access certain views
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'OWNER'


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow owners full access, staff can only read
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.role == 'OWNER'