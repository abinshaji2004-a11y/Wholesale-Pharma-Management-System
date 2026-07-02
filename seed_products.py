import os
import django
import random
import requests
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()

from inventory.models import Category, Manufacturer, Brand, Product, Batch
from faker import Faker
fake = Faker()

# Sample Data
categories = ['Analgesics', 'Antibiotics', 'Antiseptics', 'Vitamins', 'Syrups', 'Ointments']
manufacturers = ['Sun Pharma', 'Cipla', 'Dr. Reddy\'s', 'Lupin', 'Aurobindo']
brands = ['Crocin', 'Dolo', 'Azithral', 'Betadine', 'Zincovit', 'Benadryl', 'Volini']
medicine_names = ['Paracetamol', 'Amoxicillin', 'Ibuprofen', 'Cetirizine', 'Azithromycin', 'Omeprazole', 'Metformin', 'Amlodipine', 'Losartan', 'Atorvastatin']

def run():
    print("Clearing old products...")
    Product.objects.all().delete()
    
    print("Seeding Categories, Manufacturers, and Brands...")
    cat_objs = [Category.objects.get_or_create(name=c)[0] for c in categories]
    man_objs = [Manufacturer.objects.get_or_create(name=m)[0] for m in manufacturers]
    
    brand_objs = []
    for b in brands:
        man = random.choice(man_objs)
        brand, _ = Brand.objects.get_or_create(name=b, defaults={'manufacturer': man})
        brand_objs.append(brand)

    print("Generating 100 Products with Photos...")
    for i in range(1, 101):
        name = f"{random.choice(medicine_names)} {random.randint(100, 500)}mg"
        generic_name = name.split()[0]
        
        category = random.choice(cat_objs)
        manufacturer = random.choice(man_objs)
        brand = random.choice(brand_objs)
        
        mrp = round(random.uniform(20.0, 500.0), 2)
        wholesale_price = round(mrp * random.uniform(0.6, 0.8), 2)
        
        # Create product
        product = Product.objects.create(
            name=f"{name} - {i}",
            generic_name=generic_name,
            category=category,
            manufacturer=manufacturer,
            brand=brand,
            description=fake.text(max_nb_chars=200),
            mrp=mrp,
            wholesale_price=wholesale_price,
            pack_size=random.choice(['10 Tablets', '100ml Syrup', '50g Tube', '15 Capsules']),
            gst_rate=random.choice([5.0, 12.0, 18.0]),
            min_order_quantity=random.randint(10, 50),
            barcode=fake.ean13(),
            is_active=True
        )
        
        # Download dummy image
        try:
            image_url = f"https://placehold.co/400x400/0A58CA/FFF/png?text={name.replace(' ', '+')}"
            
            # Setting a user-agent to avoid generic blocks
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(image_url, headers=headers)
            if response.status_code == 200:
                product.image.save(f"product_{i}.png", ContentFile(response.content), save=True)
            else:
                print(f"Failed status {response.status_code} for product {i}")
        except Exception as e:
            print(f"Failed to save image for product {i}: {e}")

        # Add a batch with stock
        import datetime
        from django.utils import timezone
        
        Batch.objects.create(
            product=product,
            batch_number=f"BTH-{fake.random_int(min=1000, max=9999)}",
            manufacturing_date=timezone.now().date() - datetime.timedelta(days=random.randint(10, 300)),
            expiry_date=timezone.now().date() + datetime.timedelta(days=random.randint(30, 700)),
            stock_quantity=random.randint(50, 500)
        )
        
        if i % 10 == 0:
            print(f"Created {i} products...")
            
    print("Successfully seeded 100 products!")

if __name__ == '__main__':
    run()
