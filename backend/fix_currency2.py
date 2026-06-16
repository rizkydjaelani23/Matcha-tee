"""
Currency converter v3:
- Adds Shopify localization form listener so when user picks "United States"
  from the country selector in the theme, currency switches to USD immediately.
- Adds window.Shopify.country fallback (set after localization form redirects).
- Clears stale tmt-ccy-pref when user picks a non-converting country (back to GBP).
"""
import os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
H  = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API = f"https://{STORE}/admin/api/2025-01"
THEME = 143507587185

SNIPPET = """{%- comment -%}
  tmt-currency v3 — free geolocation + Shopify country selector integration.
  US -> USD | eurozone + /de/ -> EUR | default GBP (checkout always GBP).
  Override: ?currency=USD / EUR / GBP stored in localStorage.
  Also reacts to Shopify's native country/region selector.
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
  var RATE_TTL = 12 * 60 * 60 * 1000;
  var GEO_TTL  = 24 * 60 * 60 * 1000;
  var FALLBACK  = { USD: 1.27, EUR: 1.17 };
  var EUR_CC    = ["DE","AT","BE","NL","FR","IT","ES","PT","IE","FI",
                   "GR","LU","SK","SI","EE","LV","LT","CY","MT","HR"];
  var LOCALE    = { USD:"en-US", EUR:"de-DE", GBP:"en-GB" };

  function ls(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } }
  function lset(k,v){ try{ localStorage.setItem(k,v); }catch(e){} }
  function ldel(k){ try{ localStorage.removeItem(k); }catch(e){} }

  function ccyFor(cc){
    if (!cc) return "GBP";
    cc = cc.toUpperCase();
    if (cc === "US") return "USD";
    if (EUR_CC.indexOf(cc) >= 0) return "EUR";
    return "GBP";
  }

  function urlOverride(){
    var m = window.location.search.match(/[?&]currency=(USD|EUR|GBP)/i);
    return m ? m[1].toUpperCase() : null;
  }

  function resolveCurrency(){
    // 1. URL ?currency= param wins
    var ov = urlOverride();
    if (ov){ lset("tmt-ccy-pref", ov); return Promise.resolve(ov); }
    // 2. Stored preference from previous selector/override
    var pref = ls("tmt-ccy-pref");
    if (pref) return Promise.resolve(pref);
    // 3. /de/ locale path -> EUR
    var p = window.location.pathname;
    if (p === "/de" || p.indexOf("/de/") === 0) return Promise.resolve("EUR");
    // 4. Shopify's country context (set after localization form redirect)
    if (window.Shopify && window.Shopify.country) {
      var sc = ccyFor(window.Shopify.country);
      if (sc !== "GBP") return Promise.resolve(sc);
    }
    // 5. Cached geo
    var c = ls("tmt-country"), ts = parseInt(ls("tmt-country-ts")||"0",10);
    if (c && (Date.now()-ts) < GEO_TTL) return Promise.resolve(ccyFor(c));
    // 6. Live geo lookup
    return fetch("https://get.geojs.io/v1/ip/country.json")
      .then(function(r){ return r.json(); })
      .then(function(d){
        var cc = (d && d.country || "").toUpperCase();
        if (cc){ lset("tmt-country",cc); lset("tmt-country-ts",String(Date.now())); }
        return ccyFor(cc);
      })
      .catch(function(){
        return fetch("https://ipwho.is/")
          .then(function(r){ return r.json(); })
          .then(function(d){
            var cc = (d && d.country_code || "").toUpperCase();
            if (cc){ lset("tmt-country",cc); lset("tmt-country-ts",String(Date.now())); }
            return ccyFor(cc);
          })
          .catch(function(){ return "GBP"; });
      });
  }

  function getRate(ccy){
    if (ccy === "GBP") return Promise.resolve(1);
    var rk="tmt-rate-"+ccy, tk="tmt-rate-ts-"+ccy;
    var cached = parseFloat(ls(rk)||"0");
    var ts     = parseInt(ls(tk)||"0",10);
    if (cached > 0 && (Date.now()-ts) < RATE_TTL) return Promise.resolve(cached);
    return fetch("https://open.er-api.com/v6/latest/GBP")
      .then(function(r){ return r.json(); })
      .then(function(d){
        var rate = d && d.rates && d.rates[ccy];
        if (rate && rate > 0){ lset(rk,String(rate)); lset(tk,String(Date.now())); return rate; }
        return cached > 0 ? cached : (FALLBACK[ccy]||1.2);
      })
      .catch(function(){ return cached > 0 ? cached : (FALLBACK[ccy]||1.2); });
  }

  function makeConverter(ccy, rate){
    var fmt  = new Intl.NumberFormat(LOCALE[ccy]||"en-US",{style:"currency",currency:ccy});
    var SKIP = {SCRIPT:1,STYLE:1,TEXTAREA:1,NOSCRIPT:1};
    return function(root){
      if (!root) return;
      var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode: function(n){
          if (!n.nodeValue || n.nodeValue.indexOf("\\u00a3")===-1) return NodeFilter.FILTER_REJECT;
          var p = n.parentNode;
          if (!p || SKIP[p.nodeName]) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      });
      var nodes=[],n;
      while((n=walker.nextNode())) nodes.push(n);
      nodes.forEach(function(node){
        node.nodeValue = node.nodeValue.replace(
          /\\u00a3\\s?[\\d,]+(?:\\.\\d{1,2})?/g,
          function(m){
            var num=parseFloat(m.replace(/[\\u00a3,\\s]/g,""));
            return isNaN(num) ? m : fmt.format(num*rate);
          });
      });
    };
  }

  function showBadge(ccy){
    var bar=document.getElementById("tmt-ccy-badge");
    var lab=document.getElementById("tmt-ccy-label");
    if(!bar||!lab) return;
    lab.textContent="\\ud83c\\udf10 "+ccy+" \\u00b7 billed in GBP";
    bar.title="Prices shown in "+ccy+". Checkout is charged in GBP.";
    bar.style.display="block";
  }

  // ── Hook Shopify's country selector form ──────────────────────────────────
  // When user picks a country from the Horizon header/footer selector,
  // store the chosen country and update the currency before the page reloads.
  function hookCountrySelector(){
    var forms = document.querySelectorAll(
      'form[action*="/localization"], form[action="/localization"]'
    );
    forms.forEach(function(form){
      form.addEventListener("change", function(){
        var el = form.querySelector('[name="country_code"]') ||
                 form.querySelector('[name="locale_code"]');
        if (!el) return;
        var val = el.value.toUpperCase();
        // country_code is like "US", "DE"; locale_code is like "en", "de"
        var cc = val.length === 2 ? val : (val.startsWith("DE") ? "DE" : null);
        if (!cc) return;
        var ccy = ccyFor(cc);
        lset("tmt-country", cc);
        lset("tmt-country-ts", String(Date.now()));
        if (ccy === "GBP") {
          ldel("tmt-ccy-pref");   // clear pref so GBP shows natively
        } else {
          lset("tmt-ccy-pref", ccy);
        }
      });
    });
  }

  if (document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", hookCountrySelector);
  } else {
    hookCountrySelector();
  }

  // ── Run conversion ─────────────────────────────────────────────────────────
  resolveCurrency().then(function(ccy){
    if (ccy === "GBP") return;
    getRate(ccy).then(function(rate){
      if (!rate || rate <= 0) return;
      var convert = makeConverter(ccy, rate);
      function run(){ convert(document.body); }
      if (document.body) run();
      document.addEventListener("DOMContentLoaded", run);
      var t;
      var obs = new MutationObserver(function(){ clearTimeout(t); t=setTimeout(run,150); });
      function startObs(){
        if (document.body) obs.observe(document.body,{childList:true,subtree:true});
      }
      if (document.body) startObs();
      else document.addEventListener("DOMContentLoaded", startObs);
      setTimeout(run,800); setTimeout(run,2000);
      showBadge(ccy);
    });
  });
})();
</script>"""

r = httpx.put(
    f"{API}/themes/{THEME}/assets.json",
    headers=H,
    json={"asset": {"key": "snippets/tmt-currency.liquid", "value": SNIPPET}},
    timeout=30,
)
print(f"PUT tmt-currency.liquid: {r.status_code}")
if r.status_code in (200, 201):
    print("Currency v3 deployed. Changes:")
    print("  + Shopify country selector now triggers currency switch on change")
    print("  + window.Shopify.country read on page load (set after form redirect)")
    print("  + GBP preference cleared when non-converting country selected")
else:
    print(r.text[:400])
