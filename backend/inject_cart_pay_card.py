"""
Inject a prominent "Pay with Card" button + modal into snippets/cart-summary.liquid.
Placed right after the PayPal smart buttons block, before </div> of .cart__ctas.
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

# ── Inject marker: right after the closing {% endif %} of additional_checkout_buttons ─
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

INJECT = """  {% if additional_checkout_buttons and settings.show_accelerated_checkout_buttons %}
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

  <!-- Modal -->
  <div id="tmtPayModal" class="tmt-modal-backdrop" onclick="if(event.target===this)tmtClosePayModal()" role="dialog" aria-modal="true">
    <div class="tmt-modal">
      <button class="tmt-modal-close" onclick="tmtClosePayModal()" aria-label="Close">&times;</button>
      <h2 class="tmt-modal-title">Pay by Debit / Credit Card</h2>
      <p class="tmt-modal-sub">No PayPal account needed &mdash; follow these 3 steps:</p>

      <div class="tmt-steps">
        <div class="tmt-step">
          <div class="tmt-step-num">1</div>
          <div class="tmt-step-body">
            <strong>Click the PayPal button</strong> above (yellow button in your cart)
          </div>
        </div>
        <div class="tmt-step">
          <div class="tmt-step-num">2</div>
          <div class="tmt-step-body">
            A PayPal window opens &mdash; look for the link that says<br>
            <strong>&ldquo;Pay with Debit or Credit Card&rdquo;</strong> (it&rsquo;s below the login box)
          </div>
        </div>
        <div class="tmt-step">
          <div class="tmt-step-num">3</div>
          <div class="tmt-step-body">
            Enter your card details &mdash; <strong>no PayPal account or sign-up required</strong>
          </div>
        </div>
      </div>

      <div class="tmt-modal-actions">
        <button class="tmt-modal-paypal-btn" onclick="tmtClosePayModal()">
          OK, got it &mdash; take me to checkout
        </button>
      </div>
      <p class="tmt-modal-note">
        🔒 All payments are processed securely by PayPal
      </p>
    </div>
  </div>
  {%- endunless -%}
</div>"""

if MARKER not in content:
    print("ERROR: marker not found in cart-summary.liquid — check indentation")
    # Try to find where additional_checkout_buttons is
    idx = content.find("content_for_additional_checkout_buttons")
    print(f"  'content_for_additional_checkout_buttons' found at char {idx}")
    print(content[max(0,idx-200):idx+200])
    sys.exit(1)

new_content = content.replace(MARKER, INJECT, 1)

# ── Append CSS + JS before {% stylesheet %} ────────────────────────────────────
STYLE_CSS = """
{% stylesheet %}
  /* ── TMT Pay by Card ──────────────────────────────── */
  .tmt-pay-card-wrap {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    margin-block-start: 4px;
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
  .tmt-pay-card-btn:hover {
    background: #1a1a1a;
    color: #fff;
  }
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
  .tmt-pill--visa  { color: #1a1f71; }
  .tmt-pill--mc   { color: #c0392b; }
  .tmt-pill--amex { color: #007bc1; }

  /* ── Modal ────────────────────────────────────────── */
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
  .tmt-modal-backdrop.tmt-open {
    display: flex;
  }
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
  .tmt-modal-title {
    font-size: 1.2rem;
    font-weight: 700;
    margin: 0 0 4px;
    color: var(--color-foreground);
  }
  .tmt-modal-sub {
    font-size: 0.85rem;
    color: rgb(var(--color-foreground-rgb) / 0.6);
    margin: 0 0 20px;
  }
  .tmt-steps {
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-bottom: 22px;
  }
  .tmt-step {
    display: flex;
    gap: 14px;
    align-items: flex-start;
  }
  .tmt-step-num {
    flex-shrink: 0;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: #1a1a1a;
    color: #fff;
    font-size: 0.85rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .tmt-step-body {
    font-size: 0.88rem;
    line-height: 1.55;
    color: var(--color-foreground);
    padding-top: 4px;
  }
  .tmt-step-body strong { color: var(--color-foreground); }
  .tmt-modal-actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 14px;
  }
  .tmt-modal-paypal-btn {
    width: 100%;
    padding: 13px;
    background: #FFD140;
    color: #1a1a1a;
    border: none;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 700;
    cursor: pointer;
    transition: filter 0.15s;
  }
  .tmt-modal-paypal-btn:hover { filter: brightness(0.93); }
  .tmt-modal-note {
    font-size: 0.75rem;
    text-align: center;
    color: rgb(var(--color-foreground-rgb) / 0.5);
    margin: 0;
  }
{% endstylesheet %}"""

JS_SNIPPET = """
<script>
  function tmtOpenPayModal() {
    document.getElementById('tmtPayModal').classList.add('tmt-open');
    document.body.style.overflow = 'hidden';
  }
  function tmtClosePayModal() {
    document.getElementById('tmtPayModal').classList.remove('tmt-open');
    document.body.style.overflow = '';
  }
</script>"""

# Insert CSS right before the first {% stylesheet %}
first_stylesheet = "{% stylesheet %}"
if first_stylesheet in new_content:
    new_content = new_content.replace(first_stylesheet, STYLE_CSS + "\n" + first_stylesheet, 1)
else:
    new_content += STYLE_CSS

# Append JS at very end
new_content = new_content.rstrip() + "\n" + JS_SNIPPET + "\n"

# Push
r2 = httpx.put(
    f"{API}/themes/{THEME}/assets.json",
    headers=H,
    json={"asset": {"key": "snippets/cart-summary.liquid", "value": new_content}},
    timeout=30,
)
print(f"PUT snippets/cart-summary.liquid: {r2.status_code}")
if r2.status_code in (200, 201):
    print("Done.")
    print("Cart page now shows: PayPal button → 'or' divider → '💳 Pay with Debit/Credit Card' button")
    print("Clicking the card button opens a 3-step modal guide.")
else:
    print(r2.text[:400])
