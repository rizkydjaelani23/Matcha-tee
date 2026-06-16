"""
Inject a free geolocation currency converter into the Horizon theme.
US visitors see USD, Germany/eurozone see EUR, everyone else stays GBP.
Display-only (checkout remains GBP) — same as the free currency-app tier,
but with the auto-switch-by-location feature that app charges $9.95/mo for.

No new scopes needed — uses existing write_themes access.
APIs used (all free, no key):
  - get.geojs.io        -> visitor country by IP
  - open.er-api.com     -> live GBP exchange rates
"""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
RH = {"X-Shopify-Access-Token": TOKEN}
API = f"https://{STORE}/admin/api/2025-01"


def get_theme_id():
    r = httpx.get(f"{API}/themes.json", headers=RH, timeout=15)
    published = next((t for t in r.json().get("themes", []) if t["role"] == "main"), None)
    if not published:
        print("ERROR: No published theme found"); sys.exit(1)
    print(f"Theme: {published['name']} (id={published['id']})")
    return published["id"]


def get_asset(theme_id, key):
    r = httpx.get(f"{API}/themes/{theme_id}/assets.json",
                  headers=RH, params={"asset[key]": key}, timeout=15)
    if r.status_code == 404:
        return None
    return r.json().get("asset", {}).get("value", "")


def put_asset(theme_id, key, value):
    r = httpx.put(f"{API}/themes/{theme_id}/assets.json",
                  headers=H, timeout=30,
                  json={"asset": {"key": key, "value": value}})
    if r.status_code not in (200, 201):
        print(f"PUT error {r.status_code}: {r.text[:200]}")
        return False
    return True


# ── snippet content ───────────────────────────────────────────────────────────
# NOTE: backslashes in the JS regexes are doubled so the Python string emits a
# single backslash into the .liquid file (same convention as tmt-de-popup).
SNIPPET = """\
{%- comment -%}
  tmt-currency — free geolocation currency converter (display only)
  US -> USD, Germany/eurozone -> EUR, everyone else stays GBP.
  Checkout still happens in GBP. Rates cached 12h in localStorage.
  Override for testing: add ?currency=USD (or EUR / GBP) to any URL.
{%- endcomment -%}

<div id="tmt-ccy-badge" style="
  display:none;position:fixed;bottom:14px;right:14px;z-index:99990;
  background:#1c1c1c;color:#f5f5f5;font-size:12px;line-height:1;
  padding:8px 12px;border-radius:20px;font-family:inherit;
  box-shadow:0 2px 10px rgba(0,0,0,0.25);cursor:default;opacity:0.92;">
  <span id="tmt-ccy-label"></span>
</div>

<script>
(function() {
  "use strict";
  var RATE_TTL = 12 * 60 * 60 * 1000;   // 12h
  var GEO_TTL  = 24 * 60 * 60 * 1000;   // 24h
  var EUR = ['DE','AT','BE','NL','FR','IT','ES','PT','IE','FI','GR','LU',
             'SK','SI','EE','LV','LT','CY','MT','HR'];
  var LOCALE = { USD:'en-US', EUR:'de-DE', GBP:'en-GB' };

  function ls(k){ try { return localStorage.getItem(k); } catch(e){ return null; } }
  function lset(k,v){ try { localStorage.setItem(k,v); } catch(e){} }

  function ccyFor(country){
    if (country === 'US') return 'USD';
    if (EUR.indexOf(country) >= 0) return 'EUR';
    return 'GBP';
  }

  function urlOverride(){
    var m = window.location.search.match(/[?&]currency=(USD|EUR|GBP)/i);
    return m ? m[1].toUpperCase() : null;
  }

  // 1) Resolve the currency we should display
  function resolveCurrency(){
    var ov = urlOverride();
    if (ov){ lset('tmt-ccy-pref', ov); return Promise.resolve(ov); }
    var pref = ls('tmt-ccy-pref');
    if (pref) return Promise.resolve(pref);

    var c   = ls('tmt-country');
    var cts = parseInt(ls('tmt-country-ts') || '0', 10);
    if (c && (Date.now() - cts) < GEO_TTL) return Promise.resolve(ccyFor(c));

    return fetch('https://get.geojs.io/v1/ip/country.json')
      .then(function(r){ return r.json(); })
      .then(function(d){
        var cc = (d && d.country || '').toUpperCase();
        if (cc){ lset('tmt-country', cc); lset('tmt-country-ts', String(Date.now())); }
        return ccyFor(cc);
      })
      .catch(function(){
        // fallback geo provider
        return fetch('https://ipwho.is/').then(function(r){return r.json();}).then(function(d){
          var cc = (d && d.country_code || '').toUpperCase();
          if (cc){ lset('tmt-country', cc); lset('tmt-country-ts', String(Date.now())); }
          return ccyFor(cc);
        }).catch(function(){ return 'GBP'; });
      });
  }

  // 2) Get the GBP->currency rate (cached)
  function getRate(ccy){
    if (ccy === 'GBP') return Promise.resolve(1);
    var rk = 'tmt-rate-' + ccy, tk = 'tmt-rate-ts-' + ccy;
    var cached = parseFloat(ls(rk) || '0');
    var ts = parseInt(ls(tk) || '0', 10);
    if (cached && (Date.now() - ts) < RATE_TTL) return Promise.resolve(cached);
    return fetch('https://open.er-api.com/v6/latest/GBP')
      .then(function(r){ return r.json(); })
      .then(function(d){
        var rate = d && d.rates && d.rates[ccy];
        if (rate){ lset(rk, String(rate)); lset(tk, String(Date.now())); return rate; }
        return cached || 1;
      })
      .catch(function(){ return cached || 1; });
  }

  // 3) Convert every £ amount in the DOM
  function makeConverter(ccy, rate){
    var fmt = new Intl.NumberFormat(LOCALE[ccy] || 'en-US',
                { style:'currency', currency:ccy });
    var SKIP = { SCRIPT:1, STYLE:1, TEXTAREA:1, NOSCRIPT:1 };
    return function(root){
      if (!root || rate === 1) return;
      var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode: function(n){
          if (!n.nodeValue || n.nodeValue.indexOf('\\u00a3') === -1)
            return NodeFilter.FILTER_REJECT;
          var p = n.parentNode;
          if (!p || SKIP[p.nodeName]) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      });
      var nodes = [], n;
      while ((n = walker.nextNode())) nodes.push(n);
      nodes.forEach(function(node){
        node.nodeValue = node.nodeValue.replace(
          /\\u00a3\\s?[\\d,]+(?:\\.\\d{1,2})?/g,
          function(m){
            var num = parseFloat(m.replace(/[\\u00a3,\\s]/g, ''));
            if (isNaN(num)) return m;
            return fmt.format(num * rate);
          });
      });
    };
  }

  function showBadge(ccy){
    var bar = document.getElementById('tmt-ccy-badge');
    var lab = document.getElementById('tmt-ccy-label');
    if (!bar || !lab) return;
    lab.textContent = '\\ud83c\\udf10 ' + ccy + ' · billed in GBP';
    bar.title = 'Prices are converted from GBP for your region. ' +
                'Your order is charged in GBP at checkout.';
    bar.style.display = 'block';
  }

  // ── run ──
  resolveCurrency().then(function(ccy){
    if (ccy === 'GBP') return;            // nothing to do for UK / default
    getRate(ccy).then(function(rate){
      if (!rate || rate === 1) return;
      var convert = makeConverter(ccy, rate);
      function run(){ convert(document.body); }
      if (document.body) run();
      document.addEventListener('DOMContentLoaded', run);
      // keep converting on dynamic updates (variant change, cart drawer, etc.)
      var t;
      var obs = new MutationObserver(function(){
        clearTimeout(t); t = setTimeout(run, 150);
      });
      function startObs(){
        if (document.body) obs.observe(document.body, {childList:true, subtree:true});
      }
      if (document.body) startObs(); else document.addEventListener('DOMContentLoaded', startObs);
      // a couple of late passes for theme JS that renders prices after load
      setTimeout(run, 800); setTimeout(run, 2000);
      showBadge(ccy);
    });
  });
})();
</script>
"""

# ── main ──────────────────────────────────────────────────────────────────────
theme_id = get_theme_id()

print("Uploading snippets/tmt-currency.liquid...")
if put_asset(theme_id, "snippets/tmt-currency.liquid", SNIPPET):
    print("  OK — snippet uploaded")
else:
    print("  FAILED"); sys.exit(1)

print("Reading layout/theme.liquid...")
layout = get_asset(theme_id, "layout/theme.liquid")
if not layout:
    print("  ERROR: could not read theme.liquid"); sys.exit(1)
print(f"  Read OK ({len(layout)} chars)")

RENDER_TAG = "{% render 'tmt-currency' %}"
if RENDER_TAG in layout:
    print("  Already injected — skipping theme.liquid update")
else:
    if "</body>" not in layout:
        print("  ERROR: </body> not found in theme.liquid"); sys.exit(1)
    layout = layout.replace("</body>", f"\n  {RENDER_TAG}\n</body>", 1)
    print("Uploading modified layout/theme.liquid...")
    if put_asset(theme_id, "layout/theme.liquid", layout):
        print("  OK — theme.liquid updated")
    else:
        print("  FAILED"); sys.exit(1)

print("""
══ DONE ══════════════════════════════════════════════
Free geolocation currency converter is now LIVE.

What happens automatically:
  • US visitors        -> all prices shown in USD
  • Germany / eurozone -> all prices shown in EUR
  • Everyone else      -> stays in GBP (no change)
  • Live GBP rates, cached 12h. Converts products, collections,
    cart, and updates on variant change / cart drawer.
  • Small corner badge: "USD · billed in GBP".

IMPORTANT — this is DISPLAY ONLY:
  Customers still CHECK OUT in GBP (PayPal charges GBP).
  For true local-currency checkout you'd need Shopify Payments
  + Markets (the setup_markets.py plan).

TEST IT:
  Add ?currency=USD to any page URL to force USD, e.g.
    https://thematchatee.com/?currency=USD
    https://thematchatee.com/?currency=EUR
  Use ?currency=GBP to reset.
══════════════════════════════════════════════════════
""")
