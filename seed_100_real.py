import os
import django
import requests
import random
import time
from django.core.files.base import ContentFile
import datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()

from inventory.models import Category, Manufacturer, Brand, Product, Batch

MEDICINES = [
    # Analgesics
    ("Dolo 650 Tablet", "Paracetamol 650mg", "Analgesics", "Micro Labs", 30.91),
    ("Calpol 500mg Tablet", "Paracetamol 500mg", "Analgesics", "GSK", 15.00),
    ("Combiflam Tablet", "Ibuprofen + Paracetamol", "Analgesics", "Sanofi", 42.50),
    ("Crocin Advance Tablet", "Paracetamol 500mg", "Analgesics", "GSK", 20.00),
    ("Zerodol-SP Tablet", "Aceclofenac + Paracetamol + Serratiopeptidase", "Analgesics", "Ipca", 115.00),
    ("Voveran SR 100 Tablet", "Diclofenac 100mg", "Analgesics", "Novartis", 130.00),
    ("Ultracet Tablet", "Tramadol + Paracetamol", "Analgesics", "Janssen", 215.00),
    ("Enzoflam Tablet", "Diclofenac + Paracetamol + Serratiopeptidase", "Analgesics", "Alkem", 145.00),
    ("Hifenac-P Tablet", "Aceclofenac + Paracetamol", "Analgesics", "Intas", 95.00),
    ("Meftal-Spas Tablet", "Mefenamic Acid + Dicyclomine", "Analgesics", "Blue Cross", 48.00),
    
    # Antibiotics
    ("Augmentin 625 Duo Tablet", "Amoxicillin + Clavulanic Acid", "Antibiotics", "GSK", 201.00),
    ("Azithral 500 Tablet", "Azithromycin 500mg", "Antibiotics", "Alembic", 119.00),
    ("Taxim-O 200 Tablet", "Cefixime 200mg", "Antibiotics", "Alkem", 108.00),
    ("Monocef-O 200 Tablet", "Cefpodoxime 200mg", "Antibiotics", "Aristo", 155.00),
    ("Zifi 200 Tablet", "Cefixime 200mg", "Antibiotics", "FDC", 109.00),
    ("Cifran 500 Tablet", "Ciprofloxacin 500mg", "Antibiotics", "Sun Pharma", 42.00),
    ("Novamox 500 Capsule", "Amoxicillin 500mg", "Antibiotics", "Cipla", 70.00),
    ("Clavam 625 Tablet", "Amoxicillin + Clavulanic Acid", "Antibiotics", "Alkem", 205.00),
    ("Mahacef 200 Tablet", "Cefixime 200mg", "Antibiotics", "Mankind", 99.00),
    ("Gudcef 200 Tablet", "Cefpodoxime 200mg", "Antibiotics", "Mankind", 145.00),
    
    # Antacids & Gastro
    ("Pan-D Capsule", "Pantoprazole + Domperidone", "Antacids", "Alkem", 199.00),
    ("Gelusil MPS Liquid", "Antacid + Antigas", "Antacids", "Pfizer", 125.00),
    ("Digene Tablets", "Antacid", "Antacids", "Abbott", 22.00),
    ("Omee Capsule", "Omeprazole 20mg", "Antacids", "Alkem", 55.00),
    ("Rantac 150 Tablet", "Ranitidine 150mg", "Antacids", "J.B. Chemicals", 35.00),
    ("Pantocid 40 Tablet", "Pantoprazole 40mg", "Antacids", "Sun Pharma", 155.00),
    ("Aciloc 150 Tablet", "Ranitidine 150mg", "Antacids", "Cadila", 38.00),
    ("Omez 20 Capsule", "Omeprazole 20mg", "Antacids", "Dr. Reddy's", 58.00),
    ("Rabicip 20 Tablet", "Rabeprazole 20mg", "Antacids", "Cipla", 85.00),
    ("Sompraz 40 Tablet", "Esomeprazole 40mg", "Antacids", "Sun Pharma", 145.00),
    
    # Antiallergics
    ("Allegra 120mg Tablet", "Fexofenadine 120mg", "Antiallergic", "Sanofi", 205.00),
    ("Montek LC Tablet", "Montelukast + Levocetirizine", "Antiallergic", "Sun Pharma", 195.00),
    ("Cetirizine 10mg Tablet", "Cetirizine 10mg", "Antiallergic", "GSK", 18.00),
    ("Levocet Tablet", "Levocetirizine 5mg", "Antiallergic", "Hetero", 45.00),
    ("Avil 25 Tablet", "Pheniramine 25mg", "Antiallergic", "Sanofi", 10.00),
    ("Atarax 25 Tablet", "Hydroxyzine 25mg", "Antiallergic", "Dr. Reddy's", 85.00),
    ("Alerid Tablet", "Cetirizine 10mg", "Antiallergic", "Cipla", 20.00),
    ("Okacet Tablet", "Cetirizine 10mg", "Antiallergic", "Cipla", 19.00),
    ("Xyzal 5 Tablet", "Levocetirizine 5mg", "Antiallergic", "Dr. Reddy's", 155.00),
    ("Telekast-L Tablet", "Montelukast + Levocetirizine", "Antiallergic", "Lupin", 185.00),
    
    # Vitamins & Supplements
    ("Zincovit Tablet", "Multivitamins + Zinc", "Supplements", "Apex Labs", 105.00),
    ("Shelcal 500 Tablet", "Calcium + Vitamin D3", "Supplements", "Torrent", 119.00),
    ("Becosules Z Capsule", "B-Complex + Vitamin C + Zinc", "Supplements", "Pfizer", 45.00),
    ("Supradyn Daily Tablet", "Multivitamins", "Supplements", "Bayer", 55.00),
    ("A to Z NS Tablet", "Multivitamins + Minerals", "Supplements", "Alkem", 110.00),
    ("Neurobion Forte Tablet", "B-Complex Vitamins", "Supplements", "P&G", 35.00),
    ("Evion 400 Capsule", "Vitamin E 400 IU", "Supplements", "P&G", 35.00),
    ("Limcee Chewable Tablet", "Vitamin C 500mg", "Supplements", "Abbott", 25.00),
    ("Revital H Capsule", "Ginseng + Multivitamins", "Supplements", "Sun Pharma", 115.00),
    ("Calcimax Forte Tablet", "Calcium + Vitamin D3 + Minerals", "Supplements", "Meyer", 185.00),
    
    # Cardiac
    ("Ecosprin 75 Tablet", "Aspirin 75mg", "Cardiac", "USV", 5.00),
    ("Telmikind 40 Tablet", "Telmisartan 40mg", "Cardiac", "Mankind", 55.00),
    ("Amlokind 5 Tablet", "Amlodipine 5mg", "Cardiac", "Mankind", 25.00),
    ("Concor 5 Tablet", "Bisoprolol 5mg", "Cardiac", "Merck", 95.00),
    ("Atorva 10 Tablet", "Atorvastatin 10mg", "Cardiac", "Zydus", 75.00),
    ("Rosuvas 10 Tablet", "Rosuvastatin 10mg", "Cardiac", "Sun Pharma", 165.00),
    ("Tazloc 40 Tablet", "Telmisartan 40mg", "Cardiac", "USV", 85.00),
    ("Cilacar 10 Tablet", "Cilnidipine 10mg", "Cardiac", "J.B. Chemicals", 105.00),
    ("Metolar XR 50 Capsule", "Metoprolol 50mg", "Cardiac", "Cipla", 75.00),
    ("Sorbitrate 5 Tablet", "Isosorbide Dinitrate 5mg", "Cardiac", "Abbott", 45.00),
    
    # Anti-Diabetic
    ("Glycomet-GP 1 Tablet", "Glimepiride + Metformin", "Anti-Diabetic", "USV", 135.00),
    ("Amaryl 1mg Tablet", "Glimepiride 1mg", "Anti-Diabetic", "Sanofi", 125.00),
    ("Jalra 50mg Tablet", "Vildagliptin 50mg", "Anti-Diabetic", "Novartis", 285.00),
    ("Januvia 100mg Tablet", "Sitagliptin 100mg", "Anti-Diabetic", "MSD", 325.00),
    ("Tenglyn 20 Tablet", "Teneligliptin 20mg", "Anti-Diabetic", "Zydus", 145.00),
    ("Istamet 50/500 Tablet", "Sitagliptin + Metformin", "Anti-Diabetic", "Sun Pharma", 305.00),
    ("Vildamac 50 Tablet", "Vildagliptin 50mg", "Anti-Diabetic", "Macleods", 185.00),
    ("Galvus 50mg Tablet", "Vildagliptin 50mg", "Anti-Diabetic", "Novartis", 295.00),
    ("Zoryl M1 Tablet", "Glimepiride + Metformin", "Anti-Diabetic", "Intas", 145.00),
    ("Gluconorm-G 1 Tablet", "Glimepiride + Metformin", "Anti-Diabetic", "Lupin", 135.00),
    
    # Respiratory & Syrups
    ("Ascoril LS Syrup", "Ambroxol + Levosalbutamol", "Syrups", "Glenmark", 118.00),
    ("Bro-Zedex Syrup", "Bromhexine + Guaifenesin", "Syrups", "Wockhardt", 125.00),
    ("Grilinctus Syrup", "Dextromethorphan + Chlorpheniramine", "Syrups", "Franco-Indian", 115.00),
    ("Benadryl Cough Syrup", "Diphenhydramine", "Syrups", "J&J", 118.00),
    ("Asthalin Inhaler", "Salbutamol 100mcg", "Respiratory", "Cipla", 145.00),
    ("Foracort 200 Inhaler", "Formoterol + Budesonide", "Respiratory", "Cipla", 385.00),
    ("Duolin Inhaler", "Levosalbutamol + Ipratropium", "Respiratory", "Cipla", 295.00),
    ("Budecort 200 Inhaler", "Budesonide 200mcg", "Respiratory", "Cipla", 345.00),
    ("Seroflo 250 Inhaler", "Salmeterol + Fluticasone", "Respiratory", "Cipla", 485.00),
    ("Deriphyllin Retard 150 Tablet", "Etofylline + Theophylline", "Respiratory", "Zydus", 45.00),
    
    # Ointments & Topicals
    ("Betadine 2% Ointment", "Povidone Iodine", "Ointments", "Win-Medicare", 105.00),
    ("Volini Gel", "Diclofenac Diethylamine", "Ointments", "Sun Pharma", 110.00),
    ("Moov Pain Relief Cream", "Diclofenac + Wintergreen Oil", "Ointments", "Reckitt", 95.00),
    ("Soframycin Skin Cream", "Framycetin", "Ointments", "Sanofi", 55.00),
    ("Candid-B Cream", "Clotrimazole + Beclometasone", "Ointments", "Glenmark", 125.00),
    ("Fourderm Cream", "Chlorhexidine + Clobetasol + Miconazole", "Ointments", "Cipla", 115.00),
    ("Quadriderm RF Cream", "Beclometasone + Clotrimazole", "Ointments", "Fulford", 135.00),
    ("T-Bact Ointment", "Mupirocin 2%", "Ointments", "GSK", 145.00),
    ("Tenovate Cream", "Clobetasol Propionate", "Ointments", "GSK", 85.00),
    ("Lulican Cream", "Luliconazole 1%", "Ointments", "Glenmark", 195.00),
    
    # Miscellaneous / Others
    ("Thyronorm 50mcg Tablet", "Thyroxine 50mcg", "Thyroid", "Abbott", 169.00),
    ("Eltroxin 50mcg Tablet", "Thyroxine 50mcg", "Thyroid", "GSK", 145.00),
    ("Dytor 10 Tablet", "Torasemide 10mg", "Diuretics", "Cipla", 85.00),
    ("Lasix 40 Tablet", "Furosemide 40mg", "Diuretics", "Sanofi", 15.00),
    ("Aldactone 25 Tablet", "Spironolactone 25mg", "Diuretics", "RPG", 45.00),
    ("Urimax 0.4 Capsule", "Tamsulosin 0.4mg", "Urology", "Cipla", 185.00),
    ("Silodal 8 Capsule", "Silodosin 8mg", "Urology", "Sun Pharma", 225.00),
    ("Viagra 50mg Tablet", "Sildenafil 50mg", "Men's Health", "Pfizer", 450.00),
    ("i-Pill Tablet", "Levonorgestrel 1.5mg", "Women's Health", "Piramal", 110.00),
    ("Regestrone 5mg Tablet", "Norethisterone 5mg", "Women's Health", "Torrent", 65.00)
]

def run():
    print("Clearing database for the final 100 REAL market medicines...")
    Product.objects.all().delete()
    
    # We will track fetched images to avoid hitting Bing 100 times for similar keywords if any, 
    # but all 100 are unique, so 100 requests will happen.
    
    for i, item in enumerate(MEDICINES):
        try:
            name, generic, cat_name, brand_name, mrp = item
            
            cat, _ = Category.objects.get_or_create(name=cat_name)
            man, _ = Manufacturer.objects.get_or_create(name=brand_name)
            brand, _ = Brand.objects.get_or_create(name=brand_name, defaults={'manufacturer': man})
            
            wp = round(mrp * 0.75, 2)
            pack = "10 Tablets" if "Tablet" in name else "100ml Bottle" if "Syrup" in name else "15g Tube" if "Cream" in name else "1 Box"
            
            product = Product.objects.create(
                name=name,
                generic_name=generic,
                category=cat,
                manufacturer=man,
                brand=brand,
                mrp=mrp,
                wholesale_price=wp,
                pack_size=pack,
                gst_rate=12.0,
                min_order_quantity=10,
                barcode=str(random.randint(100000000000, 999999999999)),
                is_active=True,
                stock_status='in_stock'
            )
            
            Batch.objects.create(
                product=product,
                batch_number=f"BN-{random.randint(1000, 9999)}",
                manufacturing_date=timezone.now().date() - datetime.timedelta(days=random.randint(30, 200)),
                expiry_date=timezone.now().date() + datetime.timedelta(days=random.randint(300, 800)),
                stock_quantity=random.randint(50, 500)
            )
            
            # Fetch Image
            query = f"{name} medicine".replace(' ', '+')
            url = f"https://tse1.mm.bing.net/th?q={query}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            if resp.status_code == 200:
                product.image.save(f"market_{product.id}.jpg", ContentFile(resp.content), save=True)
            else:
                print(f"Failed image for: {name}")
                
            if (i+1) % 10 == 0:
                print(f"Processed {i+1}/100 medicines...")
                
            # Sleep tiny bit to avoid rapid rate limits
            time.sleep(0.5)
                
        except Exception as e:
            print(f"Error on {item[0]}: {e}")

    print("Successfully populated 100 REAL market medicines with REAL photos!")

if __name__ == '__main__':
    run()
