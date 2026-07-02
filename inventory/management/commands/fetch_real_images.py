import os
import requests
import time
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from inventory.models import Product
from duckduckgo_search import DDGS

class Command(BaseCommand):
    help = 'Fetches real images from DuckDuckGo for all products'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting to fetch real images for products...")
        products = Product.objects.all()
        
        ddgs = DDGS()
        
        for product in products:
            search_query = f"{product.name} {product.manufacturer.name if product.manufacturer else ''} medicine box india"
            self.stdout.write(f"Searching for: {search_query}")
            
            try:
                results = list(ddgs.images(search_query, max_results=3))
                if not results:
                    self.stdout.write(self.style.WARNING(f"No image found for {product.name}"))
                    continue
                
                # Try downloading the first available image
                success = False
                for res in results:
                    image_url = res['image']
                    try:
                        response = requests.get(image_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                        if response.status_code == 200:
                            # Save it
                            ext = image_url.split('.')[-1].split('?')[0]
                            if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp']:
                                ext = 'jpg'
                            file_name = f"{product.barcode}_real.{ext}"
                            
                            product.image.save(file_name, ContentFile(response.content), save=True)
                            self.stdout.write(self.style.SUCCESS(f"Successfully updated image for {product.name}"))
                            success = True
                            break
                    except Exception as download_err:
                        self.stdout.write(self.style.WARNING(f"Failed to download URL {image_url}: {download_err}"))
                        continue
                
                if not success:
                    self.stdout.write(self.style.ERROR(f"Could not fetch any valid image for {product.name}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Search failed for {product.name}: {e}"))
            
            # Sleep slightly to avoid DDGS rate limiting
            time.sleep(2)
            
        self.stdout.write(self.style.SUCCESS("Finished updating product images!"))
