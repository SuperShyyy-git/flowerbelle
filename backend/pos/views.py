from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import timedelta
from accounts.utils import create_audit_log
from .models import SalesTransaction, TransactionItem, Cart, CartItem, PaymentTransaction
from inventory.models import Product
from .serializers import (
    SalesTransactionListSerializer, SalesTransactionDetailSerializer,
    SalesTransactionCreateSerializer, CartSerializer, CartItemSerializer,
    AddToCartSerializer, VoidTransactionSerializer, PaymentTransactionSerializer,
    SalesReportSerializer
)


# ========== SALES TRANSACTION VIEWS ==========

class SalesTransactionListCreateView(generics.ListCreateAPIView):
    """List all sales transactions or create a new one"""
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['transaction_number', 'customer_name', 'customer_phone']
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = SalesTransaction.objects.select_related('created_by').all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by payment method
        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Filter by user (staff)
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(created_by_id=user_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SalesTransactionCreateSerializer
        return SalesTransactionListSerializer
    
    def perform_create(self, serializer):
        transaction = serializer.save()
        
        create_audit_log(
            user=self.request.user,
            action='CREATE',
            table_name='sales_transactions',
            record_id=transaction.id,
            new_values=SalesTransactionDetailSerializer(transaction).data,
            request=self.request
        )


class SalesTransactionDetailView(generics.RetrieveAPIView):
    """Retrieve a sales transaction"""
    queryset = SalesTransaction.objects.select_related('created_by', 'voided_by').prefetch_related('items__product').all()
    serializer_class = SalesTransactionDetailSerializer
    permission_classes = [IsAuthenticated]


class VoidTransactionView(APIView):
    """Void a sales transaction"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            transaction = SalesTransaction.objects.get(pk=pk)
        except SalesTransaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if transaction.status == 'VOID':
            return Response(
                {'error': 'Transaction is already voided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VoidTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data['reason']
        transaction.void_transaction(request.user, reason)
        
        create_audit_log(
            user=request.user,
            action='UPDATE',
            table_name='sales_transactions',
            record_id=transaction.id,
            description=f"Voided transaction: {reason}",
            request=request
        )
        
        return Response({
            'message': 'Transaction voided successfully',
            'transaction': SalesTransactionDetailSerializer(transaction).data
        })


# ========== CART VIEWS ==========

class CartView(APIView):
    """Get or clear current user's active cart"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get active cart"""
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True,
            defaults={'session_id': f'CART-{request.user.id}-{timezone.now().timestamp()}'}
        )
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    def delete(self, request):
        """Clear cart"""
        try:
            cart = Cart.objects.get(user=request.user, is_active=True)
            cart.clear()
            return Response({'message': 'Cart cleared successfully'})
        except Cart.DoesNotExist:
            return Response({'message': 'No active cart found'})


class AddToCartView(APIView):
    """Add item to cart"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True,
            defaults={'session_id': f'CART-{request.user.id}-{timezone.now().timestamp()}'}
        )
        
        # Get product
        product = Product.objects.get(id=product_id)
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity, 'unit_price': product.unit_price}
        )
        
        if not created:
            # Update quantity if item already exists
            new_quantity = cart_item.quantity + quantity
            
            # Check stock availability
            if product.current_stock < new_quantity:
                return Response(
                    {'error': f'Insufficient stock. Available: {product.current_stock}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item.quantity = new_quantity
            cart_item.save()
        
        return Response({
            'message': 'Item added to cart',
            'cart': CartSerializer(cart).data
        })


class UpdateCartItemView(APIView):
    """Update cart item quantity"""
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        try:
            cart_item = CartItem.objects.select_related('product').get(
                pk=pk,
                cart__user=request.user,
                cart__is_active=True
            )
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        quantity = request.data.get('quantity')
        
        if not quantity or quantity < 1:
            return Response(
                {'error': 'Invalid quantity'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check stock availability
        if cart_item.product.current_stock < quantity:
            return Response(
                {'error': f'Insufficient stock. Available: {cart_item.product.current_stock}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart_item.quantity = quantity
        cart_item.save()
        
        return Response({
            'message': 'Cart item updated',
            'cart': CartSerializer(cart_item.cart).data
        })


class RemoveCartItemView(APIView):
    """Remove item from cart"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, pk):
        try:
            cart_item = CartItem.objects.get(
                pk=pk,
                cart__user=request.user,
                cart__is_active=True
            )
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        cart = cart_item.cart
        cart_item.delete()
        
        return Response({
            'message': 'Item removed from cart',
            'cart': CartSerializer(cart).data
        })


class CheckoutView(APIView):
    """Process cart checkout"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            cart = Cart.objects.prefetch_related('cart_items__product').get(
                user=request.user,
                is_active=True
            )
        except Cart.DoesNotExist:
            return Response(
                {'error': 'No active cart found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not cart.cart_items.exists():
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build transaction data from cart
        items = []
        for cart_item in cart.cart_items.all():
            items.append({
                'product': cart_item.product.id,
                'quantity': cart_item.quantity,
                'unit_price': cart_item.unit_price,
                'discount': 0
            })
        
        transaction_data = {
            'items': items,
            'payment_method': request.data.get('payment_method'),
            'payment_reference': request.data.get('payment_reference', ''),
            'amount_paid': request.data.get('amount_paid'),
            'tax': request.data.get('tax', 0),
            'discount': request.data.get('discount', 0),
            'notes': request.data.get('notes', ''),
            'customer_name': request.data.get('customer_name', ''),
            'customer_phone': request.data.get('customer_phone', ''),
            'customer_email': request.data.get('customer_email', '')
        }
        
        # Create transaction
        serializer = SalesTransactionCreateSerializer(
            data=transaction_data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()
        
        # Clear cart
        cart.clear()
        cart.is_active = False
        cart.save()
        
        return Response({
            'message': 'Checkout successful',
            'transaction': SalesTransactionDetailSerializer(transaction).data
        }, status=status.HTTP_201_CREATED)


# ========== SALES REPORTS ==========

class SalesReportView(APIView):
    """Get comprehensive sales report"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Date range (default to last 30 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Allow custom date range
        if request.query_params.get('start_date'):
            start_date = timezone.datetime.fromisoformat(request.query_params.get('start_date'))
        if request.query_params.get('end_date'):
            end_date = timezone.datetime.fromisoformat(request.query_params.get('end_date'))
        
        # Get completed transactions in date range
        transactions = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        # Calculate totals
        total_sales = transactions.aggregate(total=Sum('total_amount'))['total'] or 0
        total_transactions = transactions.count()
        total_items_sold = TransactionItem.objects.filter(
            transaction__in=transactions
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Calculate profit
        total_profit = sum(t.profit for t in transactions)
        
        # Average transaction
        average_transaction = total_sales / total_transactions if total_transactions > 0 else 0
        
        # Sales by payment method
        cash_sales = transactions.filter(payment_method='CASH').aggregate(
            total=Sum('total_amount'))['total'] or 0
        card_sales = transactions.filter(payment_method='CARD').aggregate(
            total=Sum('total_amount'))['total'] or 0
        digital_sales = transactions.filter(
            payment_method__in=['GCASH', 'PAYMAYA', 'BANK_TRANSFER']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Top selling products
        top_products = TransactionItem.objects.filter(
            transaction__in=transactions
        ).values(
            'product__id', 'product__name', 'product__sku'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('line_total')
        ).order_by('-total_quantity')[:10]
        
        # Daily sales breakdown
        daily_sales = transactions.extra(
            select={'day': 'DATE(created_at)'}
        ).values('day').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('day')
        
        data = {
            'total_sales': float(total_sales),
            'total_transactions': total_transactions,
            'total_items_sold': total_items_sold,
            'total_profit': float(total_profit),
            'average_transaction': float(average_transaction),
            'cash_sales': float(cash_sales),
            'card_sales': float(card_sales),
            'digital_sales': float(digital_sales),
            'top_products': list(top_products),
            'daily_sales': list(daily_sales)
        }
        
        serializer = SalesReportSerializer(data)
        return Response(serializer.data)


class DailySalesView(APIView):
    """Get today's sales summary"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        today = timezone.now().date()
        
        transactions = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__date=today
        )
        
        total_sales = transactions.aggregate(total=Sum('total_amount'))['total'] or 0
        total_transactions = transactions.count()
        total_profit = sum(t.profit for t in transactions)
        
        return Response({
            'date': today,
            'total_sales': float(total_sales),
            'total_transactions': total_transactions,
            'total_profit': float(total_profit),
            'transactions': SalesTransactionListSerializer(transactions, many=True).data
        })


class StaffSalesView(APIView):
    """Get sales by staff member"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Date range (default to today)
        start_date = request.query_params.get('start_date', timezone.now().date())
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        staff_sales = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values(
            'created_by__id',
            'created_by__full_name'
        ).annotate(
            total_sales=Sum('total_amount'),
            transaction_count=Count('id'),
            items_sold=Sum('items__quantity')
        ).order_by('-total_sales')
        
        return Response(list(staff_sales))