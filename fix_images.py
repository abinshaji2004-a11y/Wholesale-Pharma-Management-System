import urllib.request
import re
import os
import random
from django.core.files.base import ContentFile
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()
from inventory.models import Product

# Scrape Category:Pharmaceutical_packaging
url = 'https://commons.wikimedia.org/wiki/Category:Pharmaceutical_packaging'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
html = urllib.request.urlopen(req).read().decode('utf-8')

# Find thumbnail images on the category page
images = re.findall(r'src=\"(https://upload\.wikimedia\.org/wikipedia/commons/thumb/[^\"]+\.(?:jpg|JPG)/[^\"]+px-[^\"]+\.(?:jpg|JPG))\"', html)

saved_files = []
for idx, img_url in enumerate(list(set(images))[:10]):
    try:
        # Get full resolution image by removing the thumb part
        # Example thumb: https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Box.jpg/120px-Box.jpg
        # Full: https://upload.wikimedia.org/wikipedia/commons/a/a1/Box.jpg
        full_url = img_url.replace('/thumb/', '/').rsplit('/', 1)[0]
        
        r = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        img_data = urllib.request.urlopen(r).read()
        file_name = f'real_pack_{idx}.jpg'
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
    print(f"Updated {count} products with REAL generic packaging images!")
else:
    print("Failed to download any images.")
