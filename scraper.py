import json
import urllib.request
import urllib.parse
import re
import time
import ssl
import sys
import os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

core_models = {
    "Centrifugal 1 HP": {
        "لئو": "ACm75", "گرین": "CM100", "ابارا": "CMA 1.00", "شیمجه": "CPm158", "تایفو": "TCP158"
    },
    "Centrifugal 1.5 HP": {
        "لئو": "ACm110", "ابارا": "CMA 1.50", "شیمجه": "CPm170", "گرین": "CM150"
    },
    "Peripheral 0.5 HP": {
        "لئو": "APm37", "گرین": "PM45", "ابارا": "PRA 0.50", "شیمجه": "QB60", "تایفو": "QB60", "فنسی": "PM45"
    },
    "Peripheral 1 HP": {
        "لئو": "APm75", "گرین": "PM80", "ابارا": "PRA 1.00", "شیمجه": "QB80", "تایفو": "QB80"
    },
    "Jet 1 HP": {
        "لئو": "AJm75", "گرین": "JET100", "ابارا": "AGA 1.00", "شیمجه": "SGJW75", "تایفو": "JET100"
    },
    "Jet 1.5 HP": {
        "لئو": "AJm110", "ابارا": "AGA 1.50"
    },
    "Twin Impeller 1 HP": {
        "لئو": "2ACm75", "ابارا": "CDA 1.00", "گرین": "CB100"
    },
    "Twin Impeller 1.5 HP": {
        "لئو": "2ACm110", "ابارا": "CDA 1.50", "گرین": "CB160"
    },
    "Twin Impeller 2 HP": {
        "لئو": "2ACm150", "ابارا": "CDA 2.00", "گرین": "CB210"
    },
    "Inverter 0.5 kW": {
        "لئو": "MAC550", "شیمجه": "CA600"
    },
    "Pool 2 HP": {
        "لئو": "XKP1504", "ابارا": "SWS 200"
    },
    "Pool 3 HP": {
        "لئو": "XKP2204", "ابارا": "SWS 300"
    },
    "Sump 1inch 16m": {
        "لئو": "XQS", "شیمجه": "QDX1.5-17", "ابارا": "Right"
    },
    "Sewage 2inch 15m": {
        "لئو": "XSP", "شیمجه": "WQD", "ابارا": "DW"
    }
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fa,en-US;q=0.7,en;q=0.3'
}

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
                price_clean = clean_price(price_text.strip())
                if "پمپ" in title_clean and brand.lower() in title_clean and model.lower().split()[0] in title_clean.replace('-', ''):
                    return {"model": model, "price": price_clean, "url": f"https://torob.com{link}"}
    except Exception as e:
        print(f"Error fetching {brand} {model}: {e}")
    return None

def main():
    print("Starting market data scraping...")
    
    # In a real scenario, you could also fetch pumpfa.com/product-sitemap.xml here 
    # to find new products, but for robust pricing we rely on our exact core mappings.
    
    accurate_data = {}
    if os.path.exists('market_data.json'):
        try:
            with open('market_data.json', 'r', encoding='utf-8') as f:
                accurate_data = json.load(f)
        except:
            pass

    for core, brands in core_models.items():
        if core not in accurate_data:
            accurate_data[core] = {}
        for brand, model in brands.items():
            print(f"Fetching {brand} {model}...")
            res = search_torob(brand, model)
            if res and res["price"] > 1000:
                accurate_data[core][brand] = res
            time.sleep(2.0) # Sleep to avoid rate limits

    with open('market_data.json', 'w', encoding='utf-8') as f:
        json.dump(accurate_data, f, ensure_ascii=False, indent=2)
        
    print("Scraping completed and market_data.json updated.")

if __name__ == '__main__':
    main()
