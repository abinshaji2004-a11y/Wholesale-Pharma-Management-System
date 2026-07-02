import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()
from inventory.models import Product
from PIL import Image, ImageDraw, ImageFont

def generate_local_images():
    products = Product.objects.all()
    count = 0
    print(f"Generating 100 local professional images...")
    
    # Try to find a generic font, fallback to default
    try:
        # Windows standard font
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_sub = ImageFont.truetype("arial.ttf", 20)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    for p in products:
        # Create a clean white/gray gradient background (400x400)
        img = Image.new('RGB', (400, 400), color=(240, 245, 250))
        draw = ImageDraw.Draw(img)
        
        # Draw a modern card shape
        draw.rounded_rectangle([(20, 20), (380, 380)], radius=20, fill=(255, 255, 255), outline=(200, 210, 220), width=2)
        
        # Draw a medical cross icon
        cross_color = (40, 167, 69) # Green
        draw.rectangle([(190, 80), (210, 140)], fill=cross_color)
        draw.rectangle([(160, 100), (240, 120)], fill=cross_color)
        
        # Draw Medicine Name (centered)
        name = p.name
        # Simple text wrapping
        words = name.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + " " + word) < 18:
                current_line += " " + word
            else:
                lines.append(current_line.strip())
                current_line = word
        if current_line:
            lines.append(current_line.strip())
            
        y_text = 180
        for line in lines:
            try:
                # Pillow >= 10.0
                bbox = draw.textbbox((0,0), line, font=font_title)
                w = bbox[2] - bbox[0]
            except AttributeError:
                # Older Pillow
                w, h = draw.textsize(line, font=font_title)
            
            draw.text(((400 - w) / 2, y_text), line, fill=(30, 40, 50), font=font_title)
            y_text += 45
            
        # Draw Category / Generic
        cat = p.category.name if p.category else ""
        try:
            bbox = draw.textbbox((0,0), cat, font=font_sub)
            w2 = bbox[2] - bbox[0]
        except AttributeError:
            w2, h2 = draw.textsize(cat, font=font_sub)
        draw.text(((400 - w2) / 2, y_text + 10), cat, fill=(100, 110, 120), font=font_sub)
        
        # Save image
        safe_name = "".join([c for c in p.name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        file_name = f"local_{safe_name.replace(' ', '_')}_{p.id}.jpg"
        out_path = os.path.join('media', 'products', file_name)
        
        img.save(out_path, quality=95)
        
        # Assign to DB
        p.image.name = f"products/{file_name}"
        p.save()
        count += 1
        
    print(f"Successfully generated and assigned {count} images.")

if __name__ == '__main__':
    generate_local_images()
