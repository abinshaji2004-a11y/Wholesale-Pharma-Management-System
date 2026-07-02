import os, time, urllib.request, urllib.parse
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()
from inventory.models import Product

def run():
    products = Product.objects.all()
    total = products.count()
    print(f"Starting AI image generation for {total} products...")
    
    count = 0
    for idx, p in enumerate(products, 1):
        # We want isolated product images, no realistic backgrounds
        prompt = f"A clean 3D render of a medicine product package for {p.name}, isolated on a pure white background, minimalist product photography"
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=400&height=400&nologo=true&seed={p.id}"
        
        safe_name = "".join([c for c in p.name if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(' ', '_')
        file_name = f"isolated_ai_{safe_name}_{p.id}.jpg"
        out_path = os.path.join('media', 'products', file_name)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                img_data = urllib.request.urlopen(req, timeout=15).read()
                
                with open(out_path, 'wb') as f:
                    f.write(img_data)
                    
                p.image.name = f"products/{file_name}"
                p.save()
                print(f"[{idx}/{total}] Successfully generated AI image for {p.name}", flush=True)
                count += 1
                time.sleep(2)  # Prevent rate limiting
                break
            except Exception as e:
                print(f"[{idx}/{total}] Attempt {attempt+1} failed for {p.name}: {e}", flush=True)
                time.sleep(5)
                
    print(f"Finished generating {count} AI images.", flush=True)

if __name__ == '__main__':
    run()
