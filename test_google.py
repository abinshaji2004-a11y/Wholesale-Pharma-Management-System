import urllib.request
import re

url = 'https://www.google.com/search?q=Zincovit+Capsule+medicine+box&tbm=isch'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    images = re.findall(r'<img.*?src=\"(https://encrypted-tbn0\.gstatic\.com/images.*?)\"', html)
    print(images[:3] if images else 'no images')
except Exception as e:
    print('Error:', e)
