"""
Create US (USD) + Germany (EUR) markets with fixed prices per size tier.
Requires scopes: read_markets, write_markets, read_products
Run AFTER adding these scopes to the Shopify custom app and reinstalling.
"""
import os, sys, re, time, json
import httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
RH = {"X-Shopify-Access-Token": TOKEN}
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"
GQL = f"https://{STORE}/admin/api/2025-01/graphql.json"

def gql(q, v=None):
    r = httpx.post(GQL, headers=H, json={"query": q, "variables": v or {}}, timeout=30)
    d = r.json()
    if "errors" in d:
        for e in d["errors"]: print(f"GQL error: {e['message'][:120]}")
    return d

# ── size tier detection (matches update_prices_by_size.py) ───────────────────
def size_tier(option_val):
    s = (option_val or "").upper().replace(" ", "").replace("-", "")
    if re.search(r'5XL|XXXXXL', s): return "5xl"
    if re.search(r'4XL|XXXXL',  s): return "4xl"
    if re.search(r'3XL|XXXL',   s): return "3xl"
    if re.search(r'2XL|XXL',    s): return "2xl"
    return "base"

def categorize(title, ptype):
    t = title.lower(); p = (ptype or "").lower()
    if any(k in t or k in p for k in ["kid", "youth", "child", "toddler"]):
        return "kids"
    if any(k in t or k in p for k in ["hoodie", "hoody", "sweatshirt", "crewneck", "pullover"]):
        return "hoodie"
    return "tee"

# ── price tables ──────────────────────────────────────────────────────────────
# Based on actual POD costs from the cost chart + competitive UK/US/DE market rates
# US: competitive with US POD vintage tee market ($35-55 range)
# DE: competitive with EU market (€32-52 range)
US_PRICES = {
    "tee":    {"base": ("34.99","44.99"), "2xl": ("34.99","44.99"),
               "3xl": ("36.99","47.99"), "4xl": ("36.99","47.99"), "5xl": ("36.99","47.99")},
    "hoodie": {"base": ("47.99","61.99"), "2xl": ("51.99","67.99"),
               "3xl": ("53.99","69.99"), "4xl": ("55.99","72.99"), "5xl": ("55.99","72.99")},
    "kids":   {"base": ("27.99","35.99"), "2xl": ("27.99","35.99"),
               "3xl": ("27.99","35.99"), "4xl": ("27.99","35.99"), "5xl": ("27.99","35.99")},
}
DE_PRICES = {
    "tee":    {"base": ("31.99","41.99"), "2xl": ("31.99","41.99"),
               "3xl": ("33.99","43.99"), "4xl": ("33.99","43.99"), "5xl": ("33.99","43.99")},
    "hoodie": {"base": ("43.99","57.99"), "2xl": ("46.99","61.99"),
               "3xl": ("48.99","63.99"), "4xl": ("50.99","65.99"), "5xl": ("50.99","65.99")},
    "kids":   {"base": ("25.99","33.99"), "2xl": ("25.99","33.99"),
               "3xl": ("25.99","33.99"), "4xl": ("25.99","33.99"), "5xl": ("25.99","33.99")},
}

MARKETS_CFG = [
    {"name": "United States", "handle": "united-states",
     "country": "US", "currency": "USD", "prices": US_PRICES},
    {"name": "Germany",       "handle": "germany",
     "country": "DE", "currency": "EUR", "prices": DE_PRICES},
]

# ── scope check ───────────────────────────────────────────────────────────────
chk = gql("{ markets(first:1) { edges { node { id } } } }")
if not chk.get("data"):
    print("\nERROR: read_markets scope missing.")
    print("Add 'read_markets' + 'write_markets' to your custom app, reinstall, update .env token, re-run.")
    sys.exit(1)

# ── fetch all products + variants ─────────────────────────────────────────────
products = []
url = f"{API}/products.json?limit=250"
while url:
    r = httpx.get(url, headers=RH, timeout=30)
    products.extend(r.json()["products"])
    link = r.headers.get("Link","")
    url = None
    for part in link.split(","):
        if 'rel="next"' in part: url = part.strip().split(";")[0].strip("<> ")
print(f"Fetched {len(products)} products, building variant map...")

# Map variant_id → (category, size_tier)
variant_map = {}
for p in products:
    cat = categorize(p["title"], p.get("product_type",""))
    for v in p["variants"]:
        tier = size_tier(v.get("option1",""))
        variant_map[f"gid://shopify/ProductVariant/{v['id']}"] = (cat, tier)
print(f"  {len(variant_map)} variants indexed\n")

# ── create / find markets and set prices ──────────────────────────────────────
MARKET_CREATE = """mutation mc($input: MarketCreateInput!) {
  marketCreate(input: $input) {
    market { id name }
    userErrors { field message }
  }
}"""

MARKET_QUERY = """{ markets(first: 20) {
  edges { node { id name handle
    catalogs(first:1) { edges { node {
      id ... on MarketCatalog { priceList { id currency } }
    } } }
  } }
} }"""

PRICES_ADD = """mutation pa($plId: ID!, $prices: [PriceListPriceInput!]!) {
  priceListFixedPricesAdd(priceListId: $plId, prices: $prices) {
    prices { variant { id } price { amount currencyCode } }
    userErrors { field message }
  }
}"""

PRICELIST_CREATE = """mutation plc($input: PriceListCreateInput!) {
  priceListCreate(input: $input) {
    priceList { id name currency }
    userErrors { field message }
  }
}"""

for cfg in MARKETS_CFG:
    print(f"═══ {cfg['name']} ({cfg['currency']}) ═══")

    # find existing market
    existing = gql(MARKET_QUERY)
    markets_list = existing.get("data",{}).get("markets",{}).get("edges",[])
    market_node = next(
        (e["node"] for e in markets_list if e["node"]["handle"] == cfg["handle"]),
        None
    )

    if market_node:
        print(f"  Found existing market id={market_node['id']}")
    else:
        # create market
        result = gql(MARKET_CREATE, {"input": {
            "name":   cfg["name"],
            "handle": cfg["handle"],
            "conditions": {
                "regionsCondition": {
                    "regions": [{"countryCode": cfg["country"]}]
                }
            },
            "currencySettings": {
                "baseCurrency": cfg["currency"],
                "localCurrencies": False,
                "roundingEnabled": True
            },
            "status": "ACTIVE"
        }})
        mc = result.get("data",{}).get("marketCreate",{})
        if mc.get("userErrors"):
            print(f"  CREATE ERROR: {mc['userErrors']}")
            continue
        market_node = mc["market"]
        print(f"  Created market id={market_node['id']}")
        time.sleep(1)

        # re-query to get catalog
        existing = gql(MARKET_QUERY)
        markets_list = existing.get("data",{}).get("markets",{}).get("edges",[])
        market_node = next(
            (e["node"] for e in markets_list if e["node"]["handle"] == cfg["handle"]),
            market_node
        )

    # get price list id from market's catalog
    catalog_edges = market_node.get("catalogs",{}).get("edges",[])
    price_list_id = None
    for ce in catalog_edges:
        node = ce["node"]
        pl = node.get("priceList")
        if pl and pl.get("currency") == cfg["currency"]:
            price_list_id = pl["id"]
            print(f"  Using existing price list id={price_list_id}")
            break

    if not price_list_id:
        # try first catalog regardless of currency
        for ce in catalog_edges:
            pl = ce["node"].get("priceList")
            if pl:
                price_list_id = pl["id"]
                print(f"  Using catalog price list id={price_list_id} (currency={pl.get('currency')})")
                break

    if not price_list_id:
        # create a standalone price list and link to catalog
        print(f"  No price list found — creating one for {cfg['currency']}...")
        catalog_id = catalog_edges[0]["node"]["id"] if catalog_edges else None
        pl_input = {
            "name": f"{cfg['name']} Prices",
            "currency": cfg["currency"],
            "parent": {"adjustment": {"value": 0.0, "type": "PERCENTAGE_DECREASE"}},
        }
        if catalog_id:
            pl_input["catalogId"] = catalog_id
        plr = gql(PRICELIST_CREATE, {"input": pl_input})
        plc = plr.get("data",{}).get("priceListCreate",{})
        if plc.get("userErrors"):
            print(f"  PRICELIST ERROR: {plc['userErrors']}")
            continue
        price_list_id = plc["priceList"]["id"]
        print(f"  Created price list id={price_list_id}")

    # build prices payload in batches of 100
    prices_payload = []
    for variant_gid, (cat, tier) in variant_map.items():
        price, compare = cfg["prices"][cat][tier]
        prices_payload.append({
            "variantId": variant_gid,
            "price": {"amount": price, "currencyCode": cfg["currency"]},
            "compareAtPrice": {"amount": compare, "currencyCode": cfg["currency"]},
        })

    total = len(prices_payload)
    ok = 0
    for i in range(0, total, 100):
        batch = prices_payload[i:i+100]
        res = gql(PRICES_ADD, {"plId": price_list_id, "prices": batch})
        pla = res.get("data",{}).get("priceListFixedPricesAdd",{})
        errs = pla.get("userErrors",[])
        if errs:
            print(f"  Batch {i//100+1} ERRORS: {errs}")
        else:
            ok += len(pla.get("prices",[]))
        print(f"  Prices set: {min(i+100, total)}/{total}", end="\r")
        time.sleep(0.3)

    print(f"\n  OK — {ok} variant prices set in {cfg['currency']}          ")
    time.sleep(0.5)

print("\n══ DONE ══")
print("US visitors see USD prices, German visitors see EUR prices automatically.")
print("No action needed for existing UK/GBP prices — primary market unchanged.")
