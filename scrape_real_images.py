import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from inventory.models import Product
from playwright.sync_api import sync_playwright
import urllib.request
import urllib.parse
import time

def run():
    products = Product.objects.all()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        
        for idx, product in enumerate(products, 1):
            name = product.name
            query = f"{name} medicine box india"
            encoded_query = urllib.parse.quote(query)
            url = f"https://duckduckgo.com/?q={encoded_query}&t=h_&iar=images&iax=images&ia=images"
            
            print(f"[{idx}/100] Searching real image for {name}...")
            
            try:
                page.goto(url, wait_until="networkidle")
                time.sleep(2)  # wait for images to load
                
                # Wait for the first image tile to appear
                page.wait_for_selector('img.tile--img__img', timeout=10000)
                
                # Get the first image src
                img_src = page.eval_on_selector('img.tile--img__img', 'el => el.src')
                
                if img_src and img_src.startswith('http'):
                    # Download it
                    req = urllib.request.Request(img_src, headers={'User-Agent': 'Mozilla/5.0'})
                    img_data = urllib.request.urlopen(req).read()
                    
                    safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    file_name = f"{safe_name.replace(' ', '_')}_{product.id}_real.jpg"
                    out_path = os.path.join('media', 'products', file_name)
                    
                    with open(out_path, 'wb') as f:
                        f.write(img_data)
                        
                    product.image.name = f"products/{file_name}"
                    product.save()
                    print(f"Success for {name}")
                else:
                    print(f"No valid image found for {name}")
                    
            except Exception as e:
                print(f"Error on {name}: {e}")
                
        browser.close()

if __name__ == '__main__':
    run()
