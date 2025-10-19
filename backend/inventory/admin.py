from django.contrib import admin
from .models import Category, Supplier, Product, InventoryMovement, LowStockAlert


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_person', 'phone', 'email')
    ordering = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'current_stock', 'reorder_level', 
                   'unit_price', 'is_low_stock', 'is_active')
    list_filter = ('category', 'is_active', 'supplier', 'created_at')
    search_fields = ('sku', 'name', 'barcode')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('sku', 'name', 'category', 'supplier', 'description', 'image')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'unit_price')
        }),
        ('Inventory', {
            'fields': ('current_stock', 'reorder_level', 'barcode', 'expiry_date')
        }),
        ('Status', {
            'fields': ('is_active', 'created_by', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new product
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'stock_before', 
                   'stock_after', 'created_by', 'created_at')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('product__name', 'product__sku', 'reference_number')
    readonly_fields = ('stock_before', 'stock_after', 'created_at', 'created_by')
    ordering = ('-created_at',)
    
    def has_delete_permission(self, request, obj=None):
        return False  # Inventory movements should not be deleted


@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    readonly_fields = ('current_stock',)