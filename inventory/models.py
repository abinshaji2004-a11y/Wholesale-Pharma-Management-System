from django.db import models
from django.conf import settings

class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.TextField()
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    def __str__(self):
        return self.name

class Manufacturer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gst_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=200)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, related_name='brands')

    def __str__(self):
        return self.name

class Product(models.Model):
    STOCK_STATUS_CHOICES = (
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    )

    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255, blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    
    pack_size = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. 10x10 Tablets, 100ml Syrup")
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)
    
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=12.0)
    
    is_active = models.BooleanField(default=True)
    min_order_quantity = models.IntegerField(default=1)
    
    stock_status = models.CharField(max_length=20, choices=STOCK_STATUS_CHOICES, default='out_of_stock')
    
    storage_instructions = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if not self.image:
            self.generate_automatic_image()

    def generate_automatic_image(self):
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            from django.core.files.base import ContentFile
            
            h = hash(self.name)
            r = (h & 0xFF0000) >> 16
            g = (h & 0x00FF00) >> 8
            b = (h & 0x0000FF)
            
            bg_color = (240 + (r % 15), 242 + (g % 13), 245 + (b % 10))
            img = Image.new('RGB', (400, 300), color=bg_color)
            draw = ImageDraw.Draw(img)
            
            box_color = (40 + (r % 100), 80 + (g % 100), 120 + (b % 100))
            draw.rounded_rectangle([50, 40, 350, 240], radius=12, fill=box_color, outline=(255,255,255), width=3)
            draw.rectangle([50, 110, 350, 170], fill=(255, 255, 255))
            
            try:
                font_large = ImageFont.truetype("arial.ttf", 24)
                font_med = ImageFont.truetype("arial.ttf", 16)
                font_small = ImageFont.truetype("arial.ttf", 11)
            except IOError:
                font_large = ImageFont.load_default()
                font_med = ImageFont.load_default()
                font_small = ImageFont.load_default()
                
            draw.text((70, 60), self.name[:18].upper(), fill=(255, 255, 255), font=font_large)
            generic_text = self.generic_name or (self.category.name if self.category else "MEDICINE")
            draw.text((70, 130), generic_text[:25], fill=box_color, font=font_med)
            
            pack_text = self.pack_size or "Standard Packaging"
            draw.text((70, 190), pack_text, fill=(240, 240, 240), font=font_med)
            draw.text((70, 212), "B2B WHOLESALE • ABIN PHARMA", fill=(200, 200, 200), font=font_small)
            
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=95)
            output.seek(0)
            
            filename = f"product_{self.id}.jpg"
            self.image.save(filename, ContentFile(output.read()), save=False)
            super().save(update_fields=['image'])
        except Exception as e:
            print(f"Automatic image generation failed: {e}")

class Batch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=50)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches')
    stock_quantity = models.IntegerField(default=0)
    expiry_date = models.DateField()
    manufacturing_date = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True, help_text="Shelf/Rack location")

    def __str__(self):
        return f"{self.product.name} - {self.batch_number}"

class PurchaseBill(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    bill_number = models.CharField(max_length=100, unique=True)
    date = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Purchase {self.bill_number}"

class PurchaseItem(models.Model):
    bill = models.ForeignKey(PurchaseBill, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    batch_number = models.CharField(max_length=50)
    expiry_date = models.DateField()
    quantity = models.IntegerField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} (Batch: {self.batch_number})"

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.product.name} by {self.user.username}"

class SupplierPayment(models.Model):
    bill = models.ForeignKey(PurchaseBill, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    payment_mode = models.CharField(max_length=50, blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Payment {self.amount_paid} for {self.bill.bill_number}"

class GoodsReceivedNote(models.Model):
    purchase_bill = models.OneToOneField(PurchaseBill, on_delete=models.CASCADE, related_name='grn')
    grn_number = models.CharField(max_length=100, unique=True)
    received_date = models.DateField(auto_now_add=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"GRN {self.grn_number} for PO {self.purchase_bill.bill_number}"

class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
