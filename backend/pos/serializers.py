from rest_framework import serializers
from django.db import transaction
from .models import SalesTransaction, TransactionItem, Cart, CartItem, PaymentTransaction
from inventory.models import Product


class TransactionItemSerializer(serializers.ModelSerializer):
    """Serializer for transaction items"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True)
    profit = serializers.ReadOnlyField()
    
    class Meta:
        model = TransactionItem
        fields = ('id', 'product', 'product_name', 'product_sku', 'product_image',
                 'quantity', 'unit_price', 'discount', 'line_total', 'profit', 'notes')
        read_only_fields = ('id', 'line_total')


class TransactionItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transaction items"""
    
    class Meta:
        model = TransactionItem
        fields = ('product', 'quantity', 'unit_price', 'discount', 'notes')
    
    def validate_quantity(self, value):
        """Ensure quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value
    
    def validate(self, data):
        """Validate stock availability"""
        product = data.get('product')
        quantity = data.get('quantity')
        
        if product.current_stock < quantity:
            raise serializers.ValidationError({
                "quantity": f"Insufficient stock. Available: {product.current_stock}"
            })
        
        return data


class SalesTransactionListSerializer(serializers.ModelSerializer):
    """Serializer for transaction list view"""
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    item_count = serializers.ReadOnlyField()
    
    class Meta:
        model = SalesTransaction
        fields = ('id', 'transaction_number', 'total_amount', 'payment_method',
                 'payment_method_display', 'status', 'status_display', 'item_count',
                 'customer_name', 'created_by', 'created_by_name', 'created_at')


class SalesTransactionDetailSerializer(serializers.ModelSerializer):
    """Serializer for transaction detail view"""
    items = TransactionItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    voided_by_name = serializers.CharField(source='voided_by.full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    item_count = serializers.ReadOnlyField()
    profit = serializers.ReadOnlyField()
    
    class Meta:
        model = SalesTransaction
        fields = ('id', 'transaction_number', 'subtotal', 'tax', 'discount', 'total_amount',
                 'payment_method', 'payment_method_display', 'payment_reference',
                 'amount_paid', 'change_amount', 'status', 'status_display', 'notes',
                 'customer_name', 'customer_phone', 'customer_email',
                 'items', 'item_count', 'profit',
                 'created_by', 'created_by_name', 'created_at', 'updated_at',
                 'completed_at', 'voided_by', 'voided_by_name', 'voided_at', 'void_reason')


class SalesTransactionCreateSerializer(serializers.Serializer):
    """Serializer for creating a sales transaction"""
    items = TransactionItemCreateSerializer(many=True)
    payment_method = serializers.ChoiceField(choices=SalesTransaction.PAYMENT_METHODS)
    payment_reference = serializers.CharField(required=False, allow_blank=True)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    tax = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, min_value=0)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        """Ensure at least one item"""
        if not value:
            raise serializers.ValidationError("At least one item is required")
        return value
    
    def validate(self, data):
        """Validate payment amount"""
        items = data.get('items', [])
        tax = data.get('tax', 0)
        discount = data.get('discount', 0)
        amount_paid = data.get('amount_paid')
        
        # Calculate total
        subtotal = sum(
            (item['unit_price'] * item['quantity']) - item.get('discount', 0)
            for item in items
        )
        total = subtotal + tax - discount
        
        if amount_paid < total:
            raise serializers.ValidationError({
                "amount_paid": f"Insufficient payment. Total: ₱{total:.2f}"
            })
        
        data['calculated_subtotal'] = subtotal
        data['calculated_total'] = total
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Create transaction with items"""
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        
        subtotal = validated_data.pop('calculated_subtotal')
        total = validated_data.pop('calculated_total')
        
        # Create transaction
        sales_transaction = SalesTransaction.objects.create(
            subtotal=subtotal,
            total_amount=total,
            created_by=user,
            change_amount=validated_data['amount_paid'] - total,
            **validated_data
        )
        
        # Create transaction items
        for item_data in items_data:
            TransactionItem.objects.create(
                transaction=sales_transaction,
                **item_data
            )
        
        # Complete the transaction (updates inventory)
        sales_transaction.complete_transaction()
        
        return sales_transaction


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True)
    product_stock = serializers.IntegerField(source='product.current_stock', read_only=True)
    line_total = serializers.ReadOnlyField()
    
    class Meta:
        model = CartItem
        fields = ('id', 'product', 'product_name', 'product_sku', 'product_image',
                 'product_stock', 'quantity', 'unit_price', 'line_total', 'added_at')
        read_only_fields = ('id', 'unit_price', 'added_at')


class CartSerializer(serializers.ModelSerializer):
    """Serializer for cart"""
    cart_items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.ReadOnlyField()
    subtotal = serializers.ReadOnlyField()
    
    class Meta:
        model = Cart
        fields = ('id', 'session_id', 'cart_items', 'item_count', 'subtotal',
                 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'session_id', 'created_at', 'updated_at')


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    
    def validate_product_id(self, value):
        """Ensure product exists and is active"""
        try:
            product = Product.objects.get(id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or inactive")
        return value
    
    def validate(self, data):
        """Validate stock availability"""
        try:
            product = Product.objects.get(id=data['product_id'])
            if product.current_stock < data['quantity']:
                raise serializers.ValidationError({
                    "quantity": f"Insufficient stock. Available: {product.current_stock}"
                })
        except Product.DoesNotExist:
            pass
        
        return data


class VoidTransactionSerializer(serializers.Serializer):
    """Serializer for voiding a transaction"""
    reason = serializers.CharField(max_length=500)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transactions"""
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = ('id', 'sales_transaction', 'payment_method', 'payment_method_display',
                 'amount', 'reference_number', 'authorization_code', 'status',
                 'status_display', 'card_last_four', 'created_at', 'processed_at')
        read_only_fields = ('id', 'created_at', 'processed_at')


class SalesReportSerializer(serializers.Serializer):
    """Serializer for sales reports"""
    total_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_transactions = serializers.IntegerField()
    total_items_sold = serializers.IntegerField()
    total_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_transaction = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # By payment method
    cash_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    card_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    digital_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Top products
    top_products = serializers.ListField(child=serializers.DictField())
    
    # Daily breakdown
    daily_sales = serializers.ListField(child=serializers.DictField())
