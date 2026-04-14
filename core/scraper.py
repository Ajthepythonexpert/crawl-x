import json

# ✅ KEYWORD SEARCH
def build_keyword_script(sitemap_url, search_text, path_filter, out_json):
    sitemap_url = json.dumps(sitemap_url)
    search_text = json.dumps(search_text.lower())
    out_json = out_json.replace("\\", "/")

    return f"""
import requests
import json
import advertools as adv

results = []
sitemap_urls = []

try:
    df = adv.sitemap_to_df({sitemap_url})
    if 'loc' in df.columns:
        sitemap_urls = df['loc'].dropna().tolist()
except Exception as e:
    print(e)

for url in sitemap_urls[:300]:
    try:
        r = requests.get(url, timeout=10)
        text = r.text.lower() if r.status_code == 200 else ""
        results.append({{
            "URL": url,
            "Status": r.status_code,
            "Keyword_Found": {search_text} in text
        }})
    except:
        results.append({{
            "URL": url,
            "Status": "ERROR",
            "Keyword_Found": False
        }})

with open("{out_json}", "w") as f:
    json.dump({{"results": results, "sitemap": sitemap_urls}}, f)
"""

# ✅ REDIRECT CHECK
def build_redirect_script(sitemap_url, path_filter, out_json):
    sitemap_url = json.dumps(sitemap_url)
    out_json = out_json.replace("\\", "/")

    return f"""
import requests
import json
import advertools as adv

results = []

try:
    df = adv.sitemap_to_df({sitemap_url})
    urls = df['loc'].dropna().tolist() if 'loc' in df.columns else []
except:
    urls = []

for url in urls[:200]:
    chain = []
    current = url

    try:
        for _ in range(5):
            r = requests.get(current, allow_redirects=False, timeout=10)
            chain.append(current)

            if r.status_code in [301,302,307,308]:
                nxt = r.headers.get("Location")
                if not nxt or nxt in chain:
                    break
                current = nxt
            else:
                break

        results.append({{
            "URL": url,
            "Final_Dest": current,
            "Status": r.status_code,
            "Chain": " -> ".join(chain)
        }})

    except:
        results.append({{
            "URL": url,
            "Final_Dest": "ERROR",
            "Status": "ERROR",
            "Chain": ""
        }})

with open("{out_json}", "w") as f:
    json.dump({{"results": results}}, f)
"""

# ✅ SITEMAP CHECK
def build_sitemap_script(sitemap_url, out_json):
    sitemap_url = json.dumps(sitemap_url)
    out_json = out_json.replace("\\", "/")

    return f"""
import requests
import json
import advertools as adv

live_urls = []
sitemap_urls = []

try:
    df = adv.sitemap_to_df({sitemap_url})
    if 'loc' in df.columns:
        sitemap_urls = df['loc'].dropna().tolist()
except:
    pass

for url in sitemap_urls[:300]:
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            live_urls.append(url)
    except:
        pass

with open("{out_json}", "w") as f:
    json.dump({{"live": live_urls, "sitemap": sitemap_urls}}, f)
"""
