from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Invoice, Return
from inventory.serializers import ProductSerializer

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'created_at']
        read_only_fields = ['user']

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    batch_number = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'batch_number', 'quantity', 'price', 'gst_amount']

    def get_batch_number(self, obj):
        if obj.batch_number:
            return obj.batch_number
        if obj.product:
            first_batch = obj.product.batches.filter(stock_quantity__gt=0).order_by('expiry_date').first()
            if first_batch:
                return first_batch.batch_number
            any_batch = obj.product.batches.first()
            if any_batch:
                return any_batch.batch_number
        return 'N/A'

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment_status = serializers.SerializerMethodField(read_only=True)
    payment_method = serializers.SerializerMethodField(read_only=True)
    payment_amount_paid = serializers.SerializerMethodField(read_only=True)
    payment_amount_remaining = serializers.SerializerMethodField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    customer_phone = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'total_amount', 'shipping_address', 'created_at', 
            'items', 'prescription_file', 'payment_status', 'payment_method', 
            'payment_amount_paid', 'payment_amount_remaining', 'customer_name', 'customer_phone'
        ]
        read_only_fields = ['order_number', 'status', 'total_amount', 'user']

    def get_customer_name(self, obj):
        if obj.user:
            name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            return name or obj.user.username
        return "Walk-in Customer"

    def get_customer_phone(self, obj):
        if obj.user:
            return obj.user.phone_number or "N/A"
        return "N/A"

    def get_payment_status(self, obj):
        try:
            return obj.payment.status
        except Exception:
            return 'pending'

    def get_payment_method(self, obj):
        try:
            return obj.payment.method
        except Exception:
            return 'bank_transfer'

    def get_payment_amount_paid(self, obj):
        try:
            return float(obj.payment.amount_paid)
        except Exception:
            return 0.0

    def get_payment_amount_remaining(self, obj):
        try:
            return float(obj.payment.amount - obj.payment.amount_paid)
        except Exception:
            try:
                return float(obj.total_amount)
            except Exception:
                return 0.0

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'

class ReturnSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    customer_name = serializers.CharField(source='order.user.username', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    batch_number = serializers.SerializerMethodField(read_only=True)
    payment_status = serializers.SerializerMethodField(read_only=True)
    payment_method = serializers.SerializerMethodField(read_only=True)
    refund_amount = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Return
        fields = ['id', 'order', 'order_number', 'customer_name', 'product', 'product_name', 'batch_number', 'quantity', 'reason', 'return_type', 'status', 'payment_status', 'payment_method', 'refund_amount', 'refund_method', 'created_at']

    def get_batch_number(self, obj):
        if obj.batch_number:
            return obj.batch_number
        if obj.order and obj.product:
            order_item = obj.order.items.filter(product=obj.product).first()
            if order_item and order_item.batch_number:
                return order_item.batch_number
            first_batch = obj.product.batches.filter(stock_quantity__gt=0).order_by('expiry_date').first()
            if first_batch:
                return first_batch.batch_number
            any_batch = obj.product.batches.first()
            if any_batch:
                return any_batch.batch_number
        return 'N/A'

    def get_payment_status(self, obj):
        try:
            return obj.order.payment.status
        except Exception:
            return 'pending'

    def get_payment_method(self, obj):
        try:
            return obj.order.payment.method
        except Exception:
            return 'N/A'

    def get_refund_amount(self, obj):
        from decimal import Decimal
        try:
            order_item = obj.order.items.filter(product=obj.product).first()
            if order_item:
                unit_price = order_item.price
                unit_gst = order_item.gst_amount / order_item.quantity if order_item.quantity > 0 else Decimal('0.00')
                total_unit_cost = unit_price + unit_gst
                return float(obj.quantity * total_unit_cost)
        except Exception:
            pass
        try:
            return float(obj.quantity * obj.product.wholesale_price)
        except Exception:
            return 0.0
