import urllib.request
import re
import os
import random
from django.core.files.base import ContentFile
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()
from inventory.models import Product

wiki_drugs = ['Paracetamol', 'Amoxicillin', 'Ibuprofen', 'Aspirin', 'Cetirizine', 'Omeprazole', 'Metformin']
real_image_urls = []

print("Scraping real images from Wikipedia...")
for drug in wiki_drugs:
    try:
        url = f'https://en.wikipedia.org/wiki/{drug}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req).read().decode('utf-8')
        # Find the first image link that looks like a drug photo
        match = re.search(r'\"(https://upload\.wikimedia\.org/wikipedia/commons/thumb/[^\"]+/(?:Paracetamol|Amoxicillin|Ibuprofen|Aspirin|Cetirizine|Omeprazole|Metformin|Tablet|Pill)[^\"]+\.(?:jpg|png))\"', html, re.IGNORECASE)
        if match:
            # Get full image instead of thumb
            img_url = match.group(1).replace('/thumb/', '/').rsplit('/', 1)[0]
            real_image_urls.append(img_url)
            print(f"Found image for {drug}: {img_url}")
    except Exception as e:
        print(f"Error scraping {drug}: {e}")

# Fallback direct Wikipedia image links (Creative Commons)
fallback_urls = [
    'https://upload.wikimedia.org/wikipedia/commons/1/1a/Paracetamol-Tablets.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/e/e6/Aspirin-tablets.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/d/d4/Ibuprofen-tablets.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/3/36/Amoxicillin_Capsules_500mg.jpg'
]

if not real_image_urls:
    real_image_urls = fallback_urls

# Download the images locally
saved_files = []
for idx, img_url in enumerate(real_image_urls):
    try:
        req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
        img_data = urllib.request.urlopen(req).read()
        file_name = f'real_wiki_drug_{idx}.jpg'
        
        # Save manually to media/products/
        out_path = os.path.join('media', 'products', file_name)
        with open(out_path, 'wb') as f:
            f.write(img_data)
        saved_files.append(file_name)
        print(f"Downloaded {file_name}")
    except Exception as e:
        print(f"Failed to download {img_url}: {e}")

if saved_files:
    products = Product.objects.all()
    count = 0
    for p in products:
        random_file = random.choice(saved_files)
        p.image.name = f"products/{random_file}"
        p.save()
        count += 1
    print(f"Updated {count} products with REAL Wikipedia images!")
else:
    print("Failed to secure any real images.")
