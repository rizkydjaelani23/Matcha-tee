import httpx, sys, re, time
sys.stdout.reconfigure(encoding="utf-8")

def probe(url):
    cb = f"{url}{'&' if '?' in url else '?'}nocache={int(time.time())}"
    r = httpx.get(cb, timeout=30, follow_redirects=True,
                  headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    html = r.text
    lang = re.search(r'<html[^>]*\blang="([^"]+)"', html)
    print(f"\n=== {url}")
    print(f"  status={r.status_code}  final={r.url}")
    print(f"  <html lang>: {lang.group(1) if lang else '?'}")
    # hreflang alternate tags Shopify adds for published locales
    hrefs = re.findall(r'hreflang="([^"]+)"', html)
    print(f"  hreflang tags: {sorted(set(hrefs))}")
    # look for any German UI words that would only appear if translated
    de_words = [w for w in ["Warenkorb","In den Warenkorb","Suchen","Startseite","Menü","Kasse"] if w in html]
    print(f"  German UI words found: {de_words or 'none'}")

probe("https://thematchatee.com/")
probe("https://thematchatee.com/de")
probe("https://thematchatee.com/de/products/da-vinci-retro-shirt")
