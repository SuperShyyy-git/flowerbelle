from django.urls import path
from .views import (
    CartView, AddToCartView, UpdateCartItemView, RemoveCartItemView, CheckoutView,
    SalesTransactionListCreateView, SalesTransactionDetailView, VoidTransactionView,
    SalesReportView, DailySalesView, StaffSalesView
)

app_name = 'pos'

urlpatterns = [
    path('transactions/', SalesTransactionListCreateView.as_view(), name='transaction-list'),
    path('transactions/<int:pk>/', SalesTransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/<int:pk>/void/', VoidTransactionView.as_view(), name='transaction-void'),

    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', AddToCartView.as_view(), name='cart-add'),
    path('cart/items/<int:pk>/', UpdateCartItemView.as_view(), name='cart-item-update'),
    path('cart/items/<int:pk>/remove/', RemoveCartItemView.as_view(), name='cart-item-remove'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),

    path('reports/sales/', SalesReportView.as_view(), name='sales-report'),
    path('reports/daily/', DailySalesView.as_view(), name='daily-sales'),
    path('reports/staff/', StaffSalesView.as_view(), name='staff-sales'),
]
