import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
res = requests.get('https://www.netmeds.com/catalogsearch/result/dolo%20650/all', headers=headers)
print('Netmeds status:', res.status_code)

match = re.search(r'https://www\.netmeds\.com/images/product-v1/[^"]+', res.text)
if match:
    print(match.group(0))
else:
    print("No image found")
