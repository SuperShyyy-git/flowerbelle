from django.urls import path
from django.http import JsonResponse
from .views import (
    LoginView, LogoutView, CurrentUserView,
    UserListCreateView, UserDetailView,
    ChangePasswordView, AuditLogListView
)

app_name = 'accounts'

urlpatterns = [
    # Root API endpoint
    path('', lambda request: JsonResponse({
        "message": "Accounts API root",
        "endpoints": [
            "login/",
            "logout/",
            "me/",
            "change-password/",
            "users/",
            "users/<id>/",
            "audit-logs/"
        ]
    })),

    # Authentication
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

    # User Management
    path('users/', UserListCreateView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),

    # Audit Logs
    path('audit-logs/', AuditLogListView.as_view(), name='audit-logs'),
]
