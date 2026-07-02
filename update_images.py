import os
import django
import random
import requests
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()

from inventory.models import Product

# List of realistic medicine images from Unsplash
IMAGE_URLS = [
    "https://images.unsplash.com/photo-1584308666744-24d5e47761cb?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1583324113626-70df0f4deaab?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1550572017-edb708b73e51?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1587854692152-cbe660dbde88?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1471864190281-a93a3070b6de?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1576086213369-97a306d36557?auto=format&fit=crop&w=400&q=80"
]

def run():
    print("Downloading realistic base images...")
    base_images = []
    for i, url in enumerate(IMAGE_URLS):
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code == 200:
                base_images.append(resp.content)
                print(f"Downloaded image {i+1}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            
    if not base_images:
        print("Failed to download any base images.")
        return

    products = Product.objects.all()
    print(f"Updating {products.count()} products with realistic photos...")
    
    for i, product in enumerate(products):
        # Pick a random realistic image
        img_content = random.choice(base_images)
        
        # Save it to the product
        product.image.save(f"real_med_{product.id}.jpg", ContentFile(img_content), save=True)
        
        if (i+1) % 20 == 0:
            print(f"Updated {i+1} products...")
            
    print("Successfully updated all product photos!")

if __name__ == '__main__':
    run()
