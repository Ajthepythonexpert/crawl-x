import requests
import re
from urllib.parse import urlparse

def is_garbage_link(url):
    IGNORE_KEYWORDS = ["icon", "logo", "font", "sprite", "badge", "btn", "button", "mstile", "android", "apple", "favicon", "manifest", "loader", "spinner", ".svg"]
    url_lower = url.lower()
    if url_lower.startswith("data:"): return True
    for kw in IGNORE_KEYWORDS:
        if kw in url_lower: return True
    return False

def check_asset_health(url, session):
    try:
        r = session.head(url, timeout=10, allow_redirects=True)
        if r.status_code == 404: return True, "404 NOT FOUND"
        if r.status_code >= 400: return True, f"STATUS {r.status_code}"
        return False, "OK"
    except: return False, "TIMEOUT/ERROR"

def get_image_details(img_url, session):
    try:
        res = session.head(img_url, timeout=5)
        size_bytes = int(res.headers.get('Content-Length', 0))
        size_kb = size_bytes / 1024
        dim_match = re.search(r'(\d{2,4})x(\d{2,4})', img_url)
        res_str = f"{dim_match.group(1)}x{dim_match.group(2)}" if dim_match else "Unknown"
        return size_kb, res_str
    except:
        return 0, "N/A"