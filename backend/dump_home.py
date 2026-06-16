import httpx, sys, time
sys.stdout.reconfigure(encoding="utf-8")
r=httpx.get(f"https://thematchatee.com/?cb={int(time.time())}",timeout=30,
            headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
html=r.text
print("== HEADERS ==")
for k,v in r.headers.items():
    print(f"  {k}: {v}")
print(f"\n== size {len(html)} ==")
print("contains 'powered by shopify password':", "password" in html.lower())
print("contains 'Diese Website':", "Diese Website" in html)
print("contains 'content-for-layout':", "content-for-layout" in html)
print("contains 'shopify-section':", "shopify-section" in html)
i=html.rfind("</body>")
print("\n== last 1800 chars before/around </body> ==")
print(html[max(0,i-1800):i+20] if i>=0 else "NO </body> FOUND -- tail:\n"+html[-1800:])
