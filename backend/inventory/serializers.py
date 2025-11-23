# inventory/serializers.py

from rest_framework import serializers
from .models import Category, Supplier, Product, InventoryMovement, LowStockAlert


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    product_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'is_active', 'product_count', 
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class SupplierSerializer(serializers.ModelSerializer):
    """Serializer for Supplier model"""
    
    class Meta:
        model = Supplier
        fields = ('id', 'name', 'contact_person', 'phone', 'email', 'address', 
                  'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer for Product list view (minimal data).
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    is_low_stock = serializers.ReadOnlyField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = (
            'id', 
            'sku', 
            'name', 
            'category',
            'category_name',
            'supplier_name',
            'unit_price',
            'cost_price',
            'current_stock',
            'reorder_level', 
            'is_low_stock', 
            'is_active', 
            'image',
            'image_url'
        )
    
    def get_image_url(self, obj):
        """Get absolute URL for product image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for Product detail view (complete data)"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    # Computed fields
    is_low_stock = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()
    stock_value = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = ('id', 'sku', 'name', 'description', 'category', 'category_name',
                  'supplier', 'supplier_name', 'unit_price', 'cost_price', 
                  'current_stock', 'reorder_level', 'image', 'image_url', 'barcode', 
                  'expiry_date', 'is_active', 'is_low_stock', 'profit_margin', 
                  'stock_value', 'is_expired', 'created_by', 'created_by_name', 
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by')
    
    def get_image_url(self, obj):
        """Get absolute URL for product image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating products"""
    
    class Meta:
        model = Product
        fields = ('sku', 'name', 'description', 'category', 'supplier', 
                  'unit_price', 'cost_price', 'current_stock', 'reorder_level',
                  'image', 'barcode', 'expiry_date', 'is_active')
    
    def validate_unit_price(self, value):
        """Ensure unit price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Unit price must be greater than 0")
        return value
    
    def validate_cost_price(self, value):
        """Ensure cost price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Cost price must be greater than 0")
        return value
    
    def validate(self, data):
        """Validate that unit price is not less than cost price"""
        unit_price = data.get('unit_price')
        cost_price = data.get('cost_price')
        
        if unit_price and cost_price and unit_price < cost_price:
            raise serializers.ValidationError({
                "unit_price": "Unit price should not be less than cost price"
            })
        
        return data


class InventoryMovementSerializer(serializers.ModelSerializer):
    """Serializer for Inventory Movement"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    
    class Meta:
        model = InventoryMovement
        fields = ('id', 'product', 'product_name', 'product_sku', 'movement_type',
                  'movement_type_display', 'quantity', 'stock_before', 'stock_after',
                  'reference_number', 'reason', 'notes', 'transaction_id',
                  'created_by', 'created_by_name', 'created_at')
        read_only_fields = ('id', 'stock_before', 'stock_after', 'created_by', 'created_at')


class InventoryMovementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating inventory movements"""
    
    class Meta:
        model = InventoryMovement
        fields = ('product', 'movement_type', 'quantity', 'reference_number', 
                  'reason', 'notes')
    
    def validate_quantity(self, value):
        """Ensure quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value
    
    def validate(self, data):
        """Validate stock availability for stock-out movements"""
        product = data.get('product')
        movement_type = data.get('movement_type')
        quantity = data.get('quantity')
        
        if movement_type in ['STOCK_OUT', 'SALE', 'DAMAGE']:
            if product.current_stock < quantity:
                raise serializers.ValidationError({
                    "quantity": f"Insufficient stock. Available: {product.current_stock}"
                })
        
        return data


class StockAdjustmentSerializer(serializers.Serializer):
    """Serializer for stock adjustments"""
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    new_stock_level = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(max_length=500)
    notes = serializers.CharField(required=False, allow_blank=True)


class LowStockAlertSerializer(serializers.ModelSerializer):
    """Serializer for Low Stock Alerts"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = LowStockAlert
        fields = ('id', 'product', 'product_name', 'product_sku', 'category_name',
                  'current_stock', 'reorder_level', 'status', 'status_display',
                  'created_at', 'acknowledged_at', 'acknowledged_by', 
                  'acknowledged_by_name', 'resolved_at')
        read_only_fields = ('id', 'product', 'current_stock', 'reorder_level',
                            'created_at', 'acknowledged_at', 'acknowledged_by', 'resolved_at')


class InventoryReportSerializer(serializers.Serializer):
    """Serializer for inventory reports"""
    total_products = serializers.IntegerField()
    active_products = serializers.IntegerField()
    total_stock_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    low_stock_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()
    expired_products_count = serializers.IntegerField()
    categories_count = serializers.IntegerField()
    
    # Top products
    top_selling = serializers.ListField(child=serializers.DictField())
    low_stock_products = serializers.ListField(child=serializers.DictField())