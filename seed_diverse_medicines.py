import os, time, urllib.request, urllib.parse, urllib.error
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()

from inventory.models import Product, Category
from PIL import Image, ImageDraw, ImageFont

def generate_fallback_image(product):
    img = Image.new('RGB', (400, 400), color=(240, 245, 250))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(20, 20), (380, 380)], radius=20, fill=(255, 255, 255), outline=(200, 210, 220), width=2)
    cross_color = (40, 167, 69)
    draw.rectangle([(190, 80), (210, 140)], fill=cross_color)
    draw.rectangle([(160, 100), (240, 120)], fill=cross_color)
    
    try: font_title = ImageFont.truetype("arial.ttf", 36)
    except: font_title = ImageFont.load_default()
    
    words = product.name.split()
    lines, current_line = [], ""
    for word in words:
        if len(current_line + " " + word) < 18: current_line += " " + word
        else:
            lines.append(current_line.strip())
            current_line = word
    if current_line: lines.append(current_line.strip())
        
    y = 180
    for line in lines:
        try: w = draw.textbbox((0,0), line, font=font_title)[2]
        except: w = draw.textsize(line, font=font_title)[0]
        draw.text(((400 - w) / 2, y), line, fill=(30, 40, 50), font=font_title)
        y += 45
        
    safe_name = "".join([c for c in product.name if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(' ', '_')
    file_name = f"local_{safe_name}_{product.id}.jpg"
    out_path = os.path.join('media', 'products', file_name)
    img.save(out_path, quality=95)
    return f"products/{file_name}"

def run():
    diverse_medicines = [
        ("Asthalin Inhaler", "Respiratory", "Salbutamol 100mcg", "200 MDI", 150.00),
        ("Betadine Ointment", "First Aid", "Povidone Iodine 10%", "20g Tube", 85.00),
        ("Volini Spray", "Pain Relief", "Diclofenac", "60g Can", 199.00),
        ("Refresh Tears", "Eye Care", "Carboxymethylcellulose 0.5%", "10ml Drop", 140.00),
        ("Candid V Gel", "Gynecology", "Clotrimazole 2%", "30g Tube", 115.00),
        ("Vicks VapoRub", "Cold & Cough", "Menthol & Camphor", "50g Jar", 95.00),
        ("Soframycin Cream", "Antibiotics", "Framycetin 1%", "30g Tube", 55.00),
        ("Dettol Liquid", "Antiseptic", "Chloroxylenol", "500ml Bottle", 185.00),
        ("Electral ORS", "Supplements", "Oral Rehydration Salts", "21g Sachet", 20.00),
        ("Hansaplast Bandage", "First Aid", "Adhesive Bandage", "100 Strips", 150.00),
        ("Revital H Gummies", "Supplements", "Multivitamin & Minerals", "30 Gummies", 250.00),
        ("Lantus Insulin Pen", "Diabetes", "Insulin Glargine", "3ml Pen", 650.00),
        ("Caladryl Lotion", "Dermatology", "Calamine & Diphenhydramine", "100ml Bottle", 80.00),
        ("VWash Plus", "Hygiene", "Lactic Acid", "100ml Bottle", 180.00),
        ("Eno Fruit Salt", "Antacids", "Svarjiksara & Nimbukamlam", "5g Sachet", 10.00),
    ]
    
    print("Seeding diverse medicines...")
    for name, cat_name, generic, pack, price in diverse_medicines:
        cat, _ = Category.objects.get_or_create(name=cat_name)
        product, created = Product.objects.get_or_create(
            name=name,
            defaults={
                'category': cat, 'generic_name': generic, 'pack_size': pack,
                'mrp': price, 'wholesale_price': price * 0.7, 'gst_rate': 12.0,
                'barcode': f"DIV{int(time.time()*1000)}"[-12:]
            }
        )
        if created or not product.image:
            print(f"Generating image for {name}...")
            # Try pollinations first
            prompt = f"A photorealistic macro photograph of a medicine {name}. Professional lighting, 4k."
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=400&height=400&nologo=true"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                img_data = urllib.request.urlopen(req, timeout=15).read()
                safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(' ', '_')
                file_name = f"ai_{safe_name}_{product.id}.jpg"
                out_path = os.path.join('media', 'products', file_name)
                with open(out_path, 'wb') as f:
                    f.write(img_data)
                product.image.name = f"products/{file_name}"
                time.sleep(3)
            except Exception as e:
                print(f"Pollinations failed for {name} ({e}), using fallback.")
                product.image.name = generate_fallback_image(product)
                
            product.save()

    print("Finished seeding diverse medicines!")

if __name__ == '__main__':
    run()
