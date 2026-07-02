import os
import django
import requests
import random
from django.core.files.base import ContentFile
import datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()

from inventory.models import Category, Manufacturer, Brand, Product, Batch

# Real Indian Market Medicines
REAL_MEDICINES = [
    {
        "name": "Dolo 650 Tablet",
        "generic": "Paracetamol 650mg",
        "brand": "Micro Labs",
        "category": "Analgesics",
        "pack_size": "15 Tablets",
        "mrp": 30.91,
        "search": "Dolo 650 Tablet strip"
    },
    {
        "name": "Augmentin 625 Duo Tablet",
        "generic": "Amoxicillin 500mg + Clavulanic Acid 125mg",
        "brand": "GSK",
        "category": "Antibiotics",
        "pack_size": "10 Tablets",
        "mrp": 201.71,
        "search": "Augmentin 625 Duo Tablet strip"
    },
    {
        "name": "Pan-D Capsule",
        "generic": "Pantoprazole 40mg + Domperidone 30mg",
        "brand": "Alkem",
        "category": "Antacids",
        "pack_size": "15 Capsules",
        "mrp": 199.00,
        "search": "Pan-D Capsule strip"
    },
    {
        "name": "Allegra 120mg Tablet",
        "generic": "Fexofenadine 120mg",
        "brand": "Sanofi",
        "category": "Antiallergic",
        "pack_size": "10 Tablets",
        "mrp": 203.46,
        "search": "Allegra 120mg Tablet box"
    },
    {
        "name": "Calpol 500mg Tablet",
        "generic": "Paracetamol 500mg",
        "brand": "GSK",
        "category": "Analgesics",
        "pack_size": "15 Tablets",
        "mrp": 14.73,
        "search": "Calpol 500mg Tablet"
    },
    {
        "name": "Azithral 500 Tablet",
        "generic": "Azithromycin 500mg",
        "brand": "Alembic",
        "category": "Antibiotics",
        "pack_size": "5 Tablets",
        "mrp": 119.50,
        "search": "Azithral 500 Tablet"
    },
    {
        "name": "Zincovit Tablet",
        "generic": "Multivitamins and Minerals",
        "brand": "Apex Labs",
        "category": "Supplements",
        "pack_size": "15 Tablets",
        "mrp": 105.00,
        "search": "Zincovit Tablet strip"
    },
    {
        "name": "Shelcal 500 Tablet",
        "generic": "Calcium 500mg + Vitamin D3 250 IU",
        "brand": "Torrent Pharma",
        "category": "Supplements",
        "pack_size": "15 Tablets",
        "mrp": 119.50,
        "search": "Shelcal 500 Tablet strip"
    },
    {
        "name": "Ecosprin 75 Tablet",
        "generic": "Aspirin 75mg",
        "brand": "USV",
        "category": "Cardiac",
        "pack_size": "14 Tablets",
        "mrp": 4.93,
        "search": "Ecosprin 75 Tablet strip"
    },
    {
        "name": "Glycomet-GP 1 Tablet PR",
        "generic": "Glimepiride 1mg + Metformin 500mg",
        "brand": "USV",
        "category": "Anti-Diabetic",
        "pack_size": "15 Tablets",
        "mrp": 134.00,
        "search": "Glycomet-GP 1 Tablet strip"
    },
    {
        "name": "Telmikind 40 Tablet",
        "generic": "Telmisartan 40mg",
        "brand": "Mankind",
        "category": "Cardiac",
        "pack_size": "10 Tablets",
        "mrp": 55.40,
        "search": "Telmikind 40 Tablet strip"
    },
    {
        "name": "Thyronorm 50mcg Tablet",
        "generic": "Thyroxine 50mcg",
        "brand": "Abbott",
        "category": "Thyroid",
        "pack_size": "120 Tablets",
        "mrp": 169.00,
        "search": "Thyronorm 50mcg bottle"
    },
    {
        "name": "Betadine 2% Ointment",
        "generic": "Povidone Iodine 2%",
        "brand": "Win-Medicare",
        "category": "Antiseptics",
        "pack_size": "15g Tube",
        "mrp": 105.00,
        "search": "Betadine Ointment 15g"
    },
    {
        "name": "Benadryl Cough Formula",
        "generic": "Diphenhydramine + Ammonium Chloride",
        "brand": "J&J",
        "category": "Syrups",
        "pack_size": "150ml Bottle",
        "mrp": 118.00,
        "search": "Benadryl Cough Formula 150ml"
    },
    {
        "name": "Volini Gel",
        "generic": "Diclofenac Diethylamine",
        "brand": "Sun Pharma",
        "category": "Ointments",
        "pack_size": "30g Tube",
        "mrp": 110.00,
        "search": "Volini Gel 30g"
    },
    {
        "name": "Gelusil MPS Liquid",
        "generic": "Aluminium Hydroxide + Magnesium",
        "brand": "Pfizer",
        "category": "Antacids",
        "pack_size": "200ml Bottle",
        "mrp": 124.00,
        "search": "Gelusil MPS Liquid 200ml bottle"
    },
    {
        "name": "Becosules Z Capsule",
        "generic": "B-Complex + Vitamin C + Zinc",
        "brand": "Pfizer",
        "category": "Supplements",
        "pack_size": "20 Capsules",
        "mrp": 45.00,
        "search": "Becosules Z Capsule strip"
    },
    {
        "name": "Combiflam Tablet",
        "generic": "Ibuprofen 400mg + Paracetamol 325mg",
        "brand": "Sanofi",
        "category": "Analgesics",
        "pack_size": "20 Tablets",
        "mrp": 42.00,
        "search": "Combiflam Tablet strip"
    },
    {
        "name": "Montek LC Tablet",
        "generic": "Montelukast 10mg + Levocetirizine 5mg",
        "brand": "Sun Pharma",
        "category": "Antiallergic",
        "pack_size": "15 Tablets",
        "mrp": 194.00,
        "search": "Montek LC Tablet strip"
    },
    {
        "name": "Ascoril LS Syrup",
        "generic": "Ambroxol + Levosalbutamol + Guaifenesin",
        "brand": "Glenmark",
        "category": "Syrups",
        "pack_size": "100ml Bottle",
        "mrp": 118.00,
        "search": "Ascoril LS Syrup 100ml"
    }
]

def run():
    print("Clearing old fictional products...")
    Product.objects.all().delete()
    
    print("Seeding REAL Market Medicines...")
    
    for item in REAL_MEDICINES:
        try:
            # Create Category, Brand, Manufacturer
            cat, _ = Category.objects.get_or_create(name=item['category'])
            man, _ = Manufacturer.objects.get_or_create(name=item['brand'])
            brand, _ = Brand.objects.get_or_create(name=item['brand'], defaults={'manufacturer': man})
            
            wp = round(item['mrp'] * 0.75, 2)
            
            # Create Product
            product = Product.objects.create(
                name=item['name'],
                generic_name=item['generic'],
                category=cat,
                manufacturer=man,
                brand=brand,
                mrp=item['mrp'],
                wholesale_price=wp,
                pack_size=item['pack_size'],
                gst_rate=12.0,
                min_order_quantity=10,
                barcode=str(random.randint(100000000000, 999999999999)),
                is_active=True,
                stock_status='in_stock'
            )
            
            # Add Batch
            Batch.objects.create(
                product=product,
                batch_number=f"BN-{random.randint(1000, 9999)}",
                manufacturing_date=timezone.now().date() - datetime.timedelta(days=random.randint(30, 200)),
                expiry_date=timezone.now().date() + datetime.timedelta(days=random.randint(300, 800)),
                stock_quantity=random.randint(100, 1000)
            )
            
            # Fetch Real Image from Bing
            query = item['search'].replace(' ', '+')
            url = f"https://tse1.mm.bing.net/th?q={query}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            if resp.status_code == 200:
                product.image.save(f"market_{product.id}.jpg", ContentFile(resp.content), save=True)
                print(f"Added: {product.name}")
            else:
                print(f"Failed image for: {product.name}")
                
        except Exception as e:
            print(f"Error processing {item['name']}: {e}")

    print("Successfully seeded REAL market medicines!")

if __name__ == '__main__':
    run()
