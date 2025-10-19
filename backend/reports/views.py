from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import timedelta, datetime
from accounts.permissions import IsOwner
from pos.models import SalesTransaction, TransactionItem
from inventory.models import Product, Category, InventoryMovement, LowStockAlert
from .models import DashboardMetric, ReportSchedule, ReportExport
from .serializers import (
    DashboardOverviewSerializer, DashboardMetricSerializer,
    SalesAnalyticsSerializer, InventoryAnalyticsSerializer,
    ProfitLossSerializer, StaffPerformanceSerializer,
    ReportScheduleSerializer, ReportExportSerializer, ExportRequestSerializer
)


# ========== DASHBOARD VIEWS ==========

class DashboardOverviewView(APIView):
    """Get dashboard overview with key metrics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Today's metrics
        today_txns = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__date=today
        )
        today_sales = today_txns.aggregate(total=Sum('total_amount'))['total'] or 0
        today_transactions = today_txns.count()
        today_profit = sum(t.profit for t in today_txns)
        today_items = TransactionItem.objects.filter(
            transaction__in=today_txns
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # This week
        week_txns = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__date__gte=week_start
        )
        week_sales = week_txns.aggregate(total=Sum('total_amount'))['total'] or 0
        week_transactions = week_txns.count()
        week_profit = sum(t.profit for t in week_txns)
        
        # This month
        month_txns = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__date__gte=month_start
        )
        month_sales = month_txns.aggregate(total=Sum('total_amount'))['total'] or 0
        month_transactions = month_txns.count()
        month_profit = sum(t.profit for t in month_txns)
        
        # Inventory metrics
        total_products = Product.objects.filter(is_active=True).count()
        low_stock_count = Product.objects.filter(
            current_stock__lte=F('reorder_level'),
            is_active=True
        ).count()
        out_of_stock_count = Product.objects.filter(
            current_stock=0,
            is_active=True
        ).count()
        inventory_value = Product.objects.filter(is_active=True).aggregate(
            total=Sum(F('current_stock') * F('cost_price'))
        )['total'] or 0
        
        # Pending alerts
        pending_alerts = LowStockAlert.objects.filter(status='PENDING').count()
        
        # Top products (this month)
        top_products = TransactionItem.objects.filter(
            transaction__in=month_txns
        ).values(
            'product__id', 'product__name', 'product__sku'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('line_total')
        ).order_by('-total_quantity')[:5]
        
        # Recent transactions
        recent_txns = SalesTransaction.objects.filter(
            status='COMPLETED'
        ).order_by('-created_at')[:10].values(
            'id', 'transaction_number', 'total_amount', 'created_at',
            'created_by__full_name'
        )
        
        data = {
            'today_sales': float(today_sales),
            'today_transactions': today_transactions,
            'today_profit': float(today_profit),
            'today_items_sold': today_items,
            'week_sales': float(week_sales),
            'week_transactions': week_transactions,
            'week_profit': float(week_profit),
            'month_sales': float(month_sales),
            'month_transactions': month_transactions,
            'month_profit': float(month_profit),
            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'inventory_value': float(inventory_value),
            'pending_alerts': pending_alerts,
            'top_products': list(top_products),
            'recent_transactions': list(recent_txns)
        }
        
        serializer = DashboardOverviewSerializer(data)
        return Response(serializer.data)


class DashboardMetricsHistoryView(generics.ListAPIView):
    """Get historical dashboard metrics"""
    serializer_class = DashboardMetricSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        days = int(self.request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        return DashboardMetric.objects.filter(date__gte=start_date)


# ========== SALES ANALYTICS ==========

class SalesAnalyticsView(APIView):
    """Get detailed sales analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get date range
        period = request.query_params.get('period', 'month')  # day, week, month, year, custom
        
        today = timezone.now().date()
        
        if period == 'day':
            start_date = today
            end_date = today
            prev_start = today - timedelta(days=1)
            prev_end = today - timedelta(days=1)
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
            prev_month = start_date - timedelta(days=1)
            prev_start = prev_month.replace(day=1)
            prev_end = prev_month
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
            prev_start = start_date.replace(year=start_date.year - 1)
            prev_end = prev_start.replace(year=prev_start.year, month=12, day=31)
        else:  # custom
            start_date = datetime.fromisoformat(request.query_params.get('start_date')).date()
            end_date = datetime.fromisoformat(request.query_params.get('end_date')).date()
            days_diff = (end_date - start_date).days
            prev_start = start_date - timedelta(days=days_diff + 1)
            prev_end = start_date - timedelta(days=1)
        
        # Current period transactions
        transactions = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Previous period for comparison
        prev_transactions = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__date__gte=prev_start,
            created_at__date__lte=prev_end
        )
        
        # Calculate metrics
        total_sales = transactions.aggregate(total=Sum('total_amount'))['total'] or 0
        total_transactions = transactions.count()
        total_items = TransactionItem.objects.filter(
            transaction__in=transactions
        ).aggregate(total=Sum('quantity'))['total'] or 0
        total_profit = sum(t.profit for t in transactions)
        average_transaction = total_sales / total_transactions if total_transactions > 0 else 0
        
        # Calculate cost and profit margin
        total_cost = sum(
            item.product.cost_price * item.quantity
            for t in transactions
            for item in t.items.all()
        )
        profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
        
        # Growth comparison
        prev_sales = prev_transactions.aggregate(total=Sum('total_amount'))['total'] or 0
        prev_count = prev_transactions.count()
        
        sales_growth = ((total_sales - prev_sales) / prev_sales * 100) if prev_sales > 0 else 0
        transaction_growth = ((total_transactions - prev_count) / prev_count * 100) if prev_count > 0 else 0
        
        # Payment breakdown
        payment_breakdown = transactions.values('payment_method').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Category breakdown
        category_breakdown = TransactionItem.objects.filter(
            transaction__in=transactions
        ).values(
            'product__category__name'
        ).annotate(
            total_sales=Sum('line_total'),
            total_quantity=Sum('quantity')
        ).order_by('-total_sales')
        
        # Top products
        top_products = TransactionItem.objects.filter(
            transaction__in=transactions
        ).values(
            'product__id', 'product__name', 'product__sku'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('line_total')
        ).order_by('-total_sales')[:10]
        
        # Hourly distribution
        hourly_sales = transactions.extra(
            select={'hour': 'EXTRACT(hour FROM created_at)'}
        ).values('hour').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('hour')
        
        # Daily trend
        daily_trend = transactions.extra(
            select={'day': 'DATE(created_at)'}
        ).values('day').annotate(
            total=Sum('total_amount'),
            count=Count('id'),
            items=Sum('items__quantity')
        ).order_by('day')
        
        data = {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'total_sales': float(total_sales),
            'total_transactions': total_transactions,
            'total_items_sold': total_items,
            'total_profit': float(total_profit),
            'average_transaction': float(average_transaction),
            'profit_margin': float(profit_margin),
            'sales_growth': float(sales_growth),
            'transaction_growth': float(transaction_growth),
            'payment_breakdown': list(payment_breakdown),
            'category_breakdown': list(category_breakdown),
            'top_products': list(top_products),
            'hourly_sales': list(hourly_sales),
            'daily_trend': list(daily_trend)
        }
        
        serializer = SalesAnalyticsSerializer(data)
        return Response(serializer.data)


# ========== INVENTORY ANALYTICS ==========

class InventoryAnalyticsView(APIView):
    """Get detailed inventory analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Basic metrics
        total_products = Product.objects.count()
        active_products = Product.objects.filter(is_active=True).count()
        
        total_inventory_value = Product.objects.filter(is_active=True).aggregate(
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
        
        expired_products = Product.objects.filter(
            expiry_date__lt=timezone.now().date(),
            is_active=True
        ).count()
        
        # Stock age (average days since product was created)
        from django.db.models import Avg
        from django.db.models.functions import ExtractDay
        average_stock_age = Product.objects.filter(is_active=True).annotate(
            age=ExtractDay(timezone.now() - F('created_at'))
        ).aggregate(avg=Avg('age'))['avg'] or 0
        
        # Fast moving products (sold most in last 30 days)
        last_30_days = timezone.now() - timedelta(days=30)
        fast_moving = TransactionItem.objects.filter(
            transaction__status='COMPLETED',
            transaction__created_at__gte=last_30_days
        ).values(
            'product__id', 'product__name', 'product__current_stock'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')[:10]
        
        # Slow moving products (low sales in last 30 days)
        slow_moving = Product.objects.filter(
            is_active=True
        ).annotate(
            sold=Sum(
                'transaction_items__quantity',
                filter=Q(
                    transaction_items__transaction__status='COMPLETED',
                    transaction_items__transaction__created_at__gte=last_30_days
                )
            )
        ).filter(
            Q(sold__isnull=True) | Q(sold__lte=5)
        ).values('id', 'name', 'current_stock', 'sold')[:10]
        
        # Category distribution
        category_distribution = Product.objects.filter(is_active=True).values(
            'category__name'
        ).annotate(
            product_count=Count('id'),
            total_stock=Sum('current_stock'),
            total_value=Sum(F('current_stock') * F('cost_price'))
        ).order_by('-total_value')
        
        # Stock movements (last 30 days)
        stock_in_total = InventoryMovement.objects.filter(
            movement_type='STOCK_IN',
            created_at__gte=last_30_days
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        stock_out_total = InventoryMovement.objects.filter(
            movement_type__in=['STOCK_OUT', 'SALE'],
            created_at__gte=last_30_days
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        adjustments_total = InventoryMovement.objects.filter(
            movement_type='ADJUSTMENT',
            created_at__gte=last_30_days
        ).count()
        
        data = {
            'total_products': total_products,
            'active_products': active_products,
            'total_inventory_value': float(total_inventory_value),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'expired_products': expired_products,
            'average_stock_age': int(average_stock_age),
            'fast_moving_products': list(fast_moving),
            'slow_moving_products': list(slow_moving),
            'category_distribution': list(category_distribution),
            'stock_in_total': stock_in_total,
            'stock_out_total': stock_out_total,
            'adjustments_total': adjustments_total
        }
        
        serializer = InventoryAnalyticsSerializer(data)
        return Response(serializer.data)


# ========== PROFIT & LOSS REPORT ==========

class ProfitLossReportView(APIView):
    """Get profit & loss report"""
    permission_classes = [IsAuthenticated, IsOwner]
    
    def get(self, request):
        # Get date range
        period = request.query_params.get('period', 'month')
        today = timezone.now().date()
        
        if period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:  # custom
            start_date = datetime.fromisoformat(request.query_params.get('start_date')).date()
            end_date = datetime.fromisoformat(request.query_params.get('end_date')).date()
        
        # Get transactions
        transactions = SalesTransaction.objects.filter(
            status='COMPLETED',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Revenue calculations
        gross_sales = transactions.aggregate(
            total=Sum('subtotal')
        )['total'] or 0
        
        discounts = transactions.aggregate(
            total=Sum('discount')
        )['total'] or 0
        
        net_sales = transactions.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Cost of goods sold
        cost_of_goods_sold = sum(
            item.product.cost_price * item.quantity
            for t in transactions
            for item in t.items.all()
        )
        
        # Gross profit
        gross_profit = net_sales - cost_of_goods_sold
        gross_profit_margin = (gross_profit / net_sales * 100) if net_sales > 0 else 0
        
        # Operating expenses (placeholder)
        operating_expenses = 0  # Can be expanded later
        
        # Net profit
        net_profit = gross_profit - operating_expenses
        net_profit_margin = (net_profit / net_sales * 100) if net_sales > 0 else 0
        
        # Profit by category
        profit_by_category = []
        for category in Category.objects.filter(is_active=True):
            cat_items = TransactionItem.objects.filter(
                transaction__in=transactions,
                product__category=category
            )
            
            cat_revenue = cat_items.aggregate(total=Sum('line_total'))['total'] or 0
            cat_cost = sum(
                item.product.cost_price * item.quantity
                for item in cat_items
            )
            cat_profit = cat_revenue - cat_cost
            
            if cat_revenue > 0:
                profit_by_category.append({
                    'category': category.name,
                    'revenue': float(cat_revenue),
                    'cost': float(cat_cost),
                    'profit': float(cat_profit),
                    'margin': float((cat_profit / cat_revenue * 100))
                })
        
        profit_by_category.sort(key=lambda x: x['profit'], reverse=True)
        
        # Top profitable products
        profit_by_product = []
        product_items = TransactionItem.objects.filter(
            transaction__in=transactions
        ).values(
            'product__id', 'product__name', 'product__cost_price'
        ).annotate(
            revenue=Sum('line_total'),
            quantity=Sum('quantity')
        )
        
        for item in product_items:
            cost = item['product__cost_price'] * item['quantity']
            profit = item['revenue'] - cost
            
            profit_by_product.append({
                'product': item['product__name'],
                'revenue': float(item['revenue']),
                'cost': float(cost),
                'profit': float(profit),
                'quantity': item['quantity']
            })
        
        profit_by_product.sort(key=lambda x: x['profit'], reverse=True)
        profit_by_product = profit_by_product[:15]  # Top 15
        
        data = {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'gross_sales': float(gross_sales),
            'discounts': float(discounts),
            'net_sales': float(net_sales),
            'cost_of_goods_sold': float(cost_of_goods_sold),
            'gross_profit': float(gross_profit),
            'gross_profit_margin': float(gross_profit_margin),
            'operating_expenses': float(operating_expenses),
            'net_profit': float(net_profit),
            'net_profit_margin': float(net_profit_margin),
            'profit_by_category': profit_by_category,
            'profit_by_product': profit_by_product
        }
        
        serializer = ProfitLossSerializer(data)
        return Response(serializer.data)


# ========== STAFF PERFORMANCE ==========

class StaffPerformanceView(APIView):
    """Get staff performance report"""
    permission_classes = [IsAuthenticated, IsOwner]
    
    def get(self, request):
        # Get date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            # Default to current month
            today = timezone.now().date()
            start_date = today.replace(day=1)
            end_date = today
        else:
            start_date = datetime.fromisoformat(start_date).date()
            end_date = datetime.fromisoformat(end_date).date()
        
        # Get all staff users
        from accounts.models import User
        staff_users = User.objects.filter(role='STAFF', is_active=True)
        
        performance_data = []
        
        for user in staff_users:
            transactions = SalesTransaction.objects.filter(
                status='COMPLETED',
                created_by=user,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
            
            total_sales = transactions.aggregate(total=Sum('total_amount'))['total'] or 0
            total_transactions = transactions.count()
            total_items = TransactionItem.objects.filter(
                transaction__in=transactions
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            average_transaction = total_sales / total_transactions if total_transactions > 0 else 0
            
            days_worked = (end_date - start_date).days + 1
            transactions_per_day = total_transactions / days_worked if days_worked > 0 else 0
            
            # Best selling day
            best_day = transactions.extra(
                select={'day': 'DATE(created_at)'}
            ).values('day').annotate(
                total=Sum('total_amount')
            ).order_by('-total').first()
            
            best_selling_day = best_day['day'] if best_day else start_date
            best_selling_day_amount = best_day['total'] if best_day else 0
            
            performance_data.append({
                'staff_id': user.id,
                'staff_name': user.full_name,
                'total_sales': float(total_sales),
                'total_transactions': total_transactions,
                'total_items_sold': total_items,
                'average_transaction': float(average_transaction),
                'transactions_per_day': float(transactions_per_day),
                'best_selling_day': best_selling_day,
                'best_selling_day_amount': float(best_selling_day_amount)
            })
        
        # Sort by total sales
        performance_data.sort(key=lambda x: x['total_sales'], reverse=True)
        
        serializer = StaffPerformanceSerializer(performance_data, many=True)
        return Response(serializer.data)


# ========== REPORT MANAGEMENT ==========

class ReportExportView(APIView):
    """Export report to file"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create export record
        export = ReportExport.objects.create(
            report_type=serializer.validated_data['report_type'],
            export_format=serializer.validated_data['export_format'],
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date'),
            filters=serializer.validated_data.get('filters'),
            created_by=request.user,
            status='PENDING'
        )
        
        # TODO: Implement actual export logic (PDF/CSV generation)
        # For now, just mark as completed
        export.status = 'COMPLETED'
        export.completed_at = timezone.now()
        export.file_path = f'/exports/{export.report_type}_{export.id}.{export.export_format.lower()}'
        export.save()
        
        return Response({
            'message': 'Export created successfully',
            'export': ReportExportSerializer(export).data
        }, status=status.HTTP_201_CREATED)


class ReportExportListView(generics.ListAPIView):
    """List all report exports"""
    serializer_class = ReportExportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ReportExport.objects.filter(created_by=self.request.user).order_by('-created_at')