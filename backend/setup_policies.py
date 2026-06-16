"""Push policy content to Shopify's built-in legal policy fields (shown at checkout)."""
import os
import sys

import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE = os.environ["SHOPIFY_STORE"]
H = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"],
     "Content-Type": "application/json"}
GQL = f"https://{STORE}/admin/api/2025-01/graphql.json"
PAGES = os.path.join(os.path.dirname(__file__), "pages")


def load(fname):
    with open(os.path.join(PAGES, fname), encoding="utf-8") as f:
        body = f.read()
    if body.startswith("<!--title:"):
        _, body = body.split("\n", 1)
    return body.strip()


POLICIES = {
    "REFUND_POLICY":       load("return-policy.html"),
    "PRIVACY_POLICY":      load("privacy-policy.html"),
    "TERMS_OF_SERVICE":    load("terms-and-conditions.html"),
    "SHIPPING_POLICY":     load("shipping-policy.html"),
}

MUT = """
mutation shopPolicyUpdate($type: ShopPolicyType!, $body: String!) {
  shopPolicyUpdate(shopPolicy: {type: $type, body: $body}) {
    shopPolicy { type title url }
    userErrors { field message }
  }
}"""


def gql(query, variables):
    r = httpx.post(GQL, headers=H, json={"query": query, "variables": variables},
                   timeout=30)
    return r.json()


for ptype, body in POLICIES.items():
    res = gql(MUT, {"type": ptype, "body": body})
    node = res.get("data", {}).get("shopPolicyUpdate", {})
    errs = node.get("userErrors") or res.get("errors")
    if errs:
        print(f"{ptype}: ERROR {errs}")
    else:
        p = node.get("shopPolicy", {})
        print(f"{ptype}: OK -> {p.get('url')}")
