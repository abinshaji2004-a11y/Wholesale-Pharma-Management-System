import os, time, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from inventory.models import Product
from duckduckgo_search import DDGS
import urllib.request

def run():
    products = Product.objects.all()
    total = products.count()
    print(f"Starting download of EXACT images for {total} products...", flush=True)
    count = 0
    
    with DDGS() as ddgs:
        for idx, p in enumerate(products, 1):
            query = f"{p.name} medicine box india"
            try:
                results = list(ddgs.images(query, max_results=1))
                if results:
                    img_url = results[0]['image']
                    req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                    img_data = urllib.request.urlopen(req, timeout=10).read()
                    
                    safe_name = "".join([c for c in p.name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    file_name = f"exact_{safe_name.replace(' ', '_')}_{p.id}.jpg"
                    out_path = os.path.join('media', 'products', file_name)
                    
                    with open(out_path, 'wb') as f:
                        f.write(img_data)
                        
                    p.image.name = f"products/{file_name}"
                    p.save()
                    print(f"[{idx}/{total}] Downloaded exactly: {p.name}", flush=True)
                    count += 1
                else:
                    print(f"[{idx}/{total}] No exact image found for {p.name}", flush=True)
            except Exception as e:
                print(f"[{idx}/{total}] Error for {p.name}: {e}", flush=True)
                
            time.sleep(2)
            
    print(f"Finished downloading {count} exact real images.", flush=True)

if __name__ == '__main__':
    run()
