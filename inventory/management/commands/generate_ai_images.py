import urllib.request
import urllib.parse
import urllib.error
import os
import time
from django.core.management.base import BaseCommand
from inventory.models import Product

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        products = Product.objects.all()
        total = products.count()
        self.stdout.write(f"Generating custom AI images for {total} products with rate-limit protection...")
        
        for idx, product in enumerate(products, 1):
            name = product.name
            # Skip if already has an ai image
            if product.image and '_ai.jpg' in product.image.name:
                continue
                
            prompt = f"A highly realistic photorealistic macro photograph of a medicine box sitting on a pharmacy counter clearly labeled with exact text {name} prominently on front. Professional lighting, 8k"
            encoded_prompt = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=400&height=400&nologo=true"
            
            success = False
            retries = 3
            while not success and retries > 0:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    img_data = urllib.request.urlopen(req).read()
                    
                    safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    file_name = f"{safe_name.replace(' ', '_')}_{product.id}_ai.jpg"
                    out_path = os.path.join('media', 'products', file_name)
                    
                    with open(out_path, 'wb') as f:
                        f.write(img_data)
                        
                    product.image.name = f"products/{file_name}"
                    product.save()
                    
                    self.stdout.write(f"[{idx}/{total}] Generated AI image for {name}")
                    success = True
                    time.sleep(10)  # Long delay to prevent 429 Too Many Requests
                    
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        self.stdout.write(f"Rate limited on {name}. Waiting 20 seconds...")
                        time.sleep(20)
                        retries -= 1
                    else:
                        self.stdout.write(f"HTTP Error {e.code} on {name}")
                        break
                except Exception as e:
                    self.stdout.write(f"Error on {name}: {e}")
                    break
                    
        self.stdout.write("Finished generating all AI medicine images!")
