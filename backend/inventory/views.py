from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, F, Q
from django.utils import timezone
from accounts.permissions import IsOwner, IsOwnerOrReadOnly
from accounts.utils import create_audit_log
from django.db import IntegrityError 
from rest_framework import serializers 
from .models import Category, Supplier, Product, InventoryMovement, LowStockAlert
from .serializers import (
    CategorySerializer, SupplierSerializer,
    ProductListSerializer, ProductDetailSerializer, ProductCreateUpdateSerializer,
    InventoryMovementSerializer, InventoryMovementCreateSerializer,
    StockAdjustmentSerializer, LowStockAlertSerializer, InventoryReportSerializer
)


# ========== CATEGORY VIEWS ==========

class CategoryListCreateView(generics.ListCreateAPIView):
    """List all categories or create a new one"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        category = serializer.save()
        create_audit_log(
            user=self.request.user,
            action='CREATE',
            table_name='categories',
            record_id=category.id,
            new_values=serializer.data,
            request=self.request
        )


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a category"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def perform_update(self, serializer):
        old_data = CategorySerializer(self.get_object()).data
        category = serializer.save()
        create_audit_log(
            user=self.request.user,
            action='UPDATE',
            table_name='categories',
            record_id=category.id,
            old_values=old_data,
            new_values=serializer.data,
            request=self.request
        )
    
    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()
        create_audit_log(
            user=self.request.user,
            action='DELETE',
            table_name='categories',
            record_id=instance.id,
            description=f"Deactivated category: {instance.name}",
            request=self.request
        )


# ========== SUPPLIER VIEWS ==========

class SupplierListCreateView(generics.ListCreateAPIView):
    """List all suppliers or create a new one"""
    # Only active suppliers are shown
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact_person', 'phone', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        supplier = serializer.save()
        create_audit_log(
            user=self.request.user,
            action='CREATE',
            table_name='suppliers',
            record_id=supplier.id,
            new_values=serializer.data,
            request=self.request
        )


class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a supplier"""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def perform_update(self, serializer):
        old_data = SupplierSerializer(self.get_object()).data
        supplier = serializer.save()
        create_audit_log(
            user=self.request.user,
            action='UPDATE',
            table_name='suppliers',
            record_id=supplier.id,
            old_values=old_data,
            new_values=serializer.data,
            request=self.request
        )
    
    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()
        create_audit_log(
            user=self.request.user,
            action='DELETE',
            table_name='suppliers',
            record_id=instance.id,
            description=f"Deactivated supplier: {instance.name}",
            request=self.request
        )


# ========== PRODUCT VIEWS ==========

class ProductListCreateView(generics.ListCreateAPIView):
    """List all products or create a new one"""
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'barcode', 'category__name']
    ordering_fields = ['name', 'unit_price', 'current_stock', 'created_at']
    ordering = ['name']
    
    # 👇 THIS DISABLES PAGINATION SO YOU SEE ALL PRODUCTS 👇
    pagination_class = None 
    
    def get_queryset(self):
        # Start with only ACTIVE products by default
        queryset = Product.objects.filter(is_active=True).select_related('category', 'supplier')
        
        # Filter by category
        category_param = self.request.query_params.get('category')
        if category_param:
            try:
                category_id = int(category_param)
                queryset = queryset.filter(category_id=category_id)
            except (ValueError, TypeError):
                pass # Ignore invalid category
        
        # Filter by low stock
        low_stock = self.request.query_params.get('low_stock')
        if low_stock == 'true':
            queryset = queryset.filter(current_stock__lte=F('reorder_level'))
        
        # Filter by active status override
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() == 'false':
                queryset = Product.objects.filter(is_active=False).select_related('category', 'supplier')
            elif is_active.lower() == 'true':
                queryset = Product.objects.filter(is_active=True).select_related('category', 'supplier')
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductListSerializer
    
    def perform_create(self, serializer):
        try:
            product = serializer.save(created_by=self.request.user)
            
            try:
                create_audit_log(
                    user=self.request.user,
                    action='CREATE',
                    table_name='products',
                    record_id=product.id,
                    new_values=ProductDetailSerializer(product).data,
                    request=self.request
                )
            except Exception as audit_e:
                print(f"AUDIT LOG FAILED: {audit_e}")
            
        except IntegrityError as e:
            error_message = str(e).lower()
            if 'unique' in error_message and 'sku' in error_message:
                raise serializers.ValidationError(
                    {"sku": "A product with this SKU already exists. Please choose a unique SKU."}, 
                    code='unique'
                )
            raise
        except Exception as e:
            print(f"CRITICAL SERVER ERROR: {e}")
            raise


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a product"""
    queryset = Product.objects.select_related('category', 'supplier', 'created_by').all()
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer
    
    def perform_update(self, serializer):
        try:
            old_data = ProductDetailSerializer(self.get_object()).data
            product = serializer.save()
            
            try:
                create_audit_log(
                    user=self.request.user,
                    action='UPDATE',
                    table_name='products',
                    record_id=product.id,
                    old_values=old_data,
                    new_values=ProductDetailSerializer(product).data,
                    request=self.request
                )
            except Exception as audit_e:
                print(f"AUDIT LOG FAILED: {audit_e}")

        except IntegrityError as e:
            error_message = str(e).lower()
            if 'unique' in error_message and 'sku' in error_message:
                raise serializers.ValidationError(
                    {"sku": "A product with this SKU already exists. Please choose a unique SKU."}, 
                    code='unique'
                )
            raise
        except Exception as e:
            print(f"CRITICAL SERVER ERROR: {e}")
            raise
    
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
        create_audit_log(
            user=self.request.user,
            action='DELETE',
            table_name='products',
            record_id=instance.id,
            description=f"Deactivated product: {instance.name}",
            request=self.request
        )


# ========== INVENTORY MOVEMENT VIEWS ==========

class InventoryMovementListCreateView(generics.ListCreateAPIView):
    """List all inventory movements or create a new one"""
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product__name', 'product__sku', 'reference_number']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = InventoryMovement.objects.select_related('product', 'created_by').all()
        
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        movement_type = self.request.query_params.get('movement_type')
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InventoryMovementCreateSerializer
        return InventoryMovementSerializer
    
    def perform_create(self, serializer):
        movement = serializer.save(created_by=self.request.user)
        
        product = movement.product
        if product.is_low_stock:
            existing_alert = LowStockAlert.objects.filter(
                product=product,
                status='PENDING'
            ).first()
            
            if not existing_alert:
                LowStockAlert.objects.create(
                    product=product,
                    current_stock=product.current_stock,
                    reorder_level=product.reorder_level
                )
        
        create_audit_log(
            user=self.request.user,
            action='CREATE',
            table_name='inventory_movements',
            record_id=movement.id,
            new_values=InventoryMovementSerializer(movement).data,
            request=self.request
        )


class InventoryMovementDetailView(generics.RetrieveAPIView):
    """Retrieve an inventory movement"""
    queryset = InventoryMovement.objects.select_related('product', 'created_by').all()
    serializer_class = InventoryMovementSerializer
    permission_classes = [IsAuthenticated]


class StockAdjustmentView(APIView):
    """Adjust product stock to a specific level"""
    permission_classes = [IsAuthenticated, IsOwner]
    
    def post(self, request):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product = serializer.validated_data['product']
        new_stock = serializer.validated_data['new_stock_level']
        reason = serializer.validated_data['reason']
        notes = serializer.validated_data.get('notes', '')
        
        movement = InventoryMovement.objects.create(
            product=product,
            movement_type='ADJUSTMENT',
            quantity=new_stock,
            reference_number=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            reason=reason,
            notes=notes,
            created_by=request.user
        )
        
        create_audit_log(
            user=request.user,
            action='UPDATE',
            table_name='products',
            record_id=product.id,
            description=f"Stock adjusted to {new_stock}. Reason: {reason}",
            request=request
        )
        
        return Response({
            'message': 'Stock adjusted successfully',
            'movement': InventoryMovementSerializer(movement).data,
            'product': ProductDetailSerializer(product).data
        })


# ========== LOW STOCK ALERT VIEWS ==========

class LowStockAlertListView(generics.ListAPIView):
    """List all low stock alerts"""
    serializer_class = LowStockAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = LowStockAlert.objects.select_related('product', 'acknowledged_by').all()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


class LowStockAlertDetailView(generics.RetrieveAPIView):
    """Retrieve a low stock alert"""
    queryset = LowStockAlert.objects.select_related('product', 'acknowledged_by').all()
    serializer_class = LowStockAlertSerializer
    permission_classes = [IsAuthenticated]


class AcknowledgeAlertView(APIView):
    """Acknowledge a low stock alert"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            alert = LowStockAlert.objects.get(pk=pk)
        except LowStockAlert.DoesNotExist:
            return Response(
                {'error': 'Alert not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if alert.status != 'PENDING':
            return Response(
                {'error': 'Alert has already been acknowledged'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alert.acknowledge(request.user)
        
        return Response({
            'message': 'Alert acknowledged successfully',
            'alert': LowStockAlertSerializer(alert).data
        })


class ResolveAlertView(APIView):
    """Resolve a low stock alert"""
    permission_classes = [IsAuthenticated, IsOwner]
    
    def post(self, request, pk):
        try:
            alert = LowStockAlert.objects.get(pk=pk)
        except LowStockAlert.DoesNotExist:
            return Response(
                {'error': 'Alert not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if alert.status == 'RESOLVED':
            return Response(
                {'error': 'Alert is already resolved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alert.resolve()
        
        return Response({
            'message': 'Alert resolved successfully',
            'alert': LowStockAlertSerializer(alert).data
        })


# ========== INVENTORY REPORTS ==========

class InventoryReportView(APIView):
    """Get comprehensive inventory report"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        total_products = Product.objects.count()
        active_products = Product.objects.filter(is_active=True).count()
        
        total_stock_value = Product.objects.aggregate(
            total=Sum(F('current_stock') * F('cost_price'))
        )['total'] or 0
        
        low_stock_count = Product.objects.filter(
            current_stock__lte=F('reorder_level'),
            is_active=True
        ).count()
        
        out_of_stock_count = Product.objects.filter(
            current_stock=0,
            is_active=True
        ).count()
        
        expired_products_count = Product.objects.filter(
            expiry_date__lt=timezone.now().date(),
            is_active=True
        ).count()
        
        categories_count = Category.objects.filter(is_active=True).count()
        
        top_selling = InventoryMovement.objects.filter(
            movement_type='SALE'
        ).values(
            'product__id', 'product__name', 'product__sku'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')[:5]
        
        low_stock_products = Product.objects.filter(
            current_stock__lte=F('reorder_level'),
            is_active=True
        ).values(
            'id', 'name', 'sku', 'current_stock', 'reorder_level', 'category__name'
        )[:10]
        
        data = {
            'total_products': total_products,
            'active_products': active_products,
            'total_stock_value': float(total_stock_value),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'expired_products_count': expired_products_count,
            'categories_count': categories_count,
            'top_selling': list(top_selling),
            'low_stock_products': list(low_stock_products)
        }
        
        serializer = InventoryReportSerializer(data)
        return Response(serializer.data)


class CategoryReportView(APIView):
    """Get report of products by category"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = Category.objects.filter(is_active=True).annotate(
            product_count=Sum('products__current_stock'),
            stock_value=Sum(F('products__current_stock') * F('products__cost_price'))
        ).values('id', 'name', 'product_count', 'stock_value')
        
        return Response(list(categories))