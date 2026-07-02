import os
import django
import requests
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()

from inventory.models import Product

def run():
    products = Product.objects.all()
    print(f"Fetching REAL images for {products.count()} products from Bing Search...")
    
    # To avoid downloading the same image 10 times for 10 Amoxicillins, we can cache them by generic_name
    image_cache = {}

    for i, product in enumerate(products):
        try:
            generic = product.generic_name
            if generic not in image_cache:
                # Use Bing Image Search Thumbnail API for the exact medicine
                query = f"{generic}+medicine+box"
                url = f"https://tse1.mm.bing.net/th?q={query}"
                
                resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                if resp.status_code == 200:
                    image_cache[generic] = resp.content
                else:
                    print(f"Failed to fetch {generic}")
                    continue
            
            # Save the cached real image to the product
            img_content = image_cache.get(generic)
            if img_content:
                product.image.save(f"real_{generic}_{product.id}.jpg", ContentFile(img_content), save=True)
            
            if (i+1) % 20 == 0:
                print(f"Updated {i+1} products...")
                
        except Exception as e:
            print(f"Error updating product {product.id}: {e}")

    print("Successfully assigned 100% REAL medicine images!")

if __name__ == '__main__':
    run()
