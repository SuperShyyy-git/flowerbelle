from django.urls import path
from .views import (
    # Categories
    CategoryListCreateView, CategoryDetailView,
    # Suppliers
    SupplierListCreateView, SupplierDetailView,
    # Products
    ProductListCreateView, ProductDetailView,
    # Inventory Movements
    InventoryMovementListCreateView, InventoryMovementDetailView,
    StockAdjustmentView,
    # Low Stock Alerts
    LowStockAlertListView, LowStockAlertDetailView,
    AcknowledgeAlertView, ResolveAlertView,
    # Reports
    InventoryReportView, CategoryReportView
)

app_name = 'inventory'

urlpatterns = [
    # Categories
    path('categories/', CategoryListCreateView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    
    # Suppliers
    path('suppliers/', SupplierListCreateView.as_view(), name='supplier-list'),
    path('suppliers/<int:pk>/', SupplierDetailView.as_view(), name='supplier-detail'),
    
    # Products
    path('products/', ProductListCreateView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    
    # Inventory Movements
    path('movements/', InventoryMovementListCreateView.as_view(), name='movement-list'),
    path('movements/<int:pk>/', InventoryMovementDetailView.as_view(), name='movement-detail'),
    path('stock-adjustment/', StockAdjustmentView.as_view(), name='stock-adjustment'),
    
    # Low Stock Alerts
    path('alerts/', LowStockAlertListView.as_view(), name='alert-list'),
    path('alerts/<int:pk>/', LowStockAlertDetailView.as_view(), name='alert-detail'),
    path('alerts/<int:pk>/acknowledge/', AcknowledgeAlertView.as_view(), name='alert-acknowledge'),
    path('alerts/<int:pk>/resolve/', ResolveAlertView.as_view(), name='alert-resolve'),
    
    # Reports
    path('reports/inventory/', InventoryReportView.as_view(), name='inventory-report'),
    path('reports/categories/', CategoryReportView.as_view(), name='category-report'),
]