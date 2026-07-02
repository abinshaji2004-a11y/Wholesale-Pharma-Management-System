import os
import requests
import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from inventory.models import Category, Manufacturer, Brand, Product, Batch, Warehouse

class Command(BaseCommand):
    help = 'Seeds the database with 100 realistic Indian pharmaceutical products'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting to seed database...")

        # 1. Categories
        categories = [
            'Analgesics', 'Antibiotics', 'Antacids', 'Antipyretics', 'Antihistamines',
            'Vitamins & Supplements', 'Cardiovascular', 'Anti-diabetics', 'Dermatology'
        ]
        cat_objs = {}
        for c in categories:
            obj, _ = Category.objects.get_or_create(name=c, defaults={'description': f'{c} products'})
            cat_objs[c] = obj

        # 2. Manufacturers
        manufacturers = [
            'Sun Pharma', 'Cipla', "Dr. Reddy's", 'Abbott', 'Mankind', 
            'Lupin', 'Alkem', 'Torrent', 'Zydus', 'Glenmark', 'Micro Labs', 'Intas'
        ]
        mfg_objs = {}
        for m in manufacturers:
            obj, _ = Manufacturer.objects.get_or_create(name=m)
            mfg_objs[m] = obj

        # 3. Base Medicines List (Names, Generic, Category, Base Price)
        base_medicines = [
            ("Dolo 650", "Paracetamol 650mg", "Antipyretics", 30.0, "Micro Labs"),
            ("Crocin 650", "Paracetamol 650mg", "Antipyretics", 25.0, "Cipla"),
            ("Augmentin 625", "Amoxicillin 500mg + Clavulanic Acid 125mg", "Antibiotics", 200.0, "Sun Pharma"),
            ("Azithral 500", "Azithromycin 500mg", "Antibiotics", 110.0, "Alkem"),
            ("Pan 40", "Pantoprazole 40mg", "Antacids", 140.0, "Alkem"),
            ("Pan D", "Pantoprazole 40mg + Domperidone 30mg", "Antacids", 190.0, "Alkem"),
            ("Shelcal 500", "Calcium 500mg + Vitamin D3", "Vitamins & Supplements", 120.0, "Torrent"),
            ("Limcee", "Vitamin C 500mg", "Vitamins & Supplements", 25.0, "Abbott"),
            ("Becosules", "Vitamin B Complex", "Vitamins & Supplements", 45.0, "Cipla"),
            ("Allegra 120", "Fexofenadine 120mg", "Antihistamines", 210.0, "Sun Pharma"),
            ("Okacet", "Cetirizine 10mg", "Antihistamines", 20.0, "Cipla"),
            ("Thyrox 50", "Thyroxine Sodium 50mcg", "Cardiovascular", 150.0, "Mankind"),
            ("Amlokind 5", "Amlodipine 5mg", "Cardiovascular", 35.0, "Mankind"),
            ("Telmikind 40", "Telmisartan 40mg", "Cardiovascular", 60.0, "Mankind"),
            ("Glycomet 500", "Metformin 500mg", "Anti-diabetics", 65.0, "Cipla"),
            ("Glycomet Trio", "Metformin + Glimepiride + Voglibose", "Anti-diabetics", 140.0, "Cipla"),
            ("Volini Gel", "Diclofenac Diethylamine", "Analgesics", 110.0, "Sun Pharma"),
            ("Soframycin", "Framycetin Skin Cream", "Dermatology", 55.0, "Zydus"),
            ("Candid Dusting", "Clotrimazole Powder", "Dermatology", 145.0, "Glenmark"),
            ("Aciloc 150", "Ranitidine 150mg", "Antacids", 38.0, "Zydus"),
            ("Betadine 10%", "Povidone Iodine", "Dermatology", 120.0, "Cipla"),
            ("Combiflam", "Ibuprofen + Paracetamol", "Analgesics", 42.0, "Cipla"),
            ("Ecosprin 75", "Aspirin 75mg", "Cardiovascular", 15.0, "Cipla"),
            ("Omez 20", "Omeprazole 20mg", "Antacids", 55.0, "Dr. Reddy's"),
            ("Zincovit", "Multivitamin & Multimineral", "Vitamins & Supplements", 105.0, "Cipla")
        ]

        # Generate exactly 100 items by adding variations (e.g. Tablets, Syrup, Injection, Drop)
        variations = ["Tablet", "Capsule", "Syrup", "Injection", "Drops"]
        products_data = []
        count = 1
        
        while len(products_data) < 100:
            for base in base_medicines:
                if len(products_data) >= 100:
                    break
                
                var = random.choice(variations)
                name = f"{base[0]} {var}"
                if var in ["Syrup", "Drops"]:
                    pack = "100ml Bottle"
                elif var == "Injection":
                    pack = "1 Vial"
                else:
                    pack = "10x10 Strip"
                
                # Jiggle price
                mrp = round(base[3] * random.uniform(0.8, 1.5), 2)
                ws = round(mrp * 0.7, 2)
                
                products_data.append({
                    'name': name,
                    'generic_name': base[1],
                    'category': base[2],
                    'mrp': mrp,
                    'wholesale_price': ws,
                    'manufacturer': base[4],
                    'pack_size': pack,
                    'barcode': f"8901030{str(count).zfill(5)}"
                })
                count += 1

        warehouse, _ = Warehouse.objects.get_or_create(name='Main Warehouse')

        # Create Products
        new_products = 0
        for data in products_data:
            cat = cat_objs[data['category']]
            mfg = mfg_objs[data['manufacturer']]
            
            # Create Brand based on product name (without variation)
            base_name = data['name'].rsplit(' ', 1)[0]
            brand, _ = Brand.objects.get_or_create(name=base_name, manufacturer=mfg)

            product, created = Product.objects.get_or_create(
                barcode=data['barcode'],
                defaults={
                    'name': data['name'],
                    'generic_name': data['generic_name'],
                    'brand': brand,
                    'category': cat,
                    'manufacturer': mfg,
                    'pack_size': data['pack_size'],
                    'mrp': data['mrp'],
                    'wholesale_price': data['wholesale_price'],
                    'gst_rate': 12.0,
                    'is_active': True,
                    'min_order_quantity': random.randint(1, 5),
                    'stock_status': 'in_stock'
                }
            )

            if created:
                new_products += 1
                
                # Fetch a placeholder image
                # Placehold.co gives quick reliable images.
                safe_name = data['name'].replace(' ', '+')
                image_url = f"https://placehold.co/400x400/0d6efd/ffffff.png?text={safe_name}"
                try:
                    resp = requests.get(image_url, timeout=5)
                    if resp.status_code == 200:
                        product.image.save(f"{data['barcode']}.png", ContentFile(resp.content), save=True)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Failed to download image for {product.name}: {e}"))

                # Create Batches
                stock_qty = random.randint(50, 500)
                expiry_days = random.randint(180, 1095)
                batch_number = f"BAT-{product.barcode}-{random.randint(10,99)}"
                
                Batch.objects.create(
                    product=product,
                    batch_number=batch_number,
                    warehouse=warehouse,
                    stock_quantity=stock_qty,
                    manufacturing_date=timezone.now().date() - timedelta(days=random.randint(30, 300)),
                    expiry_date=timezone.now().date() + timedelta(days=expiry_days),
                    location=f"Rack-{random.randint(1,20)}"
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {new_products} new products. Total: 100 (including previously seeded)."))
