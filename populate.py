import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()

from accounts.models import User, Profile
from inventory.models import Category, Manufacturer, Brand, Product

def populate():
    # Create Admin
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser('admin', 'admin@abinpharma.com', 'admin123')
        admin.role = 'admin'
        admin.save()
        Profile.objects.create(user=admin)
        print("Admin user created (admin / admin123)")

    # Create Categories
    cat1, _ = Category.objects.get_or_create(name='Prescription')
    cat2, _ = Category.objects.get_or_create(name='OTC Medicines')
    cat3, _ = Category.objects.get_or_create(name='Supplements')

    # Create Manufacturer & Brand
    man1, _ = Manufacturer.objects.get_or_create(name='PharmaCorp Inc')
    brand1, _ = Brand.objects.get_or_create(name='HealthPlus', manufacturer=man1)

    # Create Products
    if not Product.objects.exists():
        Product.objects.create(
            name='Paracetamol 500mg', generic_name='Paracetamol', brand=brand1, category=cat2,
            mrp=50.00, wholesale_price=35.00, min_order_quantity=100
        )
        Product.objects.create(
            name='Amoxicillin 250mg', generic_name='Amoxicillin', brand=brand1, category=cat1,
            mrp=120.00, wholesale_price=85.00, min_order_quantity=50
        )
        Product.objects.create(
            name='Vitamin C Zinc Tablets', generic_name='Ascorbic Acid + Zinc', brand=brand1, category=cat3,
            mrp=150.00, wholesale_price=90.00, min_order_quantity=20
        )
        print("Mock products populated.")

if __name__ == '__main__':
    populate()
