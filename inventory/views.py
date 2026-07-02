from rest_framework import viewsets, filters, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from .models import Category, Manufacturer, Brand, Product, Batch, PurchaseBill, Wishlist, Supplier, GoodsReceivedNote, SupplierPayment
from .serializers import CategorySerializer, ManufacturerSerializer, BrandSerializer, ProductSerializer, BatchSerializer, PurchaseBillSerializer, SupplierSerializer, GoodsReceivedNoteSerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]

class ManufacturerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [AllowAny]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).order_by('-id')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'generic_name', 'brand__name', 'category__name', 'manufacturer__name', 'barcode']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role == 'admin':
            queryset = Product.objects.all().order_by('-id')
        else:
            queryset = Product.objects.filter(is_active=True).order_by('-id')
            
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
            
        is_active_param = self.request.query_params.get('is_active')
        if is_active_param is not None:
            is_active_val = is_active_param.lower() == 'true'
            queryset = queryset.filter(is_active=is_active_val)
            
        return queryset

    @action(detail=False, methods=['post'], url_path='import-excel')
    def import_excel(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            import pandas as pd
            df = pd.read_excel(file)
            
            required_cols = ['name', 'mrp', 'wholesale_price']
            for col in required_cols:
                if col not in df.columns:
                    return Response({'error': f'Missing required column: {col}'}, status=status.HTTP_400_BAD_REQUEST)
            
            imported_count = 0
            for index, row in df.iterrows():
                name = str(row['name']).strip()
                if not name or name == 'nan':
                    continue
                    
                mrp = row['mrp']
                wholesale_price = row['wholesale_price']
                
                generic_name = str(row.get('generic_name', '')).strip()
                if generic_name == 'nan': generic_name = ''
                
                description = str(row.get('description', '')).strip()
                if description == 'nan': description = ''
                
                pack_size = str(row.get('pack_size', '')).strip()
                if pack_size == 'nan': pack_size = ''
                
                barcode = str(row.get('barcode', '')).strip()
                if barcode == 'nan' or not barcode:
                    barcode = None
                    
                gst_rate = row.get('gst_rate', 12.0)
                if pd.isna(gst_rate): gst_rate = 12.0
                
                stock_status = str(row.get('stock_status', 'out_of_stock')).strip()
                if stock_status not in ['in_stock', 'low_stock', 'out_of_stock']:
                    stock_status = 'out_of_stock'
                    
                is_active = row.get('is_active', True)
                if pd.isna(is_active): is_active = True
                
                min_order_quantity = row.get('min_order_quantity', 1)
                if pd.isna(min_order_quantity): min_order_quantity = 1
                
                category_name = str(row.get('category', '')).strip()
                category_obj = None
                if category_name and category_name != 'nan':
                    category_obj, _ = Category.objects.get_or_create(name=category_name)
                    
                product, created = Product.objects.update_or_create(
                    name=name,
                    defaults={
                        'generic_name': generic_name or None,
                        'category': category_obj,
                        'description': description or None,
                        'pack_size': pack_size or None,
                        'barcode': barcode,
                        'mrp': mrp,
                        'wholesale_price': wholesale_price,
                        'gst_rate': gst_rate,
                        'is_active': bool(is_active),
                        'min_order_quantity': int(min_order_quantity),
                        'stock_status': stock_status
                    }
                )
                imported_count += 1
                
            return Response({'message': f'Successfully imported {imported_count} medicines.'})
        except Exception as e:
            return Response({'error': f'Error parsing Excel file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='export-excel')
    def export_excel(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        import pandas as pd
        from django.http import HttpResponse
        import io
        
        products = Product.objects.all()
        data = []
        for p in products:
            data.append({
                'name': p.name,
                'generic_name': p.generic_name or '',
                'category': p.category.name if p.category else '',
                'description': p.description or '',
                'pack_size': p.pack_size or '',
                'barcode': p.barcode or '',
                'mrp': float(p.mrp),
                'wholesale_price': float(p.wholesale_price),
                'gst_rate': float(p.gst_rate),
                'stock_status': p.stock_status,
                'is_active': p.is_active,
                'min_order_quantity': p.min_order_quantity
            })
            
        df = pd.DataFrame(data)
        if df.empty:
            df = pd.DataFrame(columns=[
                'name', 'generic_name', 'category', 'description', 'pack_size', 
                'barcode', 'mrp', 'wholesale_price', 'gst_rate', 'stock_status', 
                'is_active', 'min_order_quantity'
            ])
            
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Medicines', index=False)
            
        output.seek(0)
        response = HttpResponse(
            output.read(), 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="AbinPharma_Medicines_Export.xlsx"'
        return response

    @action(detail=False, methods=['post'], url_path='delete-all')
    def delete_all(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        try:
            count, _ = Product.objects.all().delete()
            return Response({'message': f'Successfully deleted {count} medicines completely.'})
        except Exception as e:
            return Response({'error': f'Error deleting medicines: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

class BatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Batch.objects.filter(stock_quantity__gt=0)
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]

class GoodsReceivedNoteViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceivedNote.objects.all()
    serializer_class = GoodsReceivedNoteSerializer
    permission_classes = [IsAuthenticated]

class PurchaseBillViewSet(viewsets.ModelViewSet):
    queryset = PurchaseBill.objects.all().order_by('-date')
    serializer_class = PurchaseBillSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def update_payment_status(self, request, pk=None):
        bill = self.get_object()
        status_val = request.data.get('status')
        if status_val == 'completed':
            total_paid = sum(p.amount_paid for p in bill.payments.all())
            remaining = bill.total_amount - total_paid
            if remaining > 0:
                SupplierPayment.objects.create(
                    bill=bill,
                    amount_paid=remaining,
                    payment_mode='cash'
                )
            return Response({'status': 'completed'})
        elif status_val == 'pending':
            bill.payments.all().delete()
            return Response({'status': 'pending'})
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

class WishlistView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist = Wishlist.objects.filter(user=request.user)
        products = [item.product for item in wishlist]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    def post(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'Product ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(id=product_id)
            Wishlist.objects.get_or_create(user=request.user, product=product)
            return Response({'message': 'Added to wishlist'})
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
            
    def delete(self, request):
        product_id = request.data.get('product_id')
        Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
        return Response({'message': 'Removed from wishlist'})

class LowStockAlertView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        products = Product.objects.filter(stock_status='low_stock')
        # Alternatively dynamically calculate based on min_order_quantity
        low_stock_products = []
        for p in Product.objects.filter(is_active=True):
            total_stock = sum(b.stock_quantity for b in p.batches.all())
            if total_stock <= p.min_order_quantity:
                low_stock_products.append({
                    'id': p.id,
                    'name': p.name,
                    'brand': p.brand.name if p.brand else '',
                    'total_stock': total_stock,
                    'min_required': p.min_order_quantity
                })
        return Response(low_stock_products)

class NearExpiryAlertView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import datetime
        from django.utils import timezone
        
        ninety_days_from_now = timezone.now().date() + datetime.timedelta(days=90)
        batches = Batch.objects.filter(stock_quantity__gt=0, expiry_date__lte=ninety_days_from_now).order_by('expiry_date')
        
        near_expiry_batches = []
        for b in batches:
            near_expiry_batches.append({
                'product_name': b.product.name,
                'batch_number': b.batch_number,
                'stock_quantity': b.stock_quantity,
                'expiry_date': b.expiry_date
            })
            
        return Response(near_expiry_batches)
