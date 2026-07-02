import os
import django
import glob
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()
from inventory.models import Product

def run():
    products = Product.objects.all()
    assigned_count = 0
    missing = []
    
    for p in products:
        if not p.generic_name:
            missing.append(p.name)
            continue
            
        # Extract the first word of the generic name (e.g., 'Amoxicillin' from 'Amoxicillin 500mg')
        gen_base = p.generic_name.split()[0].replace(',', '').replace('+', '')
        
        # Look for images starting with 'real_' and containing the generic base name
        pattern = os.path.join('media', 'products', f'real_{gen_base}*.jpg')
        matches = glob.glob(pattern)
        
        if matches:
            # Pick a random match to add variety if there are multiple
            selected_image = random.choice(matches)
            # Make path relative to MEDIA_ROOT (i.e. 'products/filename.jpg')
            rel_path = os.path.relpath(selected_image, 'media').replace('\\', '/')
            p.image.name = rel_path
            p.save()
            assigned_count += 1
        else:
            missing.append(p.name)
            
    print(f'Successfully assigned real images to {assigned_count} products.')
    print(f'Missing exact real images for {len(missing)} products.')
    if missing:
        print('First 10 missing:', missing[:10])

if __name__ == '__main__':
    run()
