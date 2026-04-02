import os

def build_keyword_script(sitemap_url, search_text, path_filter, out_json):
    # Ensure paths work on Windows
    out_json = out_json.replace("\\", "/")
    return f"""
import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urlparse
import json
import advertools as adv

class KWSpider(scrapy.Spider):
    name = 'kw_spider'
    custom_settings = {{
        'LOG_LEVEL': 'ERROR',
        'CLOSESPIDER_PAGECOUNT': 500,
        'CLOSESPIDER_TIMEOUT': 300,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }}

    def __init__(self):
        parsed = urlparse("{sitemap_url}")
        self.allowed_domains = [parsed.netloc]
        self.search_text = "{search_text}".lower()
        self.path_filter = "{path_filter}"
        self.results = []
        self.sitemap_urls = set()
        try:
            df = adv.sitemap_to_df("{sitemap_url}")
            self.sitemap_urls = set(df['loc'].dropna().unique())
        except: pass

    def start_requests(self):
        homepage = "{sitemap_url}".replace('sitemap.xml', '')
        yield scrapy.Request(homepage, callback=self.parse_page)
        for u in self.sitemap_urls:
            yield scrapy.Request(u, callback=self.parse_page)

    def parse_page(self, response):
        kw_found = self.search_text in response.text.lower() if response.status == 200 else False
        self.results.append({{'URL': response.url, 'Status': response.status, 'Keyword_Found': kw_found}})
        
    def closed(self, reason):
        with open("{out_json}", "w") as f:
            json.dump({{'results': self.results, 'sitemap': list(self.sitemap_urls)}}, f)

process = CrawlerProcess()
process.crawl(KWSpider)
process.start()
"""
def build_redirect_script(sitemap_url, path_filter, out_json):
    """
    Generates a Scrapy spider script specifically for tracing redirect chains.
    """
    # Ensure Windows paths don't break the string
    out_json = out_json.replace("\\", "/")
    
    return f"""
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerProcess
import advertools as adv
from urllib.parse import urlparse
import json

class RedirectSpider(scrapy.Spider):
    name = 'redirect_spider'
    custom_settings = {{
        'USER_AGENT': 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko)',
        'DOWNLOAD_DELAY': 0.2,
        'LOG_LEVEL': 'ERROR',
        'REDIRECT_ENABLED': False,  # We disable this to manually trace the hops
        'HTTPERROR_ALLOWED_CODES': [301, 302, 307, 308, 404],
        'RETRY_TIMES': 1,
    }}

    def __init__(self):
        parsed = urlparse("{sitemap_url}")
        self.domain = parsed.netloc
        self.allowed_domains = [self.domain]
        self.base_folder = parsed.path.replace('sitemap.xml', '')
        self.path_filter = "{path_filter}"
        self.results = []
        self.visited = set()

    def start_requests(self):
        parsed = urlparse("{sitemap_url}")
        hp = f"{{parsed.scheme}}://{{self.domain}}{{self.base_folder}}"
        yield scrapy.Request(hp, callback=self.trace, meta={{'path': [hp]}})

    def trace(self, response):
        path = response.meta.get('path', [])
        
        # Avoid infinite loops on the same URL
        if response.url in self.visited and response.status == 200:
            return
        self.visited.add(response.url)

        # 1. HANDLE REDIRECTS (3xx)
        if response.status in [301, 302, 307, 308]:
            loc = response.headers.get('Location', b'').decode('utf-8')
            
            # Fix relative URLs
            if loc.startswith('/'):
                parsed = urlparse(response.url)
                loc = f"{{parsed.scheme}}://{{self.domain}}{{loc}}"
            
            # Loop Detection
            if loc in path:
                self.results.append({{
                    'URL': path[0], 
                    'Status': 'LOOP', 
                    'Final_Dest': loc, 
                    'Chain': ' -> '.join(path) + f' -> {{loc}}'
                }})
                return
            
            # Follow the next hop
            yield scrapy.Request(loc, callback=self.trace, meta={{'path': path + [loc]}})
            return

        # 2. HANDLE FINAL DESTINATION (200, 404, etc.)
        self.results.append({{
            'URL': path[0], 
            'Status': response.status, 
            'Final_Dest': response.url if len(path) > 1 else 'Direct', 
            'Chain': ' -> '.join(path) if len(path) > 1 else 'None'
        }})

        # 3. CRAWL NEXT LINKS (If it's a 200 OK page)
        if response.status == 200:
            fp = self.path_filter if self.path_filter else self.base_folder
            for link in LinkExtractor(allow=fp).extract_links(response):
                if link.url not in self.visited:
                    yield scrapy.Request(link.url, callback=self.trace, meta={{'path': [link.url]}})

    def closed(self, reason):
        with open("{out_json}", "w") as f:
            json.dump({{'results': self.results}}, f)

process = CrawlerProcess()
process.crawl(RedirectSpider)
process.start()
"""


def build_sitemap_script(sitemap_url, out_json):
    out_json = out_json.replace("\\", "/")
    return f"""
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerProcess
import advertools as adv
from urllib.parse import urlparse
import json

class SitemapSpider(scrapy.Spider):
    name = 'sitemap_spider'
    custom_settings = {{
        'USER_AGENT': 'Mozilla/5.0 AppleWebKit/537.36',
        'DOWNLOAD_DELAY': 0.2,
        'LOG_LEVEL': 'ERROR',
        'ROBOTSTXT_OBEY': False,
    }}

    def __init__(self):
        parsed = urlparse("{sitemap_url}")
        self.allowed_domains = [parsed.netloc]
        self.start_url = "{sitemap_url}".replace('sitemap.xml', '')
        self.folder_path = parsed.path.replace('sitemap.xml', '')
        self.live_urls = []
        self.sitemap_urls = []
        self.visited = set()
        
        # Pull Official Sitemap URLs immediately
        try:
            df = adv.sitemap_to_df("{sitemap_url}")
            self.sitemap_urls = df['loc'].dropna().unique().tolist()
        except: 
            pass

    def start_requests(self):
        yield scrapy.Request(self.start_url, callback=self.parse_item)

    def parse_item(self, response):
        if response.url in self.visited:
            return
        self.visited.add(response.url)
        
        if response.status == 200:
            self.live_urls.append(response.url)
            
            # Extract and follow links recursively to find all live pages
            le = LinkExtractor(allow=self.folder_path)
            for link in le.extract_links(response):
                if link.url not in self.visited:
                    yield scrapy.Request(link.url, callback=self.parse_item)

    def closed(self, reason):
        with open("{out_json}", "w") as f:
            json.dump({{'live': list(set(self.live_urls)), 'sitemap': self.sitemap_urls}}, f)

process = CrawlerProcess()
process.crawl(SitemapSpider)
process.start()
"""

