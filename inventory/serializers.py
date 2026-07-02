from rest_framework import serializers
from .models import (
    Category,
    Manufacturer,
    Brand,
    Product,
    Batch,
    PurchaseBill,
    PurchaseItem,
    Supplier,
    GoodsReceivedNote,
)

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class GoodsReceivedNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceivedNote
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), source='brand', write_only=True, required=False, allow_null=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category', write_only=True, required=False, allow_null=True)
    manufacturer_id = serializers.PrimaryKeyRelatedField(queryset=Manufacturer.objects.all(), source='manufacturer', write_only=True, required=False, allow_null=True)
    total_stock = serializers.SerializerMethodField(read_only=True)
    batches = BatchSerializer(many=True, read_only=True)

    # Write-only fields for quick initial batch setup
    batch_number = serializers.CharField(write_only=True, required=False, allow_null=True)
    expiry_date = serializers.DateField(write_only=True, required=False, allow_null=True)
    stock_quantity = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Product
        fields = '__all__'
        
    def get_total_stock(self, obj):
        from django.db.models import Sum
        return obj.batches.aggregate(total=Sum('stock_quantity'))['total'] or 0

    def create(self, validated_data):
        batch_number = validated_data.pop('batch_number', None)
        expiry_date = validated_data.pop('expiry_date', None)
        stock_quantity = validated_data.pop('stock_quantity', None)
        
        product = Product.objects.create(**validated_data)
        
        if batch_number and expiry_date:
            qty = stock_quantity if stock_quantity is not None else 0
            if qty > 20:
                product.stock_status = 'in_stock'
            elif qty > 0:
                product.stock_status = 'low_stock'
            else:
                product.stock_status = 'out_of_stock'
            product.save()
            
            Batch.objects.create(
                product=product,
                batch_number=batch_number,
                expiry_date=expiry_date,
                stock_quantity=qty
            )
            
        return product


class PurchaseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = ['product', 'batch_number', 'expiry_date', 'quantity', 'purchase_price']

class PurchaseBillSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default='Unknown')
    payment_status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PurchaseBill
        fields = ['id', 'supplier', 'supplier_name', 'bill_number', 'date', 'total_amount', 'items', 'payment_status']

    def get_payment_status(self, obj):
        total_paid = sum(p.amount_paid for p in obj.payments.all())
        if total_paid >= obj.total_amount:
            return 'completed'
        return 'pending'

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        bill = PurchaseBill.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseItem.objects.create(bill=bill, **item_data)
            # Update/Create Batch Stock
            batch, created = Batch.objects.get_or_create(
                product=item_data['product'],
                batch_number=item_data['batch_number'],
                defaults={'expiry_date': item_data['expiry_date'], 'stock_quantity': 0}
            )
            batch.stock_quantity += item_data['quantity']
            batch.save()
        return bill
