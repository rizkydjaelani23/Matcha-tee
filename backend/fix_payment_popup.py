"""
Fix: modal popup appears behind cart drawer overlay.
Root cause: position:fixed inside a CSS-transformed ancestor (cart drawer slide animation)
creates a new stacking context, trapping the modal.
Fix: on open, move the modal to document.body so it escapes the transform.
Also bumps z-index from 9999 → 99999 for extra clearance.
"""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH    = {"X-Shopify-Access-Token": TOKEN}
API   = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

r = httpx.get(f"{API}/themes/{THEME}/assets.json", headers=RH,
              params={"asset[key]": "snippets/cart-summary.liquid"}, timeout=15)
content = r.json()["asset"]["value"]

if "tmt-pay-card-wrap" not in content:
    print("Payment guide not found in cart-summary.liquid — nothing to fix.")
    sys.exit(0)

# Fix 1: bump z-index from 9999 to 99999
OLD_Z = "z-index: 9999;"
NEW_Z = "z-index: 99999;"
if OLD_Z in content:
    content = content.replace(OLD_Z, NEW_Z)
    print("z-index: 9999 → 99999")
else:
    print("z-index already updated or not found at expected value")

# Fix 2: replace the JS open function to move modal to body on first open
OLD_JS = """function tmtOpenPayModal(){document.getElementById('tmtPayModal').classList.add('tmt-open');document.body.style.overflow='hidden';}
function tmtClosePayModal(){document.getElementById('tmtPayModal').classList.remove('tmt-open');document.body.style.overflow='';}"""

NEW_JS = """function tmtOpenPayModal(){
  var m=document.getElementById('tmtPayModal');
  if(!m)return;
  // Move to body to escape cart-drawer stacking context (CSS transform trap)
  if(m.parentNode!==document.body)document.body.appendChild(m);
  m.classList.add('tmt-open');
  document.body.style.overflow='hidden';
}
function tmtClosePayModal(){
  var m=document.getElementById('tmtPayModal');
  if(m){m.classList.remove('tmt-open');document.body.style.overflow='';}
}"""

if OLD_JS in content:
    content = content.replace(OLD_JS, NEW_JS)
    print("JS open function patched to move modal to body")
else:
    print("WARNING: JS marker not found exactly — searching loosely...")
    if "tmtOpenPayModal" in content:
        print("  tmtOpenPayModal found but pattern differs. Manual fix needed.")
    else:
        print("  tmtOpenPayModal not found at all.")

# Push
r2 = httpx.put(
    f"{API}/themes/{THEME}/assets.json",
    headers=H,
    json={"asset": {"key": "snippets/cart-summary.liquid", "value": content}},
    timeout=30,
)
print(f"\nPUT cart-summary.liquid: {r2.status_code}")
if r2.status_code in (200, 201):
    print("Done. The payment guide popup will now float above the cart drawer.")
else:
    print(r2.text[:400])
