import os, time, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
from inventory.models import Product
from duckduckgo_search import DDGS
import urllib.request

def run():
    products = Product.objects.all()
    count = 0
    with DDGS() as ddgs:
        for p in products:
            if 'real_blister_pack' in p.image.name or p.image.name == '' or p.image.name.endswith('png') or 'ai' in p.image.name:
                query = f"{p.name} medicine box india"
                print(f"Searching for {query}...")
                try:
                    results = list(ddgs.images(query, max_results=1))
                    if results:
                        img_url = results[0]['image']
                        req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                        img_data = urllib.request.urlopen(req, timeout=10).read()
                        
                        file_name = f"real_{p.generic_name.split()[0]}_{p.id}.jpg"
                        out_path = os.path.join('media', 'products', file_name)
                        with open(out_path, 'wb') as f:
                            f.write(img_data)
                            
                        p.image.name = f"products/{file_name}"
                        p.save()
                        print(f"Downloaded real image for {p.name}")
                        count += 1
                        time.sleep(5)
                except Exception as e:
                    print(f"Error for {p.name}: {e}")
                    time.sleep(10)
    print(f"Finished downloading {count} remaining images.")

if __name__ == '__main__':
    run()
