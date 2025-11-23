from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum, F
from django.db import DatabaseError 
from accounts.models import User
from inventory.models import Product, InventoryMovement
from decimal import Decimal
import traceback 

class SalesTransaction(models.Model):
    
    PAYMENT_METHODS = (
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('GCASH', 'GCash'),
        ('PAYMAYA', 'PayMaya'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('VOID', 'Void'),
        ('REFUNDED', 'Refunded'),
    )
    
    # Transaction identification
    transaction_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Transaction details (now set by the serializer)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_reference = models.CharField(max_length=100, blank=True, help_text='Reference number for digital payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True)
    
    # Customer information (optional)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    
    # --- FIX APPLIED HERE: Changed PROTECT to SET_NULL ---
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_transactions')
    # -----------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Voiding information
    voided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='voided_transactions')
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'sales_transactions'
        verbose_name = 'Sales Transaction'
        verbose_name_plural = 'Sales Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_number']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.transaction_number} - ₱{self.total_amount} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Generate transaction number if not exists"""
        if not self.transaction_number:
            today = timezone.now()
            date_str = today.strftime('%Y%m%d')
            
            last_transaction = SalesTransaction.objects.filter(
                transaction_number__startswith=f'TXN-{date_str}'
            ).order_by('-transaction_number').first()
            
            if last_transaction:
                last_number = int(last_transaction.transaction_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.transaction_number = f'TXN-{date_str}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    @property
    def item_count(self):
        """Total number of items in transaction"""
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0
    
    @property
    def profit(self):
        """Calculate total profit from transaction"""
        total_profit = Decimal(0)
        
        for item in self.items.all():
            cost_price = Decimal(item.product.cost_price) if item.product.cost_price is not None else Decimal(0)
            unit_price = item.unit_price
            
            try:
                item_profit = (unit_price - cost_price) * Decimal(item.quantity)
                total_profit += item_profit
            except Exception:
                return Decimal(0)
                
        return total_profit
    
    @transaction.atomic
    def complete_transaction(self):
        """Mark transaction as completed and update inventory"""
        if self.status == 'COMPLETED':
            return
        
        # 2. Deduct inventory for each item
        for item in self.items.all():
            try:
                # Refresh product instance to get current stock value just before update
                item.product.refresh_from_db()
                stock_before = item.product.current_stock
                
                # 🚨 CRITICAL FIX: Check for insufficient stock before updating
                if stock_before < item.quantity:
                    # This raises an exception that the outer @transaction.atomic block will catch
                    # and signal to the CheckoutView's catch block.
                    raise Exception(
                        f"Insufficient stock: {item.product.name} (SKU: {item.product.sku}). Available: {stock_before}, Needed: {item.quantity}"
                    )
                
                # ATOMICALLY DEDUCT STOCK using F expression
                rows_updated = Product.objects.filter(pk=item.product.pk).update(
                    current_stock=F('current_stock') - item.quantity
                )
                
                if rows_updated == 0:
                    raise DatabaseError(f"Failed to update stock for Product ID {item.product.pk}. Row not found.")

                # Refresh and capture stock AFTER deduction
                item.product.refresh_from_db()
                stock_after = item.product.current_stock
                
                # Create inventory movement log
                InventoryMovement.objects.create(
                    product=item.product,
                    movement_type='SALE',
                    quantity=item.quantity,
                    stock_before=stock_before,
                    stock_after=stock_after,
                    reference_number=self.transaction_number,
                    reason=f'Sale transaction {self.transaction_number}',
                    created_by=self.created_by,
                    transaction_id=self.id
                )
            except Exception as e:
                # Log the specific error and re-raise to trigger the rollback of the main transaction 
                print(f"Inventory deduction failed for item {item.id} (TXN: {self.transaction_number}): {e}")
                traceback.print_exc()
                raise e # CRITICAL: Re-raise the exception to rollback the transaction.

        # 1. Update the status only after inventory deduction is successful for all items
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        # Use save(update_fields=...) to save only the changed fields
        self.save(update_fields=['status', 'completed_at', 'updated_at']) 
    
    @transaction.atomic
    def void_transaction(self, user, reason):
        """Void the transaction and restore inventory"""
        if self.status == 'VOID':
            return
        
        # Restore inventory if transaction was completed
        if self.status == 'COMPLETED':
            for item in self.items.all():
                
                # 1. Refresh & Capture stock BEFORE atomic update
                item.product.refresh_from_db()
                stock_before = item.product.current_stock
                
                # 2. ATOMICALLY RESTORE STOCK
                Product.objects.filter(pk=item.product.pk).update(
                    current_stock=F('current_stock') + item.quantity
                )

                # 3. Refresh & Capture stock AFTER atomic update
                item.product.refresh_from_db()
                stock_after = item.product.current_stock
                
                # 4. Create inventory movement to restore stock
                InventoryMovement.objects.create(
                    product=item.product,
                    movement_type='RETURN',
                    quantity=item.quantity,
                    stock_before=stock_before,
                    stock_after=stock_after,
                    reference_number=f'VOID-{self.transaction_number}',
                    reason=f'Voided transaction {self.transaction_number}: {reason}',
                    created_by=user,
                    transaction_id=self.id
                )
        
        self.status = 'VOID'
        self.voided_by = user
        self.voided_at = timezone.now()
        self.void_reason = reason
        self.save()


class TransactionItem(models.Model):
    """Individual items in a sales transaction"""
    
    transaction = models.ForeignKey(SalesTransaction, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='transaction_items')
    
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    notes = models.TextField(blank=True, help_text='Special instructions or notes')
    
    class Meta:
        db_table = 'transaction_items'
        verbose_name = 'Transaction Item'
        verbose_name_plural = 'Transaction Items'
        ordering = ['id']
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity} - ₱{self.line_total}"
    
    def save(self, *args, **kwargs):
        """Calculate line total before saving"""
        self.line_total = (self.unit_price * self.quantity) - self.discount
        super().save(*args, **kwargs)
    
    @property
    def profit(self):
        """Calculate profit for this item"""
        cost_price = Decimal(self.product.cost_price) if self.product.cost_price is not None else Decimal(0)
        unit_price = self.unit_price
        
        try:
            return (unit_price - cost_price) * Decimal(self.quantity)
        except Exception:
            return Decimal(0)


class Cart(models.Model):
    """Shopping cart for building transactions"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    session_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'carts'
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Cart {self.session_id} - {self.user.username}"
    
    @property
    def item_count(self):
        """Total number of items in cart"""
        return self.cart_items.aggregate(total=Sum('quantity'))['total'] or 0
    
    @property
    def subtotal(self):
        """Calculate cart subtotal"""
        return sum(item.line_total for item in self.cart_items.all())
    
    def clear(self):
        """Clear all items from cart"""
        self.cart_items.all().delete()


class CartItem(models.Model):
    """Items in a shopping cart"""
    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cart_items'
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'product']
        ordering = ['added_at']
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
    
    @property
    def line_total(self):
        """Calculate line total"""
        if self.unit_price is None or self.quantity is None:
            return 0
        return self.unit_price * self.quantity
    
    def save(self, *args, **kwargs):
        """Set unit price from product if not provided"""
        if not self.unit_price:
            self.product.refresh_from_db()
            self.unit_price = self.product.unit_price
        super().save(*args, **kwargs)


class PaymentTransaction(models.Model):
    """Track payment details for transactions"""
    
    PAYMENT_STATUS = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('DECLINED', 'Declined'),
        ('REFUNDED', 'Refunded'),
    )
    
    sales_transaction = models.ForeignKey(SalesTransaction, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=SalesTransaction.PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Payment provider details
    reference_number = models.CharField(max_length=100, blank=True)
    authorization_code = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    
    # Additional details
    card_last_four = models.CharField(max_length=4, blank=True, help_text='Last 4 digits of card')
    provider_response = models.TextField(blank=True, help_text='Raw response from payment provider')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payment_transactions'
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_payment_method_display()} - ₱{self.amount} ({self.get_status_display()})"