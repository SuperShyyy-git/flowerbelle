from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import F

class Category(models.Model):
    """Product categories (Roses, Tulips, Arrangements, etc.)"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def product_count(self):
        """Count of products in this category"""
        return self.products.filter(is_active=True).count()


class Supplier(models.Model):
    """Suppliers for products"""
    
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'suppliers'
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Products (flowers, arrangements, accessories)"""
    
    sku = models.CharField(max_length=50, unique=True, verbose_name='SKU')
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='products', null=True, blank=True)
    
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Stock management
    current_stock = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0)], 
        blank=True, 
        null=True   
    )
    reorder_level = models.IntegerField(
        default=10, 
        validators=[MinValueValidator(0)], 
        blank=True, 
        null=True,  
        help_text='Alert when stock falls below this level'
    )
    
    # Product details
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    barcode = models.CharField(max_length=100, blank=True, unique=True, null=True)
    expiry_date = models.DateField(null=True, blank=True, help_text='For perishable items')
    
    # Status
    is_active = models.BooleanField(default=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_products') 
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def is_low_stock(self):
        """Check if product is below reorder level"""
        return self.current_stock <= self.reorder_level
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price > 0:
            return ((self.unit_price - self.cost_price) / self.cost_price) * 100
        return 0
    
    @property
    def stock_value(self):
        """Calculate total value of current stock"""
        return self.current_stock * self.cost_price
    
    @property
    def is_expired(self):
        """Check if product has expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False


class InventoryMovement(models.Model):
    """Track all inventory movements (stock-in, stock-out, adjustments)"""
    
    MOVEMENT_TYPES = (
        ('STOCK_IN', 'Stock In'),
        ('STOCK_OUT', 'Stock Out'),
        ('ADJUSTMENT', 'Adjustment'),
        ('SALE', 'Sale'),
        ('RETURN', 'Return'),
        ('DAMAGE', 'Damage/Wastage'),
    )
    
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Before and after stock levels
    stock_before = models.IntegerField()
    stock_after = models.IntegerField()
    
    # Reference information
    reference_number = models.CharField(max_length=100, blank=True, help_text='PO number, invoice, etc.')
    reason = models.TextField(help_text='Reason for movement')
    notes = models.TextField(blank=True)
    
    # Tracking
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='inventory_movements')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Link to sales transaction if movement is from a sale
    transaction_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'inventory_movements'
        verbose_name = 'Inventory Movement'
        verbose_name_plural = 'Inventory Movements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['movement_type']),
        ]
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        """
        ⚠️ NOTE: For SALE movements, stock updates and alert creation 
        are now handled in pos/serializers.py for better transaction control.
        
        This save() method now only handles manual inventory movements 
        (STOCK_IN, STOCK_OUT, ADJUSTMENT, DAMAGE).
        """
        
        if not self.pk:  # Only on creation
            
            # Only process non-SALE movements here
            # SALE movements are created with pre-calculated stock_before/stock_after
            if self.movement_type != 'SALE' and not (self.stock_before is not None and self.stock_after is not None):
                self.stock_before = self.product.current_stock
                
                if self.movement_type in ['STOCK_IN']:
                    Product.objects.filter(pk=self.product.pk).update(current_stock=F('current_stock') + self.quantity)
                elif self.movement_type in ['STOCK_OUT', 'DAMAGE']:
                    Product.objects.filter(pk=self.product.pk).update(current_stock=F('current_stock') - self.quantity)
                elif self.movement_type == 'ADJUSTMENT':
                    Product.objects.filter(pk=self.product.pk).update(current_stock=self.quantity)
                
                self.product.refresh_from_db()
                self.stock_after = self.product.current_stock
                
                # Create low stock alert for manual movements
                if self.product.is_low_stock and self.movement_type in ['STOCK_OUT', 'DAMAGE', 'ADJUSTMENT']:
                    existing_alert = LowStockAlert.objects.filter(
                        product=self.product,
                        status='PENDING'
                    ).first()
                    
                    if not existing_alert:
                        LowStockAlert.objects.create(
                            product=self.product,
                            current_stock=self.product.current_stock,
                            reorder_level=self.product.reorder_level
                        )
        
        super().save(*args, **kwargs)


class LowStockAlert(models.Model):
    """Track low stock alerts"""
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
    )
    
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='alerts')
    current_stock = models.IntegerField()
    reorder_level = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'low_stock_alerts'
        verbose_name = 'Low Stock Alert'
        verbose_name_plural = 'Low Stock Alerts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Alert: {self.product.name} - Stock: {self.current_stock}/{self.reorder_level}"

    def save(self, *args, **kwargs):
        # Auto-fill current_stock from Product if not manually set
        if not self.current_stock and self.product:
            try:
                self.current_stock = self.product.current_stock 
            except AttributeError:
                self.current_stock = 0
        super().save(*args, **kwargs)
    
    def acknowledge(self, user):
        """Mark alert as acknowledged"""
        self.status = 'ACKNOWLEDGED'
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.save()
    
    def resolve(self):
        """Mark alert as resolved"""
        self.status = 'RESOLVED'
        self.resolved_at = timezone.now()
        self.save()