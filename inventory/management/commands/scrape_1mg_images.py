import urllib.request
import urllib.parse
import os
import time
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from inventory.models import Product

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        products = Product.objects.all()
        total = products.count()
        self.stdout.write(f"Scraping real images from 1mg for {total} products...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        for idx, product in enumerate(products, 1):
            name = product.name
            
            # Search URL on DuckDuckGo HTML version to get 1mg link
            query = f"site:1mg.com {name}"
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            try:
                # 1. Get DuckDuckGo Search Results
                req = urllib.request.Request(search_url, headers=headers)
                html = urllib.request.urlopen(req).read().decode('utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find the first 1mg link
                result_link = soup.find('a', class_='result__url', href=lambda href: href and '1mg.com' in href)
                
                if result_link:
                    actual_url = result_link['href']
                    if actual_url.startswith('//'):
                        actual_url = 'https:' + actual_url
                    
                    # 2. Scrape the 1mg Product Page
                    req_1mg = urllib.request.Request(actual_url, headers=headers)
                    html_1mg = urllib.request.urlopen(req_1mg).read().decode('utf-8')
                    soup_1mg = BeautifulSoup(html_1mg, 'html.parser')
                    
                    # Try to find the main image
                    img_tag = soup_1mg.find('img', class_='style__image___Ny-Sa') or soup_1mg.find('img', alt=lambda alt: alt and name.lower() in alt.lower())
                    
                    if img_tag and img_tag.get('src'):
                        img_url = img_tag['src']
                        
                        # 3. Download the Image
                        req_img = urllib.request.Request(img_url, headers=headers)
                        img_data = urllib.request.urlopen(req_img).read()
                        
                        safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                        file_name = f"{safe_name.replace(' ', '_')}_{product.id}_real.jpg"
                        out_path = os.path.join('media', 'products', file_name)
                        
                        with open(out_path, 'wb') as f:
                            f.write(img_data)
                            
                        product.image.name = f"products/{file_name}"
                        product.save()
                        self.stdout.write(f"[{idx}/{total}] Downloaded real image for {name}")
                    else:
                        self.stdout.write(f"[{idx}/{total}] No image found on 1mg for {name}")
                else:
                    self.stdout.write(f"[{idx}/{total}] No 1mg link found for {name}")
                
                time.sleep(3) # Prevent rate limiting
                
            except Exception as e:
                self.stdout.write(f"Error on {name}: {e}")
                
        self.stdout.write("Finished scraping real images!")
