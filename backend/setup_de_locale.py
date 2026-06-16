"""
Enable German (de) locale on the storefront.
Requires scope: write_locales
Run AFTER adding write_locales scope to the custom app and reinstalling.
After this, German routes like /de/products/... work in the theme.
"""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
GQL = f"https://{STORE}/admin/api/2025-01/graphql.json"

def gql(q, v=None):
    r = httpx.post(GQL, headers=H, json={"query": q, "variables": v or {}}, timeout=15)
    d = r.json()
    if "errors" in d:
        for e in d["errors"]: print(f"  GQL error: {e['message'][:120]}")
    return d

# Check current locales
chk = gql("{ shopLocales { locale name published } }")
if not chk.get("data"):
    print("ERROR: read_locales scope missing. Add read_locales + write_locales, reinstall, re-run.")
    sys.exit(1)

locales = chk["data"]["shopLocales"]
print("Current locales:")
for loc in locales:
    print(f"  {loc['locale']} — {loc['name']} (published={loc['published']})")

de = next((l for l in locales if l["locale"] == "de"), None)
if de:
    print("\nGerman locale already exists.")
    if not de["published"]:
        print("Locale exists but not published. Publishing...")
        res = gql("""mutation { shopLocaleUpdate(locale: "de", shopLocale: {published: true}) {
            shopLocale { locale published } userErrors { field message } } }""")
        su = res.get("data",{}).get("shopLocaleUpdate",{})
        if su.get("userErrors"):
            print(f"  ERROR: {su['userErrors']}")
        else:
            print(f"  OK — German published: {su['shopLocale']['published']}")
    sys.exit(0)

# Enable German
print("\nEnabling German locale...")
res = gql("""mutation { shopLocaleEnable(locale: "de") {
    shopLocale { locale name published }
    userErrors { field message }
} }""")
sle = res.get("data",{}).get("shopLocaleEnable",{})
if sle.get("userErrors"):
    print(f"ERROR: {sle['userErrors']}")
    sys.exit(1)

sl = sle.get("shopLocale",{})
print(f"OK — German enabled: locale={sl.get('locale')} name={sl.get('name')} published={sl.get('published')}")
print("""
German locale is now active.

Next:
  • Install 'Translate & Adapt' from Shopify App Store (free)
  • It auto-translates product titles, descriptions, and storefront text to German
  • German visitors who click 'Auf Deutsch wechseln' will see fully translated pages
  • Combined with the Germany market (EUR prices), German visitors get a localised experience
""")
