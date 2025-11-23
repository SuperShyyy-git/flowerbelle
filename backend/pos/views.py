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
from django.db import transaction, DatabaseError 
from rest_framework.exceptions import ValidationError
import traceback 

from .serializers import (
    SalesTransactionListSerializer, 
    SalesTransactionDetailSerializer,
    SalesTransactionCreateSerializer, 
    CartSerializer, 
    CartItemSerializer,
    AddToCartSerializer, 
    VoidTransactionSerializer, 
    PaymentTransactionSerializer,
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
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(created_by_id=user_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SalesTransactionCreateSerializer
        return SalesTransactionListSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            self.perform_create(serializer) 
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            print("\n🚨 SALES TRANSACTION LIST/CREATE SERIALIZER ERRORS (400 CAUSE):")
            print("Incoming Data:", request.data)
            print("Errors:", serializer.errors)
            print("===============================================================")
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        transaction = serializer.save(created_by=self.request.user)
        
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
        
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True,
            defaults={'session_id': f'CART-{request.user.id}-{timezone.now().timestamp()}'}
        )
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity, 'unit_price': product.unit_price}
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            
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
    """
    Processes checkout using the active cart.
    ✅ FIXED: Transaction now creates as COMPLETED, ensuring immediate dashboard sync
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        try:
            print("\n====================================")
            print("INCOMING CHECKOUT PAYLOAD:")
            print(request.data)
            print("====================================")
            
            cart = Cart.objects.select_for_update().prefetch_related('cart_items__product').get(
                user=request.user,
                is_active=True
            )
            
            if not cart.cart_items.exists():
                return Response(
                    {'error': 'Cart is empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            transaction_data = {
                'items': [
                    {'product_id': item.product.id, 
                     'quantity': item.quantity, 
                     'unit_price': item.unit_price, 
                     'discount': 0}
                    for item in cart.cart_items.all()
                ],
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
            
            serializer = SalesTransactionCreateSerializer(
                data=transaction_data,
                context={'request': request}
            )
            
            if not serializer.is_valid():
                print("\n🚨 CHECKOUT SERIALIZER VALIDATION ERRORS (400 CAUSE):")
                print(serializer.errors)
                print("=====================================================")
                raise ValidationError(detail=serializer.errors) 
            
            # ✅ Transaction is now created with status='COMPLETED' (fixed in serializer)
            transaction_obj = serializer.save(created_by=request.user)
            
            print(f"✅ Transaction created with status: {transaction_obj.status}")
            
            # Clear the cart and deactivate it
            cart.clear()
            cart.is_active = False
            cart.save()
            
            create_audit_log(
                user=request.user,
                action='CREATE',
                table_name='sales_transactions',
                record_id=transaction_obj.id,
                new_values=SalesTransactionDetailSerializer(transaction_obj).data,
                request=request
            )
            
            return Response({
                'message': 'Checkout successful',
                'transaction': SalesTransactionDetailSerializer(transaction_obj).data
            }, status=status.HTTP_201_CREATED)

        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart not found. Please ensure the user has an active cart.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except DatabaseError as e:
            print("FATAL DATABASE ERROR DURING CHECKOUT:")
            traceback.print_exc()
            return Response(
                {'error': 'A critical database error occurred. The transaction was rolled back. Please retry checkout.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except ValidationError as e:
            return Response(
                {'error': 'Validation failed.', 'details': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            error_detail = getattr(e, 'detail', str(e))
            error_message = f'Server error during transaction processing: {error_detail}'
            print(f"UNHANDLED EXCEPTION IN CHECKOUT: {error_message}")
            traceback.print_exc()
            return Response(
                {'error': error_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ========== SALES REPORTS VIEWS ==========

class SalesReportView(APIView):
    """Get comprehensive sales report"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        if request.query_params.get('start_date'):
            start_date = timezone.datetime.fromisoformat(request.query_params.get('start_date'))
        if request.query_params.get('end_date'):
            end_date = timezone.datetime.fromisoformat(request.query_params.get('end_date'))
        
        transactions = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        total_sales = transactions.aggregate(total=Sum('total_amount'))['total'] or 0
        total_transactions = transactions.count()
        total_items_sold = TransactionItem.objects.filter(
            transaction__in=transactions
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        total_profit = sum(t.profit for t in transactions)
        
        average_transaction = total_sales / total_transactions if total_transactions > 0 else 0
        
        cash_sales = transactions.filter(payment_method='CASH').aggregate(
            total=Sum('total_amount'))['total'] or 0
        card_sales = transactions.filter(payment_method='CARD').aggregate(
            total=Sum('total_amount'))['total'] or 0
        digital_sales = transactions.filter(
            payment_method__in=['GCASH', 'PAYMAYA', 'BANK_TRANSFER']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        top_products = TransactionItem.objects.filter(
            transaction__in=transactions
        ).values(
            'product__id', 'product__name', 'product__sku'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('line_total')
        ).order_by('-total_quantity')[:10]
        
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