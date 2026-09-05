import json
import urllib.request
import urllib.parse
import re
import time
import ssl
import sys
import os

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

core_models = {
    "Centrifugal 1 HP": {"لئو": "ACm75", "گرین": "CM100", "ابارا": "CMA 1.00", "شیمجه": "CPm158", "تایفو": "TCP158"},
    "Centrifugal 1.5 HP": {"لئو": "ACm110", "ابارا": "CMA 1.50", "شیمجه": "CPm170", "گرین": "CM150"},
    "Peripheral 0.5 HP": {"لئو": "APm37", "گرین": "PM45", "ابارا": "PRA 0.50", "شیمجه": "QB60", "تایفو": "QB60"},
    "Peripheral 1 HP": {"لئو": "APm75", "گرین": "PM80", "ابارا": "PRA 1.00", "شیمجه": "QB80", "تایفو": "QB80"},
    "Jet 1 HP": {"لئو": "AJm75", "گرین": "JET100", "ابارا": "AGA 1.00", "شیمجه": "SGJW75", "تایفو": "JET100"},
    "Jet 1.5 HP": {"لئو": "AJm110", "ابارا": "AGA 1.50"},
    "Twin Impeller 1 HP": {"لئو": "2ACm75", "ابارا": "CDA 1.00", "گرین": "CB100"},
    "Twin Impeller 1.5 HP": {"لئو": "2ACm110", "ابارا": "CDA 1.50", "گرین": "CB160"},
    "Twin Impeller 2 HP": {"لئو": "2ACm150", "ابارا": "CDA 2.00", "گرین": "CB210"},
    "Inverter 0.5 kW": {"لئو": "MAC550", "شیمجه": "CA600"},
    "Pool 2 HP": {"لئو": "XKP1504", "ابارا": "SWS 200"},
    "Pool 3 HP": {"لئو": "XKP2204", "ابارا": "SWS 300"},
    "Sump 1inch 16m": {"لئو": "XQS", "شیمجه": "QDX1.5-17", "ابارا": "Right"},
    "Sewage 2inch 15m": {"لئو": "XSP", "شیمجه": "WQD", "ابارا": "DW"}
}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def clean_price(text):
    text = text.replace('تومان', '').replace('٫', '').replace(',', '').strip()
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    trans_table = str.maketrans(persian_digits, english_digits)
    text = text.translate(trans_table)
    text = re.sub(r'[^0-9]', '', text)
    if not text: return 0
    return int(text)

def search_torob(brand, model):
    query = f"پمپ {brand} {model}"
    url = "https://torob.com/search/?query=" + urllib.parse.quote(query)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            html = response.read().decode('utf-8')
            pattern = r'<a[^>]*href="(/p/[^"]+)"[^>]*>.*?product-name__[^"]*".*?>(.*?)</h2>.*?product-price-text__[^"]*">(.*?)</div>'
            matches = re.findall(pattern, html, re.DOTALL)
            for link, title, price_text in matches:
                title_clean = title.strip().lower()
                if "پمپ" in title_clean and brand.lower() in title_clean and model.lower().split()[0] in title_clean.replace('-', ''):
                    return {"model": model, "price": clean_price(price_text.strip()), "url": f"https://torob.com{link}"}
    except Exception as e:
        print(f"Torob error {brand} {model}: {e}")
    return None

def fetch_sitemap_urls():
    try:
        req = urllib.request.Request("https://pumpfa.com/product-sitemap.xml", headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            xml_data = response.read().decode('utf-8')
            return re.findall(r'<loc>(.*?)</loc>', xml_data)
    except Exception as e:
        print("Sitemap error:", e)
        return []

def get_product_details(url):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            html = response.read().decode('utf-8')
            title = ""
            if HAS_BS4:
                soup = BeautifulSoup(html, 'html.parser')
                h1 = soup.find('h1', class_='product_title')
                if h1: title = h1.text.strip()
            else:
                m = re.search(r'<h1[^>]*class="[^"]*product_title[^"]*"[^>]*>(.*?)</h1>', html)
                if m: title = m.group(1).strip()
            
            if not title:
                m = re.search(r'<title>(.*?)</title>', html)
                if m: title = m.group(1).split('-')[0].strip()

            brand = "Happy" if "هپی" in title or "-happy-" in url or "happy-" in url else "Other"
            
            eng_name = ""
            for part in url.split('/')[-2].split('-'):
                if re.search(r'[A-Za-z]', part) and re.search(r'[0-9]', part):
                    eng_name = part.upper()
                    break
            
            if not eng_name:
                m = re.search(r'مدل\s*([A-Za-z0-9/\-]+)', title)
                if m: eng_name = m.group(1)
            
            return {
                "نام محصول": title,
                "نام برند": "Happy" if brand == "Happy" else "متفرقه",
                "لینک صفحات خارجی": url,
                "نام انگلیسی محصول": eng_name
            }
    except Exception as e:
        print(f"Product page error {url}: {e}")
        return None

def main():
    print("1. Checking Sitemap...")
    sitemap_urls = fetch_sitemap_urls()
    
    products = []
    if os.path.exists('products.json'):
        try:
            with open('products.json', 'r', encoding='utf-8') as f:
                products = json.load(f)
        except: pass
            
    existing_urls = {p.get("لینک صفحات خارجی", "") for p in products}
    max_id = max([int(p.get("ID محصول", 0)) for p in products if str(p.get("ID محصول", "")).isdigit()], default=5000)
    
    new_count = 0
    for url in sitemap_urls:
        if url and url not in existing_urls and ("happy" in url.lower() or "هپی" in urllib.parse.unquote(url)):
            print(f"Found new product: {url}")
            details = get_product_details(url)
            if details and details["نام برند"] == "Happy":
                max_id += 1
                details["ID محصول"] = str(max_id)
                details["usd_price"] = 0 
                details["نوع پمپ"] = ""
                products.append(details)
                new_count += 1
                
    if new_count > 0:
        with open('products.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"Added {new_count} new products from sitemap!")
    else:
        print("No new Happy products found in sitemap.")

    print("\n2. Scraping Torob Market Data...")
    accurate_data = {}
    if os.path.exists('market_data.json'):
        try:
            with open('market_data.json', 'r', encoding='utf-8') as f:
                accurate_data = json.load(f)
        except: pass

    for core, brands in core_models.items():
        if core not in accurate_data:
            accurate_data[core] = {}
        for brand, model in brands.items():
            print(f" Fetching {brand} {model}...")
            res = search_torob(brand, model)
            if res and res["price"] > 1000:
                accurate_data[core][brand] = res
            time.sleep(1.5)

    with open('market_data.json', 'w', encoding='utf-8') as f:
        json.dump(accurate_data, f, ensure_ascii=False, indent=2)
    print("Market Data updated!")

if __name__ == '__main__':
    main()
