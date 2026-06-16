import os, httpx, sys
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv()
S = os.environ["SHOPIFY_STORE"]; T = os.environ["SHOPIFY_TOKEN"]
H = {"X-Shopify-Access-Token": T}
A = f"https://{S}/admin/api/2025-01"
DOMAIN = "https://thematchatee.com"

r = httpx.get(f"{A}/blogs/91457585265/articles.json?limit=250&fields=id,title,handle,published_at,image",
              headers=H, timeout=20)
arts = r.json()["articles"]
arts.sort(key=lambda a: a.get("published_at") or "")
for i, a in enumerate(arts):
    img = "IMG" if a.get("image") else "---"
    print(f"{i+1:2d}. [{img}] {a['title']}")
    print(f"     {DOMAIN}/blogs/style-guide/{a['handle']}")
print(f"\nTotal published: {len(arts)}")
