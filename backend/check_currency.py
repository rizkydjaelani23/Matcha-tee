import httpx, sys, time
sys.stdout.reconfigure(encoding="utf-8")

def probe(url):
    r = httpx.get(url, timeout=30, headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    html = r.text
    print(f"\n=== {url}")
    print(f"  status={r.status_code}  size={len(html)}")
    for h in ["age","cache-control","x-cache","cf-cache-status","date"]:
        if h in r.headers: print(f"  {h}: {r.headers[h]}")
    print(f"  'tmt-' occurrences: {html.count('tmt-')}")
    for m in ["tmt-ccy-badge","tmt-currency","tmt-de-bar","get.geojs.io"]:
        print(f"    {'FOUND  ' if m in html else 'missing'}  {m}")

cb = int(time.time())
probe(f"https://thematchatee.com/?nocache={cb}")
probe(f"https://thematchatee.com/products/da-vinci-retro-shirt?nocache={cb}")
