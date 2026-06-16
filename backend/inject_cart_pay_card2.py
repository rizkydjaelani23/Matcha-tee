"""
Inject Pay by Card button + modal into cart-summary.liquid.
CSS goes inside the existing stylesheet block, JS appended at end.
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

# Guard: skip if already injected
if "tmt-pay-card-wrap" in content:
    print("Already injected — skipping")
    sys.exit(0)

# ── 1. Inject HTML after additional_checkout_buttons block ────────────────────
MARKER = """  {% if additional_checkout_buttons and settings.show_accelerated_checkout_buttons %}
    <div
      class="
        additional-checkout-buttons
        {% if accelerated_checkout_buttons_layout == 'vertical' %}additional-checkout-buttons--vertical{% endif %}
      "
    >
      {{ content_for_additional_checkout_buttons }}
    </div>
  {% endif %}
</div>"""

HTML_INJECT = """  {% if additional_checkout_buttons and settings.show_accelerated_checkout_buttons %}
    <div
      class="
        additional-checkout-buttons
        {% if accelerated_checkout_buttons_layout == 'vertical' %}additional-checkout-buttons--vertical{% endif %}
      "
    >
      {{ content_for_additional_checkout_buttons }}
    </div>
  {% endif %}

  {%- unless cart == empty -%}
  <div class="tmt-pay-card-wrap">
    <div class="tmt-pay-card-or"><span>or</span></div>
    <button type="button" class="tmt-pay-card-btn" onclick="tmtOpenPayModal()">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
      Pay with Debit / Credit Card
    </button>
    <div class="tmt-pay-card-logos">
      <span class="tmt-pill tmt-pill--visa">VISA</span>
      <span class="tmt-pill tmt-pill--mc">MC</span>
      <span class="tmt-pill tmt-pill--amex">AMEX</span>
      <span class="tmt-pill">Debit</span>
      <span class="tmt-pill">Maestro</span>
    </div>
  </div>

  <div id="tmtPayModal" class="tmt-modal-backdrop" onclick="if(event.target===this)tmtClosePayModal()" role="dialog" aria-modal="true">
    <div class="tmt-modal">
      <button class="tmt-modal-close" onclick="tmtClosePayModal()" aria-label="Close">&times;</button>
      <h2 class="tmt-modal-title">Pay by Debit / Credit Card</h2>
      <p class="tmt-modal-sub">No PayPal account needed &mdash; follow these 3 steps:</p>
      <div class="tmt-steps">
        <div class="tmt-step">
          <div class="tmt-step-num">1</div>
          <div class="tmt-step-body">Click the <strong>yellow PayPal button</strong> on this page</div>
        </div>
        <div class="tmt-step">
          <div class="tmt-step-num">2</div>
          <div class="tmt-step-body">A PayPal window opens &mdash; look <strong>below the login box</strong> for the link:<br><em>&ldquo;Pay with Debit or Credit Card&rdquo;</em></div>
        </div>
        <div class="tmt-step">
          <div class="tmt-step-num">3</div>
          <div class="tmt-step-body">Enter your card details &mdash; <strong>no PayPal account needed</strong></div>
        </div>
      </div>
      <div class="tmt-modal-actions">
        <button class="tmt-modal-ok" onclick="tmtClosePayModal()">Got it &mdash; go back &amp; click PayPal</button>
      </div>
      <p class="tmt-modal-note">&#128274; All payments processed securely by PayPal</p>
    </div>
  </div>
  {%- endunless -%}
</div>"""

if MARKER not in content:
    print("ERROR: HTML marker not found — dumping nearby content")
    idx = content.find("content_for_additional_checkout_buttons")
    print(repr(content[max(0,idx-300):idx+300]))
    sys.exit(1)

content = content.replace(MARKER, HTML_INJECT, 1)

# ── 2. Inject CSS inside the existing {% stylesheet %} block ──────────────────
CSS = """
  /* ─── TMT Pay by Card ──────────────────────────────── */
  .tmt-pay-card-wrap {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    margin-block-start: 6px;
  }
  .tmt-pay-card-or {
    display: flex;
    align-items: center;
    gap: 10px;
    color: rgb(var(--color-foreground-rgb) / 0.4);
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .tmt-pay-card-or::before,
  .tmt-pay-card-or::after {
    content: '';
    flex: 1;
    height: 1px;
    background: currentColor;
  }
  .tmt-pay-card-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 14px 20px;
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: #1a1a1a;
    background: #f5f5f5;
    border: 2px solid #1a1a1a;
    border-radius: var(--border-radius-button, 4px);
    cursor: pointer;
    transition: background 0.18s, color 0.18s;
  }
  .tmt-pay-card-btn:hover { background: #1a1a1a; color: #fff; }
  .tmt-pay-card-logos {
    display: flex;
    gap: 5px;
    justify-content: center;
    flex-wrap: wrap;
  }
  .tmt-pill {
    border: 1px solid rgba(var(--color-foreground-rgb), 0.2);
    border-radius: 3px;
    padding: 2px 7px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--color-foreground);
    background: var(--color-background);
  }
  .tmt-pill--visa { color: #1a1f71; }
  .tmt-pill--mc   { color: #c0392b; }
  .tmt-pill--amex { color: #007bc1; }
  /* ─── Modal ─────────────────────────────────────────── */
  .tmt-modal-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.55);
    z-index: 9999;
    align-items: center;
    justify-content: center;
    padding: 16px;
  }
  .tmt-modal-backdrop.tmt-open { display: flex; }
  .tmt-modal {
    background: var(--color-background, #fff);
    border-radius: 12px;
    padding: 28px 24px 20px;
    max-width: 420px;
    width: 100%;
    position: relative;
    box-shadow: 0 20px 60px rgba(0,0,0,0.25);
  }
  .tmt-modal-close {
    position: absolute;
    top: 12px; right: 16px;
    font-size: 1.5rem;
    line-height: 1;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-foreground);
    opacity: 0.5;
  }
  .tmt-modal-close:hover { opacity: 1; }
  .tmt-modal-title { font-size: 1.2rem; font-weight: 700; margin: 0 0 4px; }
  .tmt-modal-sub { font-size: 0.85rem; color: rgb(var(--color-foreground-rgb) / 0.6); margin: 0 0 20px; }
  .tmt-steps { display: flex; flex-direction: column; gap: 14px; margin-bottom: 22px; }
  .tmt-step { display: flex; gap: 14px; align-items: flex-start; }
  .tmt-step-num {
    flex-shrink: 0;
    width: 30px; height: 30px;
    border-radius: 50%;
    background: #1a1a1a;
    color: #fff;
    font-size: 0.85rem; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
  }
  .tmt-step-body { font-size: 0.88rem; line-height: 1.55; padding-top: 4px; }
  .tmt-modal-actions { margin-bottom: 14px; }
  .tmt-modal-ok {
    width: 100%;
    padding: 13px;
    background: #FFD140;
    color: #1a1a1a;
    border: none;
    border-radius: 6px;
    font-size: 0.9rem; font-weight: 700;
    cursor: pointer;
    transition: filter 0.15s;
  }
  .tmt-modal-ok:hover { filter: brightness(0.93); }
  .tmt-modal-note { font-size: 0.75rem; text-align: center; color: rgb(var(--color-foreground-rgb) / 0.5); margin: 0; }
"""

STYLESHEET_OPEN = "{% stylesheet %}"
if STYLESHEET_OPEN in content:
    content = content.replace(STYLESHEET_OPEN, STYLESHEET_OPEN + CSS, 1)
else:
    print("WARNING: no {% stylesheet %} found — appending CSS as <style>")
    content += f"\n<style>{CSS}</style>"

# ── 3. Append JS ──────────────────────────────────────────────────────────────
JS = """
<script>
function tmtOpenPayModal(){document.getElementById('tmtPayModal').classList.add('tmt-open');document.body.style.overflow='hidden';}
function tmtClosePayModal(){document.getElementById('tmtPayModal').classList.remove('tmt-open');document.body.style.overflow='';}
</script>"""
content = content.rstrip() + "\n" + JS + "\n"

# ── 4. Push ───────────────────────────────────────────────────────────────────
r2 = httpx.put(
    f"{API}/themes/{THEME}/assets.json",
    headers=H,
    json={"asset": {"key": "snippets/cart-summary.liquid", "value": content}},
    timeout=30,
)
print(f"PUT snippets/cart-summary.liquid: {r2.status_code}")
if r2.status_code in (200, 201):
    print("Live! Cart page now shows:")
    print("  [Checkout button]")
    print("  [PayPal smart button]")
    print("  ── or ──")
    print("  [💳 Pay with Debit / Credit Card]  ← opens 3-step modal guide")
    print("  VISA  MC  AMEX  Debit  Maestro")
else:
    print(r2.text[:500])
