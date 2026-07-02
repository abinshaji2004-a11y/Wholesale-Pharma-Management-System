from rest_framework import viewsets, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Cart, CartItem, Order, OrderItem, Coupon, Payment
from inventory.models import Product
from decimal import Decimal
from .serializers import CartSerializer, OrderSerializer, ReturnSerializer
from .models import Return
import uuid
import csv
import io

class CartView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def post(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id)
            item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
            if not item_created:
                item.quantity += quantity
            else:
                item.quantity = quantity
            item.save()
            return Response(CartSerializer(cart).data)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id)
            item = CartItem.objects.filter(cart=cart, product=product).first()
            if item:
                if quantity <= 0:
                    item.delete()
                else:
                    item.quantity = quantity
                    item.save()
            else:
                if quantity > 0:
                    CartItem.objects.create(cart=cart, product=product, quantity=quantity)
            return Response(CartSerializer(cart).data)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id)
            CartItem.objects.filter(cart=cart, product=product).delete()
            return Response(CartSerializer(cart).data)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

class CheckoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        shipping_address = request.data.get('shipping_address', '')
        if not shipping_address:
            return Response({'error': 'Shipping address required'}, status=status.HTTP_400_BAD_REQUEST)
            
        phone = request.data.get('phone', '')
        if phone:
            user = request.user
            user.phone_number = phone
            user.save()
            shipping_address = f"{shipping_address}\nPhone: {phone}"
        
        payment_method = request.data.get('payment_method', 'upi')
        coupon_code = request.data.get('coupon_code', '')
        
        # Calculate subtotal and GST
        subtotal = Decimal(0)
        total_gst = Decimal(0)
        
        for item in cart.items.all():
            price = item.product.wholesale_price * item.quantity
            gst = (price * item.product.gst_rate) / Decimal(100)
            subtotal += price
            total_gst += gst
            
        delivery_charge = Decimal(50) if subtotal < 1000 else Decimal(0)
        grand_total = subtotal + total_gst + delivery_charge
        
        # Apply Coupon
        coupon = None
        discount = Decimal(0)
        if coupon_code:
            try:
                from django.utils import timezone
                coupon = Coupon.objects.get(code=coupon_code, is_active=True, valid_from__lte=timezone.now().date(), valid_until__gte=timezone.now().date())
                discount = (grand_total * coupon.discount_percentage) / Decimal(100)
                if coupon.max_discount_amount and discount > coupon.max_discount_amount:
                    discount = coupon.max_discount_amount
                grand_total -= discount
            except Coupon.DoesNotExist:
                return Response({'error': 'Invalid or expired coupon'}, status=status.HTTP_400_BAD_REQUEST)

        # Auto-complete payment for online modes, or use credit account
        if payment_method in ['upi', 'card', 'netbanking']:
            payment_status = 'completed'
        elif payment_method == 'credit_account':
            profile = request.user.profile
            available_credit = profile.credit_limit - profile.outstanding_balance
            if grand_total > available_credit:
                return Response({'error': f'Insufficient credit balance. Available: {available_credit}'}, status=status.HTTP_400_BAD_REQUEST)
            profile.outstanding_balance += grand_total
            profile.save()
            payment_status = 'completed'
        else:
            payment_status = 'pending'
        
        order_status = 'draft' if payment_method == 'draft' else 'pending'
        
        order = Order.objects.create(
            user=request.user,
            order_number=str(uuid.uuid4().hex[:10]).upper(),
            total_amount=grand_total,
            delivery_charge=delivery_charge,
            coupon=coupon,
            shipping_address=shipping_address,
            status=order_status
        )
        
        Payment.objects.create(
            order=order,
            amount=grand_total,
            amount_paid=grand_total if payment_status == 'completed' else Decimal('0.00'),
            method=payment_method,
            status=payment_status,
            transaction_id=str(uuid.uuid4().hex) if payment_status == 'completed' else None
        )
        
        for item in cart.items.all():
            price = item.product.wholesale_price
            gst = (price * item.product.gst_rate) / Decimal(100)
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=price,
                gst_amount=gst * item.quantity
            )
            
        cart.items.all().delete()
        
        from .serializers import OrderSerializer
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

from rest_framework.decorators import action

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Order.objects.all().order_by('-created_at')
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status in valid_statuses:
            order.status = new_status
            order.save()
            return Response({'status': new_status})
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_payment_status(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        payment_amount = request.data.get('payment_amount')
        
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={'amount': order.total_amount, 'method': 'bank_transfer', 'status': 'pending'}
        )
        
        if payment_amount is not None:
            try:
                amt = Decimal(str(payment_amount))
                payment.amount_paid += amt
                if payment.amount_paid >= payment.amount:
                    payment.status = 'completed'
                    payment.amount_paid = payment.amount
                else:
                    payment.status = 'pending'
                payment.save()
                return Response({
                    'status': payment.status, 
                    'amount_paid': float(payment.amount_paid), 
                    'amount_remaining': float(payment.amount - payment.amount_paid)
                })
            except Exception as e:
                return Response({'error': 'Invalid payment amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Fallback: complete entire payment
        new_status = request.data.get('status', 'completed')
        if new_status == 'completed':
            payment.status = 'completed'
            payment.amount_paid = payment.amount
        else:
            payment.status = 'pending'
            payment.amount_paid = Decimal('0.00')
        payment.save()
        return Response({
            'status': payment.status, 
            'amount_paid': float(payment.amount_paid), 
            'amount_remaining': float(payment.amount - payment.amount_paid)
        })

    @action(detail=True, methods=['post'])
    def cancel_order(self, request, pk=None):
        order = self.get_object()
        if order.user != request.user and request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        if order.status in ['delivered', 'cancelled']:
            return Response({'error': f'Cannot cancel order in status: {order.status}'}, status=status.HTTP_400_BAD_REQUEST)
            
        order.status = 'cancelled'
        order.save()
        
        try:
            if order.payment.method == 'credit_account':
                profile = order.user.profile
                profile.outstanding_balance = max(Decimal('0.00'), profile.outstanding_balance - order.total_amount)
                profile.save()
                order.payment.status = 'refunded'
                order.payment.save()
        except Exception:
            pass
            
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'], url_path='finalize-draft')
    def finalize_draft(self, request, pk=None):
        order = self.get_object()
        if order.status != 'draft':
            return Response({'error': 'Order is not in draft status'}, status=status.HTTP_400_BAD_REQUEST)
            
        payment_method = request.data.get('payment_method', 'upi')
        
        if payment_method == 'credit_account':
            profile = request.user.profile
            available_credit = profile.credit_limit - profile.outstanding_balance
            if order.total_amount > available_credit:
                return Response({'error': f'Insufficient credit balance. Available: {available_credit}'}, status=status.HTTP_400_BAD_REQUEST)
            profile.outstanding_balance += order.total_amount
            profile.save()
            
            payment = order.payment
            payment.status = 'completed'
            payment.amount_paid = order.total_amount
            payment.method = payment_method
            payment.save()
        elif payment_method in ['upi', 'card', 'netbanking']:
            payment = order.payment
            payment.status = 'completed'
            payment.amount_paid = order.total_amount
            payment.method = payment_method
            payment.save()
        else:
            payment = order.payment
            payment.status = 'pending'
            payment.amount_paid = Decimal('0.00')
            payment.method = payment_method
            payment.save()
            
        order.status = 'pending'
        order.save()
        return Response({'message': 'Draft order finalized successfully.'})

    @action(detail=True, methods=['post'])
    def request_return(self, request, pk=None):
        order = self.get_object()
        product_id = request.data.get('product_id')
        qty = int(request.data.get('quantity', 1))
        reason = request.data.get('reason', '')
        return_type = request.data.get('return_type', 'other')
        
        # Verify product exists in order items
        order_item = order.items.filter(product_id=product_id).first()
        if not order_item:
            return Response({'error': 'Product not found in this order'}, status=status.HTTP_400_BAD_REQUEST)
        
        if qty <= 0 or qty > order_item.quantity:
            return Response({'error': 'Invalid return quantity'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract batch number from request or serialize order_item
        batch_number = request.data.get('batch_number')
        if not batch_number:
            from .serializers import OrderItemSerializer
            batch_number = OrderItemSerializer(order_item).data.get('batch_number', 'N/A')
            
        # Create Return record
        ret = Return.objects.create(
            order=order,
            product_id=product_id,
            batch_number=batch_number,
            quantity=qty,
            reason=reason,
            return_type=return_type,
            status='pending'
        )
        from .serializers import ReturnSerializer
        return Response(ReturnSerializer(ret).data, status=status.HTTP_201_CREATED)

class ReturnViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ReturnSerializer

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Return.objects.all().order_by('-created_at')
        return Return.objects.filter(order__user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        ret = self.get_object()
        if ret.order.user != request.user:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        if ret.status != 'pending':
            return Response({'error': 'Only pending returns can be cancelled'}, status=status.HTTP_400_BAD_REQUEST)
        
        ret.status = 'cancelled'
        ret.save()
        return Response({'status': 'cancelled'})

class QuickBillingView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        items_data = request.data.get('items', [])
        if not items_data:
            return Response({'error': 'No items provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        customer_name = request.data.get('customer_name', 'Walk-in Customer')
        
        # Calculate total
        total_amount = 0
        valid_items = []
        for item in items_data:
            try:
                product = Product.objects.get(id=item['product_id'])
                qty = int(item['quantity'])
                price = product.wholesale_price
                total_amount += (price * qty)
                valid_items.append({
                    'product': product,
                    'quantity': qty,
                    'price': price
                })
            except Product.DoesNotExist:
                pass

        order = Order.objects.create(
            user=request.user,
            order_number=str(uuid.uuid4().hex[:10]).upper(),
            total_amount=total_amount,
            shipping_address=customer_name,
            status='delivered'  # Instantly delivered for quick billing
        )
        
        for v_item in valid_items:
            OrderItem.objects.create(
                order=order,
                product=v_item['product'],
                quantity=v_item['quantity'],
                price=v_item['price']
            )
            # Find batches and deduct stock
            qty_to_deduct = v_item['quantity']
            batches = v_item['product'].batches.filter(stock_quantity__gt=0).order_by('expiry_date')
            for batch in batches:
                if qty_to_deduct <= 0: break
                if batch.stock_quantity >= qty_to_deduct:
                    batch.stock_quantity -= qty_to_deduct
                    batch.save()
                    qty_to_deduct = 0
                else:
                    qty_to_deduct -= batch.stock_quantity
                    batch.stock_quantity = 0
                    batch.save()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

class BulkOrderUploadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file.name.endswith('.csv'):
            return Response({'error': 'Please upload a valid CSV file'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            cart, _ = Cart.objects.get_or_create(user=request.user)
            added_items = 0
            errors = []
            
            for row in reader:
                sku = row.get('SKU') or row.get('Product_ID')
                qty = int(row.get('Quantity', 0))
                
                if sku and qty > 0:
                    try:
                        product = Product.objects.get(id=sku) # Assuming ID is SKU for now
                        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
                        if not created:
                            item.quantity += qty
                        else:
                            item.quantity = qty
                        item.save()
                        added_items += 1
                    except Product.DoesNotExist:
                        errors.append(f"Product ID/SKU {sku} not found.")
                else:
                    errors.append(f"Invalid row data: {row}")
                    
            return Response({
                'message': f'Successfully added {added_items} products to cart.',
                'errors': errors
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PowerBIReportView(views.APIView):
    permission_classes = [IsAuthenticated] # Require admin/reporting role in prod

    def get(self, request):
        from django.db.models import Sum, Count
        import datetime
        from django.utils import timezone
        
        # Monthly Sales
        thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
        recent_orders = Order.objects.filter(created_at__gte=thirty_days_ago)
        
        from orders.models import Payment
        revenue = Payment.objects.filter(order__in=recent_orders).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        total_orders = recent_orders.count()
        
        from accounts.models import User
        active_dealers = User.objects.filter(role='dealer', profile__approval_status='approved').count()
        
        from inventory.models import Product
        total_products = Product.objects.filter(is_active=True).count()
        draft_products = Product.objects.filter(is_active=False).count()
        
        # Calculate pending amount
        from django.db.models import F
        from orders.models import Payment
        pending_amount = Payment.objects.filter(status='pending').aggregate(
            total_pending=Sum(F('amount') - F('amount_paid'))
        )['total_pending'] or 0

        # Best selling products
        top_products = OrderItem.objects.filter(order__in=recent_orders).values('product__name').annotate(total_qty=Sum('quantity')).order_by('-total_qty')[:5]
        
        return Response({
            'timestamp': timezone.now(),
            'metrics': {
                'last_30_days_revenue': revenue,
                'last_30_days_orders': total_orders,
                'active_dealers': active_dealers,
                'total_products': total_products,
                'draft_products': draft_products,
                'pending_amount': pending_amount,
            },
            'top_products': list(top_products)
        })

class AdminReturnsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        cancelled_orders = Order.objects.filter(status='cancelled').order_by('-created_at')
        damaged_returns = Return.objects.filter(return_type__in=['damaged', 'other']).order_by('-created_at')
        expired_returns = Return.objects.filter(return_type='expired').order_by('-created_at')
        
        return Response({
            'cancelled_orders': OrderSerializer(cancelled_orders, many=True).data,
            'damaged_returns': ReturnSerializer(damaged_returns, many=True).data,
            'expired_returns': ReturnSerializer(expired_returns, many=True).data
        })

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        return_id = request.data.get('return_id')
        new_status = request.data.get('status')
        valid_statuses = ['pending', 'approved', 'rejected', 'refunded']
        
        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            ret = Return.objects.get(pk=return_id)
            ret.status = new_status
            if new_status == 'refunded':
                ret.refund_method = request.data.get('refund_method', 'cash')
            ret.save()
            return Response({'message': 'Return status updated successfully', 'status': new_status})
        except Return.DoesNotExist:
            return Response({'error': 'Return record not found'}, status=status.HTTP_404_NOT_FOUND)

class InvoicePDFView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            if request.user.role == 'admin':
                order = Order.objects.get(pk=pk)
            else:
                order = Order.objects.get(pk=pk, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

        from django.http import HttpResponse
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{order.order_number}.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            name='TitleStyle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor("#0A58CA"),
            spaceAfter=5
        )
        subtitle_style = ParagraphStyle(
            name='SubtitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
            spaceAfter=20
        )
        info_style = ParagraphStyle(
            name='InfoStyle',
            parent=styles['Normal'],
            fontSize=11,
            leading=14
        )

        # Header
        elements.append(Paragraph("<b>ABIN PHARMA</b>", title_style))
        elements.append(Paragraph("Premium B2B Pharmaceutical Distribution<br/>123 Health Ave, Medical City<br/>Phone: +1 234 567 8900 | Email: support@abinpharma.com", subtitle_style))
        elements.append(Spacer(1, 10))

        # Invoice Info Table
        customer_name = f"{order.user.first_name} {order.user.last_name}".strip() or "Walk-in Customer"
        shipping = order.shipping_address if order.shipping_address != 'Walk-in Customer' else 'N/A'
        
        info_data = [
            [Paragraph(f"<b>Invoice To:</b><br/>{customer_name}<br/>{shipping}", info_style), 
             Paragraph(f"<b>Invoice No:</b> {order.order_number}<br/><b>Date:</b> {order.created_at.strftime('%d %B %Y')}<br/><b>Status:</b> {order.status.upper()}", info_style)]
        ]
        info_table = Table(info_data, colWidths=['60%', '40%'])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 10))

        # Items Table
        table_data = [['#', 'Product Description', 'Qty', 'Unit Price (₹)', 'Total (₹)']]
        
        for idx, item in enumerate(order.items.all(), 1):
            table_data.append([
                str(idx),
                item.product.name[:40],
                str(item.quantity),
                f"{item.price:,.2f}",
                f"{item.quantity * item.price:,.2f}"
            ])
            
        table_data.append(['', '', '', 'Subtotal:', f"{order.total_amount - order.delivery_charge:,.2f}"])
        if order.delivery_charge > 0:
            table_data.append(['', '', '', 'Delivery Charge:', f"{order.delivery_charge:,.2f}"])
        table_data.append(['', '', '', 'Grand Total:', f"₹ {order.total_amount:,.2f}"])

        # Table Styling
        t = Table(table_data, colWidths=['5%', '50%', '10%', '15%', '20%'])
        t.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0A58CA")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Data rows
            ('ALIGN', (0, 1), (0, -1), 'CENTER'), # Index
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),   # Product Name
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'), # Qty, Price, Total
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -4), 0.5, colors.lightgrey),
            
            # Totals rows
            ('ALIGN', (3, -3), (3, -1), 'RIGHT'),
            ('FONTNAME', (3, -3), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (3, -1), (-1, -1), colors.HexColor("#198754")), # Green Grand Total
            ('LINEABOVE', (3, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
        
        center_style = ParagraphStyle(
            name='CenterStyle',
            parent=styles['Normal'],
            alignment=1, # TA_CENTER
            fontSize=10,
        )
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("<b>Thank you for your business!</b><br/><font color='gray'>If you have any questions about this invoice, please contact support@abinpharma.com</font>", center_style))
        
        doc.build(elements)
        return response

class ExportOrdersExcelView(views.APIView):
    permission_classes = [IsAuthenticated] # Require admin/reporting role in prod

    def get(self, request):
        import pandas as pd
        from django.http import HttpResponse
        import io
        
        orders = Order.objects.all().values(
            'order_number', 'user__username', 'status', 'total_amount', 'delivery_charge', 'created_at', 'shipping_address', 'tracking_number'
        )
        
        df = pd.DataFrame(list(orders))
        
        if df.empty:
            return Response({'error': 'No orders to export'}, status=404)
            
        # Clean up timestamps
        df['created_at'] = df['created_at'].dt.tz_localize(None)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Orders', index=False)
            
        output.seek(0)
        
        response = HttpResponse(
            output.read(), 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="AbinPharma_Orders.xlsx"'
        return response
