import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'abin_pharma.settings')
django.setup()
from inventory.models import Product
from PIL import Image, ImageDraw, ImageFont

def generate_3d_box():
    products = Product.objects.all()
    count = 0
    print(f"Generating isolated 3D box images for {products.count()} products...")
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 32)
        font_sub = ImageFont.truetype("arial.ttf", 18)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    for p in products:
        # Create a pure white background
        img = Image.new('RGB', (500, 500), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Coordinates for 3D box
        # Front face
        front_x = 120
        front_y = 150
        front_w = 200
        front_h = 250
        
        # Draw top face (polygon)
        top_color = (235, 240, 245)
        top_polygon = [
            (front_x, front_y),
            (front_x + 60, front_y - 40),
            (front_x + front_w + 60, front_y - 40),
            (front_x + front_w, front_y)
        ]
        draw.polygon(top_polygon, fill=top_color, outline=(200, 205, 210))
        
        # Draw side face (polygon)
        side_color = (220, 225, 230)
        side_polygon = [
            (front_x + front_w, front_y),
            (front_x + front_w + 60, front_y - 40),
            (front_x + front_w + 60, front_y + front_h - 40),
            (front_x + front_w, front_y + front_h)
        ]
        draw.polygon(side_polygon, fill=side_color, outline=(200, 205, 210))
        
        # Draw front face
        front_color = (250, 252, 255)
        draw.rectangle(
            [(front_x, front_y), (front_x + front_w, front_y + front_h)],
            fill=front_color, outline=(200, 205, 210), width=2
        )
        
        # Draw a medical cross icon on the front face
        cross_color = (40, 167, 69) # Green
        cx = front_x + front_w // 2
        cy = front_y + 50
        draw.rectangle([(cx - 8, cy - 25), (cx + 8, cy + 25)], fill=cross_color)
        draw.rectangle([(cx - 25, cy - 8), (cx + 25, cy + 8)], fill=cross_color)
        
        # Draw Medicine Name (wrapped) on front face
        name = p.name
        words = name.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + " " + word) < 12:
                current_line += " " + word
            else:
                lines.append(current_line.strip())
                current_line = word
        if current_line:
            lines.append(current_line.strip())
            
        y_text = front_y + 100
        for line in lines:
            try:
                w = draw.textbbox((0,0), line, font=font_title)[2]
            except:
                w = draw.textsize(line, font=font_title)[0]
            
            draw.text((front_x + (front_w - w) / 2, y_text), line, fill=(30, 40, 50), font=font_title)
            y_text += 40
            
        # Draw Category / Generic
        cat = p.category.name if p.category else ""
        if len(cat) > 15:
            cat = cat[:12] + "..."
        try:
            w2 = draw.textbbox((0,0), cat, font=font_sub)[2]
        except:
            w2 = draw.textsize(cat, font=font_sub)[0]
        draw.text((front_x + (front_w - w2) / 2, y_text + 10), cat, fill=(100, 110, 120), font=font_sub)
        
        # Save image
        safe_name = "".join([c for c in p.name if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(' ', '_')
        file_name = f"box3d_{safe_name}_{p.id}.jpg"
        out_path = os.path.join('media', 'products', file_name)
        
        img.save(out_path, quality=95)
        
        # Assign to DB
        p.image.name = f"products/{file_name}"
        p.save()
        count += 1
        
    print(f"Successfully generated and assigned 3D boxes for {count} products.")

if __name__ == '__main__':
    generate_3d_box()
