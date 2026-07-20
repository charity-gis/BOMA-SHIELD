import urllib.request
import re

def search_url(url, depth=0):
    if depth > 2:
        return
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8', errors='ignore')
        hrefs = re.findall(r'href=["\']([^"\']+/?)["\']', html)
        for h in hrefs:
            if h.startswith('?') or h.startswith('/') or h.startswith('.'):
                continue
            full = url + h
            if any(k in h.lower() for k in ['ndvi', 'emodis', 'modis', 'viirs', 'veg', 'wcs']):
                print(f"[FOUND MATCH] Depth {depth}: {full}")
            if h.endswith('/') and depth < 2:
                search_url(full, depth + 1)
    except Exception as e:
        pass

print("Searching CHC for NDVI/eMODIS/MODIS/VIIRS directories...")
search_url('https://data.chc.ucsb.edu/products/')







