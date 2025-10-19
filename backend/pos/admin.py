from django.contrib import admin
from .models import SalesTransaction, TransactionItem, Cart, CartItem, PaymentTransaction


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    extra = 0
    readonly_fields = ('line_total',)


@admin.register(SalesTransaction)
class SalesTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_number', 'created_by', 'total_amount', 'payment_method', 
                   'status', 'created_at', 'item_count')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('transaction_number', 'customer_name', 'customer_phone')
    readonly_fields = ('transaction_number', 'created_at', 'updated_at', 'completed_at', 
                      'voided_by', 'voided_at', 'profit')
    inlines = [TransactionItemInline]
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('transaction_number', 'status', 'created_by', 'created_at')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax', 'discount', 'total_amount', 'profit')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_reference', 'amount_paid', 'change_amount')
        }),
        ('Customer Info', {
            'fields': ('customer_name', 'customer_phone', 'customer_email'),
            'classes': ('collapse',)
        }),
        ('Void Info', {
            'fields': ('voided_by', 'voided_at', 'void_reason'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TransactionItem)
class TransactionItemAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'product', 'quantity', 'unit_price', 'line_total')
    list_filter = ('transaction__created_at',)
    search_fields = ('transaction__transaction_number', 'product__name', 'product__sku')
    readonly_fields = ('line_total', 'profit')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('line_total', 'added_at')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'is_active', 'item_count', 'subtotal', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('session_id', 'user__username')
    readonly_fields = ('item_count', 'subtotal', 'created_at', 'updated_at')
    inlines = [CartItemInline]


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('sales_transaction', 'payment_method', 'amount', 'status', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('sales_transaction__transaction_number', 'reference_number')
    readonly_fields = ('created_at', 'processed_at')