from rest_framework import serializers
from .models import (
    SalesTransaction,
    TransactionItem,
    Cart,
    CartItem,
    PaymentTransaction
)
from inventory.models import Product, InventoryMovement, LowStockAlert
from django.db import transaction
from django.db.models import F
from decimal import Decimal

# ====================
# TRANSACTION ITEM SERIALIZER
# ====================
class TransactionItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    line_total = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TransactionItem
        fields = ['id', 'product', 'product_name', 'product_sku', 'quantity', 'unit_price', 'discount', 'line_total']

    def get_line_total(self, obj):
        return float((obj.unit_price * obj.quantity) - obj.discount)


# ====================
# SALES TRANSACTION SERIALIZERS
# ====================
class SalesTransactionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesTransaction
        fields = ['id', 'transaction_number', 'customer_name', 'total_amount', 'status', 'payment_method', 'created_at']


class SalesTransactionDetailSerializer(serializers.ModelSerializer):
    items = TransactionItemSerializer(many=True, read_only=True)

    class Meta:
        model = SalesTransaction
        fields = [
            'id', 'transaction_number', 'customer_name', 'customer_phone', 'customer_email',
            'items', 'total_amount', 'tax', 'discount', 'status', 'payment_method', 'created_by', 'created_at'
        ]


class SalesTransactionCreateSerializer(serializers.ModelSerializer):
    items = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = SalesTransaction
        fields = [
            'customer_name', 'customer_phone', 'customer_email', 'payment_method', 'payment_reference',
            'amount_paid', 'tax', 'discount', 'notes', 'items'
        ]

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])

        # Calculate subtotal
        calculated_subtotal = Decimal(0)
        for item in items_data:
            unit_price = Decimal(str(item.get('unit_price', 0)))
            quantity = Decimal(str(item.get('quantity', 0)))
            discount = Decimal(str(item.get('discount', 0)))
            calculated_subtotal += (unit_price * quantity) - discount

        tax = Decimal(str(validated_data.get('tax', 0)))
        discount = Decimal(str(validated_data.get('discount', 0)))
        amount_paid = Decimal(str(validated_data.get('amount_paid', 0)))

        total_amount = calculated_subtotal + tax - discount
        change_amount = amount_paid - total_amount

        # Set calculated totals
        validated_data['subtotal'] = float(calculated_subtotal)
        validated_data['total_amount'] = float(total_amount)
        validated_data['change_amount'] = float(max(Decimal('0.00'), change_amount))
        validated_data['status'] = 'COMPLETED'

        # Create transaction
        transaction_obj = SalesTransaction.objects.create(**validated_data)

        # Create transaction items and deduct stock
        for item in items_data:
            product_id = item.get('product_id') or item.get('product')
            product = Product.objects.select_for_update().get(id=product_id)

            quantity = int(item.get('quantity', 1))
            unit_price = float(item.get('unit_price', product.unit_price))
            discount = float(item.get('discount', 0))

            # Check stock
            if product.current_stock < quantity:
                raise serializers.ValidationError(f"Not enough stock for {product.name}")

            # ✅ FIX 1: Record stock BEFORE deduction for audit trail
            stock_before = product.current_stock

            # Deduct stock using F() expression for atomicity
            Product.objects.filter(pk=product.pk).update(
                current_stock=F('current_stock') - quantity
            )
            
            # Refresh to get updated stock
            product.refresh_from_db()
            stock_after = product.current_stock

            # Create transaction item
            TransactionItem.objects.create(
                transaction=transaction_obj,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                discount=discount
            )

            # ✅ FIX 2: Create InventoryMovement record for audit trail and alerts
            InventoryMovement.objects.create(
                product=product,
                movement_type='SALE',
                quantity=quantity,
                stock_before=stock_before,
                stock_after=stock_after,
                reference_number=transaction_obj.transaction_number,
                reason=f'Sale - Transaction #{transaction_obj.transaction_number}',
                notes=f'Customer: {transaction_obj.customer_name or "Walk-in"}',
                created_by=self.context['request'].user if 'request' in self.context else None,
                transaction_id=transaction_obj.id
            )

            # ✅ FIX 3: Create LowStockAlert if needed (synchronously)
            if product.current_stock <= product.reorder_level:
                # Check if there's already a pending alert for this product
                existing_alert = LowStockAlert.objects.filter(
                    product=product,
                    status='PENDING'
                ).first()
                
                if not existing_alert:
                    LowStockAlert.objects.create(
                        product=product,
                        current_stock=product.current_stock,
                        reorder_level=product.reorder_level,
                        status='PENDING'
                    )
                    print(f"🚨 Low Stock Alert Created: {product.name} - Stock: {product.current_stock}/{product.reorder_level}")

        return transaction_obj


# ====================
# CART SERIALIZERS
# ====================
class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price']


class CartSerializer(serializers.ModelSerializer):
    cart_items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'session_id', 'is_active', 'cart_items']


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


# ====================
# VOID TRANSACTION SERIALIZER
# ====================
class VoidTransactionSerializer(serializers.Serializer):
    reason = serializers.CharField()


# ====================
# PAYMENT TRANSACTION SERIALIZER
# ====================
class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = '__all__'


# ====================
# SALES REPORT SERIALIZER
# ====================
class SalesReportSerializer(serializers.Serializer):
    total_sales = serializers.FloatField()
    total_transactions = serializers.IntegerField()
    total_items_sold = serializers.IntegerField()
    total_profit = serializers.FloatField()
    average_transaction = serializers.FloatField()
    cash_sales = serializers.FloatField()
    card_sales = serializers.FloatField()
    digital_sales = serializers.FloatField()
    top_products = serializers.ListField()
    daily_sales = serializers.ListField()