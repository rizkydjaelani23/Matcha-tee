"""
1. Create blocks/tmt-payment-notice.liquid — card icons + "no PayPal account needed" note
2. Add the block to templates/product.json right after buy_buttons_eYQEYi
"""
import os, sys, json, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH    = {"X-Shopify-Access-Token": TOKEN}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

# ── 1. Payment notice block ────────────────────────────────────────────────────
BLOCK_LIQUID = r"""<div class="tmt-pay-notice">
  <div class="tmt-pay-notice__row">
    {%- render 'icon', icon: 'lock' -%}
    <span class="tmt-pay-notice__secure">Secure checkout</span>
  </div>
  <div class="tmt-pay-notice__cards">
    <span class="tmt-pay-notice__card tmt-pay-notice__card--visa">VISA</span>
    <span class="tmt-pay-notice__card tmt-pay-notice__card--mc">MC</span>
    <span class="tmt-pay-notice__card tmt-pay-notice__card--amex">AMEX</span>
    <span class="tmt-pay-notice__card tmt-pay-notice__card--pp">PayPal</span>
    <span class="tmt-pay-notice__card">Apple Pay</span>
  </div>
  <p class="tmt-pay-notice__hint">
    No PayPal account? Click <strong>PayPal</strong> &rarr; select <strong>&ldquo;Pay with Debit or Credit Card&rdquo;</strong> to pay by card directly.
  </p>
</div>

<style>
  .tmt-pay-notice {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 0 4px;
  }
  .tmt-pay-notice__row {
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .tmt-pay-notice__row .icon {
    width: 14px;
    height: 14px;
    opacity: 0.6;
  }
  .tmt-pay-notice__secure {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--color-foreground);
    opacity: 0.7;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }
  .tmt-pay-notice__cards {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    align-items: center;
  }
  .tmt-pay-notice__card {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(var(--color-foreground-rgb), 0.2);
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--color-foreground);
    background: var(--color-background);
    min-width: 38px;
    min-height: 22px;
  }
  .tmt-pay-notice__card--visa  { color: #1a1f71; }
  .tmt-pay-notice__card--mc   { color: #eb001b; }
  .tmt-pay-notice__card--amex { color: #007bc1; }
  .tmt-pay-notice__card--pp   { color: #003087; }
  .tmt-pay-notice__hint {
    font-size: 0.78rem;
    color: var(--color-foreground);
    opacity: 0.65;
    margin: 0;
    line-height: 1.5;
  }
  .tmt-pay-notice__hint strong {
    color: var(--color-foreground);
    opacity: 1;
  }
</style>

{% schema %}
{
  "name": "Payment notice",
  "tag": null,
  "settings": [],
  "presets": [{"name": "Payment notice"}]
}
{% endschema %}
"""

# ── 2. Push block file ─────────────────────────────────────────────────────────
r1 = httpx.put(
    f"{API}/themes/{THEME}/assets.json",
    headers=H,
    json={"asset": {"key": "blocks/tmt-payment-notice.liquid", "value": BLOCK_LIQUID}},
    timeout=30,
)
print(f"PUT blocks/tmt-payment-notice.liquid: {r1.status_code}")
if r1.status_code not in (200, 201):
    print(r1.text[:300])
    sys.exit(1)

# ── 3. Update templates/product.json ──────────────────────────────────────────
r2 = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
               params={"asset[key]": "templates/product.json"}, timeout=15)
pj = json.loads(r2.json()["asset"]["value"])

prod_details = pj["sections"]["main"]["blocks"]["product-details"]
block_order  = prod_details.get("block_order", [])
blocks       = prod_details.setdefault("blocks", {})

BLOCK_ID = "tmt_payment_notice"

# Remove if already present (idempotent)
block_order = [b for b in block_order if b != BLOCK_ID]
blocks.pop(BLOCK_ID, None)

# Insert right after buy_buttons_eYQEYi
buy_idx = block_order.index("buy_buttons_eYQEYi") if "buy_buttons_eYQEYi" in block_order else len(block_order) - 1
block_order.insert(buy_idx + 1, BLOCK_ID)

blocks[BLOCK_ID] = {
    "type": "tmt-payment-notice",
    "settings": {},
    "blocks": {},
}

prod_details["block_order"] = block_order
print(f"New block_order: {block_order}")

r3 = httpx.put(
    f"{API}/themes/{THEME}/assets.json",
    headers=H,
    json={"asset": {"key": "templates/product.json",
                    "value": json.dumps(pj, ensure_ascii=False)}},
    timeout=30,
)
print(f"PUT templates/product.json: {r3.status_code}")
if r3.status_code in (200, 201):
    print("Done. Payment notice now appears under the buy button on every product page.")
else:
    print(r3.text[:300])
