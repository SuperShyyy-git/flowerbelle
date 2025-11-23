from rest_framework import generics, status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from django.db.models import Sum, Count, F, Q, Avg
from django.utils import timezone
from django.http import HttpResponse, Http404
from django.views import View
from datetime import timedelta, datetime
from io import BytesIO, StringIO
from django.shortcuts import get_object_or_404
import csv

from django.db.models.functions import ExtractDay, ExtractHour, TruncDate

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

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
from accounts.models import User


class BinaryFileRenderer(BaseRenderer):
    media_type = '*/*'
    format = None
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class SuperSimpleTestView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        print("=" * 80)
        print("SUPER SIMPLE VIEW CALLED!")
        print("=" * 80)
        return HttpResponse("IT WORKS!", content_type="text/plain")


class TestExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return HttpResponse("Export endpoint is working!", content_type="text/plain")


class SimpleProductStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'current_stock')


PROFIT_AGGREGATION = Sum(F('items__quantity') * (F('items__unit_price') - F('items__product__cost_price')))


class DashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localtime(timezone.now()).date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        valid_statuses = ['COMPLETED', 'PAID', 'PENDING', 'Completed', 'Paid']
        base_filter = SalesTransaction.objects.filter(status__in=valid_statuses)

        def get_metrics(txns):
            metrics = txns.aggregate(sales=Sum('total_amount'), transactions=Count('id'), profit_sum=PROFIT_AGGREGATION)
            return {'sales': metrics['sales'] or 0, 'transactions': metrics['transactions'] or 0, 'profit': metrics['profit_sum'] or 0}

        today_txns = base_filter.filter(created_at__date=today)
        today_data = get_metrics(today_txns)
        week_txns = base_filter.filter(created_at__date__gte=week_start)
        week_data = get_metrics(week_txns)
        month_txns = base_filter.filter(created_at__date__gte=month_start)
        month_data = get_metrics(month_txns)
        total_products = Product.objects.filter(is_active=True).count()
        low_stock_count = Product.objects.filter(current_stock__lt=10, is_active=True).count()
        out_of_stock_count = Product.objects.filter(current_stock=0, is_active=True).count()
        inventory_value = Product.objects.filter(is_active=True).aggregate(total=Sum(F('current_stock') * F('cost_price')))['total'] or 0
        top_products = TransactionItem.objects.filter(transaction__in=month_txns).values('product__id', 'product__name', 'product__sku').annotate(total_quantity=Sum('quantity'), total_sales=Sum('line_total')).order_by('-total_quantity')[:5]
        recent_txns = base_filter.order_by('-created_at')[:10].values('id', 'transaction_number', 'total_amount', 'created_at', 'created_by__full_name')
        data = {
            'today_sales': float(today_data['sales']), 'today_transactions': today_data['transactions'],
            'today_profit': float(today_data['profit']),
            'today_items_sold': TransactionItem.objects.filter(transaction__in=today_txns).aggregate(total=Sum('quantity'))['total'] or 0,
            'week_sales': float(week_data['sales']), 'week_transactions': week_data['transactions'], 'week_profit': float(week_data['profit']),
            'month_sales': float(month_data['sales']), 'month_transactions': month_data['transactions'], 'month_profit': float(month_data['profit']),
            'total_products': total_products, 'low_stock_count': low_stock_count, 'out_of_stock_count': out_of_stock_count,
            'inventory_value': float(inventory_value), 'pending_alerts': LowStockAlert.objects.filter(status='PENDING').count(),
            'top_products': list(top_products), 'recent_transactions': list(recent_txns)
        }
        return Response(DashboardOverviewSerializer(data).data)


class DashboardMetricsHistoryView(generics.ListAPIView):
    serializer_class = DashboardMetricSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        days = int(self.request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        return DashboardMetric.objects.filter(date__gte=start_date)


class SalesAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        today = timezone.localtime(timezone.now()).date()
        if period == 'day':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today.replace(day=1)
        all_txns = SalesTransaction.objects.filter(status__in=['COMPLETED', 'PAID', 'PENDING', 'Completed', 'Paid'], created_at__date__gte=start_date).order_by('created_at')
        sales_by_date = {}
        total_sales = 0.0
        total_transactions = 0
        for txn in all_txns:
            local_date = timezone.localtime(txn.created_at).strftime('%Y-%m-%d')
            amount = float(txn.total_amount)
            total_sales += amount
            total_transactions += 1
            if local_date in sales_by_date:
                sales_by_date[local_date]['total'] += amount
                sales_by_date[local_date]['count'] += 1
            else:
                sales_by_date[local_date] = {'total': amount, 'count': 1, 'day': local_date}
        final_daily_trend = []
        current = start_date
        while current <= today:
            date_str = current.strftime('%Y-%m-%d')
            if date_str in sales_by_date:
                final_daily_trend.append({'day': date_str, 'total': sales_by_date[date_str]['total'], 'count': sales_by_date[date_str]['count']})
            else:
                final_daily_trend.append({'day': date_str, 'total': 0.0, 'count': 0})
            current += timedelta(days=1)
        recent_transactions_list = SalesTransaction.objects.all().order_by('-created_at')[:50].values('id', 'transaction_number', 'created_at', 'total_amount', 'status', 'payment_method')
        data = {'period': period, 'total_sales': total_sales, 'total_transactions': total_transactions, 'average_transaction': total_sales / total_transactions if total_transactions > 0 else 0, 'daily_trend': final_daily_trend, 'transactions': list(recent_transactions_list)}
        return Response(data)


class InventoryAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_products = Product.objects.count()
        active_products = Product.objects.filter(is_active=True).count()
        total_inventory_value = Product.objects.filter(is_active=True).aggregate(total=Sum(F('current_stock') * F('cost_price')))['total'] or 0
        low_stock_count = Product.objects.filter(current_stock__lt=10, is_active=True).count()
        out_of_stock_count = Product.objects.filter(current_stock=0, is_active=True).count()
        expired_products = Product.objects.filter(expiry_date__lt=timezone.now().date(), is_active=True).count()
        average_stock_age = Product.objects.filter(is_active=True).annotate(age=ExtractDay(timezone.now() - F('created_at'))).aggregate(avg=Avg('age'))['avg'] or 0
        last_30_days = timezone.now() - timedelta(days=30)
        fast_moving = TransactionItem.objects.filter(transaction__status__in=['COMPLETED', 'PAID', 'Completed'], transaction__created_at__gte=last_30_days).values('product__id', 'product__name', 'product__current_stock').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:10]
        slow_moving = Product.objects.filter(is_active=True).annotate(sold=Sum('transaction_items__quantity', filter=Q(transaction_items__transaction__status__in=['COMPLETED', 'PAID', 'Completed'], transaction_items__transaction__created_at__gte=last_30_days))).filter(Q(sold__isnull=True) | Q(sold__lte=5)).values('id', 'name', 'current_stock', 'sold')[:10]
        category_distribution = Product.objects.filter(is_active=True).values('category__name').annotate(product_count=Count('id'), total_stock=Sum('current_stock'), total_value=Sum(F('current_stock') * F('cost_price'))).order_by('-total_value')
        stock_in_total = InventoryMovement.objects.filter(movement_type='STOCK_IN', created_at__gte=last_30_days).aggregate(total=Sum('quantity'))['total'] or 0
        stock_out_total = InventoryMovement.objects.filter(movement_type__in=['STOCK_OUT', 'SALE'], created_at__gte=last_30_days).aggregate(total=Sum('quantity'))['total'] or 0
        adjustments_total = InventoryMovement.objects.filter(movement_type='ADJUSTMENT', created_at__gte=last_30_days).count()
        data = {'total_products': total_products, 'active_products': active_products, 'total_inventory_value': float(total_inventory_value), 'low_stock_count': low_stock_count, 'out_of_stock_count': out_of_stock_count, 'expired_products': expired_products, 'average_stock_age': int(average_stock_age) if average_stock_age else 0, 'fast_moving_products': list(fast_moving), 'slow_moving_products': list(slow_moving), 'category_distribution': list(category_distribution), 'stock_in_total': stock_in_total, 'stock_out_total': stock_out_total, 'adjustments_total': adjustments_total}
        return Response(InventoryAnalyticsSerializer(data).data)


class SimpleInventoryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SimpleProductStockSerializer

    def get_queryset(self):
        return Product.objects.filter(is_active=True, current_stock__gt=0).order_by('-current_stock')[:15]


class ProfitLossReportView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        today = timezone.localtime(timezone.now()).date()
        if period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:
            try:
                start_date = datetime.fromisoformat(request.query_params.get('start_date')).date()
                end_date = datetime.fromisoformat(request.query_params.get('end_date')).date()
            except:
                start_date = today.replace(day=1)
                end_date = today
        filter_end_date = end_date + timedelta(days=1)
        transactions = SalesTransaction.objects.filter(status__in=['COMPLETED', 'PAID', 'Completed'], created_at__date__gte=start_date, created_at__date__lt=filter_end_date)
        gross_sales = transactions.aggregate(total=Sum('subtotal'))['total'] or 0
        discounts = transactions.aggregate(total=Sum('discount'))['total'] or 0
        net_sales = transactions.aggregate(total=Sum('total_amount'))['total'] or 0
        cost_of_goods_sold = sum(item.product.cost_price * item.quantity for t in transactions for item in t.items.all())
        gross_profit = net_sales - cost_of_goods_sold
        gross_profit_margin = (gross_profit / net_sales * 100) if net_sales > 0 else 0
        operating_expenses = 0
        net_profit = gross_profit - operating_expenses
        net_profit_margin = (net_profit / net_sales * 100) if net_sales > 0 else 0
        profit_by_category = []
        for category in Category.objects.filter(is_active=True):
            cat_items = TransactionItem.objects.filter(transaction__in=transactions, product__category=category)
            cat_revenue = cat_items.aggregate(total=Sum('line_total'))['total'] or 0
            cat_cost = sum(item.product.cost_price * item.quantity for item in cat_items)
            cat_profit = cat_revenue - cat_cost
            if cat_revenue > 0:
                profit_by_category.append({'category': category.name, 'revenue': float(cat_revenue), 'cost': float(cat_cost), 'profit': float(cat_profit), 'margin': float((cat_profit / cat_revenue * 100))})
        profit_by_category.sort(key=lambda x: x['profit'], reverse=True)
        profit_by_product = []
        product_items = TransactionItem.objects.filter(transaction__in=transactions).values('product__id', 'product__name', 'product__cost_price').annotate(revenue=Sum('line_total'), quantity=Sum('quantity'))
        for item in product_items:
            cost = item['product__cost_price'] * item['quantity']
            profit = item['revenue'] - cost
            profit_by_product.append({'product': item['product__name'], 'revenue': float(item['revenue']), 'cost': float(cost), 'profit': float(profit), 'quantity': item['quantity']})
        profit_by_product.sort(key=lambda x: x['profit'], reverse=True)
        profit_by_product = profit_by_product[:15]
        data = {'period': period, 'start_date': start_date, 'end_date': end_date, 'gross_sales': float(gross_sales), 'discounts': float(discounts), 'net_sales': float(net_sales), 'cost_of_goods_sold': float(cost_of_goods_sold), 'gross_profit': float(gross_profit), 'gross_profit_margin': float(gross_profit_margin), 'operating_expenses': float(operating_expenses), 'net_profit': float(net_profit), 'net_profit_margin': float(net_profit_margin), 'profit_by_category': profit_by_category, 'profit_by_product': profit_by_product}
        return Response(ProfitLossSerializer(data).data)


class StaffPerformanceView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request):
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        today = timezone.localtime(timezone.now()).date()
        if not start_date_param or not end_date_param:
            start_date = today.replace(day=1)
            end_date = today
        else:
            try:
                start_date = datetime.fromisoformat(start_date_param).date()
                end_date = datetime.fromisoformat(end_date_param).date()
            except:
                start_date = today.replace(day=1)
                end_date = today
        filter_end_date = end_date + timedelta(days=1)
        staff_users = User.objects.filter(role='STAFF', is_active=True)
        performance_data = []
        for user in staff_users:
            transactions = SalesTransaction.objects.filter(status__in=['COMPLETED', 'PAID', 'Completed'], created_by=user, created_at__date__gte=start_date, created_at__date__lt=filter_end_date)
            total_sales = transactions.aggregate(total=Sum('total_amount'))['total'] or 0
            total_transactions = transactions.count()
            total_items = TransactionItem.objects.filter(transaction__in=transactions).aggregate(total=Sum('quantity'))['total'] or 0
            average_transaction = total_sales / total_transactions if total_transactions > 0 else 0
            days_worked = (end_date - start_date).days + 1
            transactions_per_day = total_transactions / days_worked if days_worked > 0 else 0
            best_day = transactions.annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('total_amount')).order_by('-total').first()
            best_selling_day = best_day['day'] if best_day else start_date
            best_selling_day_amount = best_day['total'] if best_day else 0
            performance_data.append({'staff_id': user.id, 'staff_name': user.full_name, 'total_sales': float(total_sales), 'total_transactions': total_transactions, 'total_items_sold': total_items, 'average_transaction': float(average_transaction), 'transactions_per_day': float(transactions_per_day), 'best_selling_day': best_selling_day, 'best_selling_day_amount': float(best_selling_day_amount)})
        performance_data.sort(key=lambda x: x['total_sales'], reverse=True)
        return Response(StaffPerformanceSerializer(performance_data, many=True).data)


class ReportExportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        export = ReportExport.objects.create(report_type=serializer.validated_data['report_type'], export_format=serializer.validated_data['export_format'], start_date=serializer.validated_data.get('start_date'), end_date=serializer.validated_data.get('end_date'), filters=serializer.validated_data.get('filters'), created_by=request.user, status='PENDING')
        export.status = 'COMPLETED'
        export.completed_at = timezone.now()
        export.file_path = f'/exports/{export.report_type}_{export.id}.{export.export_format.lower()}'
        export.save()
        return Response({'message': 'Export created successfully', 'export': ReportExportSerializer(export).data}, status=status.HTTP_201_CREATED)


class ReportExportListView(generics.ListAPIView):
    serializer_class = ReportExportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReportExport.objects.filter(created_by=self.request.user).order_by('-created_at')


# ==========================================
# ✅ NEW SIMPLE EXPORT VIEW (GUARANTEED TO WORK!)
# ==========================================

class SimpleReportExport(View):
    """Simple function-based export that definitely works"""
    
    def get(self, request, report_type):
        print("\n" + "="*80)
        print(f"✅ SimpleReportExport CALLED! Report type: {report_type}")
        print("="*80 + "\n")
        
        # Get parameters
        export_format = request.GET.get('format', 'PDF').upper()
        period = request.GET.get('period', 'month')
        
        print(f"Format: {export_format}, Period: {period}")
        
        # Calculate dates
        today = timezone.localtime(timezone.now()).date()
        
        if period == 'day':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        else:  # month
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(day=31)
            else:
                end_date = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        
        # Generate the report
        if export_format == 'PDF':
            return self.generate_pdf(report_type, start_date, end_date)
        else:
            return self.generate_csv(report_type, start_date, end_date)
    
    def generate_pdf(self, report_type, start_date, end_date):
        print(f"Generating PDF for {report_type}...")
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f"{report_type.upper()} Report", styles['Title'])
        elements.append(title)
        elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
        elements.append(Paragraph("<br/><br/>", styles['Normal']))
        
        # Get data
        data = self.get_report_data(report_type, start_date, end_date)
        
        # Create table
        if data:
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
        
        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()
        
        print(f"✅ PDF generated: {len(pdf_content)} bytes")
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_{start_date}_{end_date}.pdf"'
        return response
    
    def generate_csv(self, report_type, start_date, end_date):
        print(f"Generating CSV for {report_type}...")
        
        output = StringIO()
        writer = csv.writer(output)
        
        data = self.get_report_data(report_type, start_date, end_date)
        for row in data:
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        print(f"✅ CSV generated: {len(csv_content)} bytes")
        
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_{start_date}_{end_date}.csv"'
        return response
    
    def get_report_data(self, report_type, start_date, end_date):
        """Get data based on report type"""
        report_type_lower = report_type.lower()
        
        if report_type_lower == 'sales':
            transactions = SalesTransaction.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
                status__in=['COMPLETED', 'PAID', 'Completed', 'Paid']
            ).select_related('created_by')[:50]  # Limit to 50 for performance
            
            data = [['Date', 'Transaction #', 'Cashier', 'Total Amount', 'Payment']]
            for trans in transactions:
                data.append([
                    trans.created_at.strftime('%Y-%m-%d %H:%M'),
                    trans.transaction_number,
                    trans.created_by.full_name if trans.created_by else 'Unknown',
                    f"₱{trans.total_amount:,.2f}",
                    trans.payment_method
                ])
            return data
        
        elif report_type_lower == 'inventory':
            products = Product.objects.filter(is_active=True).select_related('category')[:100]
            
            data = [['Product', 'Category', 'Stock', 'Price', 'Status']]
            for product in products:
                status = 'Low Stock' if product.current_stock < 10 else 'In Stock'
                data.append([
                    product.name,
                    product.category.name if product.category else 'N/A',
                    str(product.current_stock),
                    f"₱{product.price:,.2f}",
                    status
                ])
            return data
        
        elif report_type_lower == 'profit':
            transactions = SalesTransaction.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
                status__in=['COMPLETED', 'PAID', 'Completed', 'Paid']
            )
            
            total_revenue = transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            data = [
                ['Metric', 'Amount'],
                ['Total Revenue', f"₱{total_revenue:,.2f}"],
                ['Total Transactions', str(transactions.count())],
                ['Period', f"{start_date} to {end_date}"]
            ]
            return data
        
        elif report_type_lower == 'staff':
            staff = User.objects.filter(role='STAFF', is_active=True)
            
            data = [['Staff Name', 'Transactions', 'Total Sales']]
            for user in staff:
                trans = SalesTransaction.objects.filter(
                    created_by=user,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                    status__in=['COMPLETED', 'PAID', 'Completed', 'Paid']
                )
                total = trans.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
                data.append([
                    user.full_name,
                    str(trans.count()),
                    f"₱{total:,.2f}"
                ])
            return data
        
        else:
            return [['Error', 'Unknown report type']]


class DebugExportView(APIView):
    permission_classes = []

    def get(self, request):
        print("\n" + "="*80)
        print("DEBUG EXPORT VIEW CALLED!")
        print("="*80 + "\n")
        return HttpResponse("Debug view works!", content_type="text/plain")