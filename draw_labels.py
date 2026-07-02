import os
import django
import random
import io
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()

from inventory.models import Product
from django.core.files.base import ContentFile

def run():
    print("Preparing to draw custom labels...")
    
    # We will use the existing product photos as bases
    products = Product.objects.all()
    print(f"Found {products.count()} products.")
    
    # Try to load a nice font, fallback to default
    try:
        font = ImageFont.truetype("arialbd.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        small_font = font

    for i, product in enumerate(products):
        try:
            # Open the current product image
            if not product.image:
                continue
                
            img_path = product.image.path
            base = Image.open(img_path).convert("RGBA")
            
            # Create a drawing context
            draw = ImageDraw.Draw(base)
            
            # We want to draw a label in the middle of the image
            width, height = base.size
            
            # Label size and position
            label_w = width * 0.8
            label_h = 100
            label_x = (width - label_w) / 2
            label_y = (height - label_h) / 2
            
            # Draw a white rectangle with a border for the label
            draw.rectangle([label_x, label_y, label_x + label_w, label_y + label_h], fill=(255, 255, 255, 240), outline=(0, 0, 0, 200), width=3)
            
            # Draw the medicine name
            text = product.name
            
            # Calculate text size and center it
            # Using getbbox or fallback
            if hasattr(font, 'getbbox'):
                bbox = font.getbbox(text)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            else:
                tw, th = draw.textsize(text, font=font)
                
            tx = label_x + (label_w - tw) / 2
            ty = label_y + (label_h - th) / 2 - 10
            
            draw.text((tx, ty), text, fill=(10, 88, 202), font=font)
            
            # Draw generic name/pack size below
            subtext = f"{product.generic_name} | {product.pack_size}"
            if hasattr(small_font, 'getbbox'):
                bbox2 = small_font.getbbox(subtext)
                sw, sh = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
            else:
                sw, sh = draw.textsize(subtext, font=small_font)
                
            sx = label_x + (label_w - sw) / 2
            sy = ty + th + 10
            
            draw.text((sx, sy), subtext, fill=(50, 50, 50), font=small_font)
            
            # Save the image back
            output = io.BytesIO()
            # Convert to RGB to save as JPEG/PNG
            final_img = base.convert("RGB")
            final_img.save(output, format='PNG')
            
            product.image.save(f"labeled_{product.id}.png", ContentFile(output.getvalue()), save=True)
            
            if (i+1) % 20 == 0:
                print(f"Labeled {i+1} products...")
                
        except Exception as e:
            print(f"Error labeling product {product.id}: {e}")

    print("Successfully labeled all product photos!")

if __name__ == '__main__':
    run()
