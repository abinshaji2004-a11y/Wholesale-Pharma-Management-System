import os
import random
from django.core.management.base import BaseCommand
from inventory.models import Product

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # Find all real images in media/products/
        import glob
        media_products_dir = os.path.join('media', 'products')
        
        # Get all jpg files that start with 'real_'
        real_images = glob.glob(os.path.join(media_products_dir, 'real_*.jpg'))
        
        if not real_images:
            self.stdout.write("No real images found!")
            return
            
        # Strip path to just the filename so it can be 'products/real_med_x.jpg'
        real_image_paths = [os.path.basename(p) for p in real_images]
        
        products = Product.objects.all()
        for product in products:
            # We can match by generic name for some, or just assign random
            assigned = False
            for r_img in real_image_paths:
                # If generic name is in the filename (e.g. Paracetamol)
                if product.generic_name and product.generic_name.split()[0] in r_img:
                    product.image.name = f"products/{r_img}"
                    product.save()
                    assigned = True
                    break
                    
            if not assigned:
                random_img = random.choice(real_image_paths)
                product.image.name = f"products/{random_img}"
                product.save()
                
        self.stdout.write("Successfully updated all products to use existing real images!")
