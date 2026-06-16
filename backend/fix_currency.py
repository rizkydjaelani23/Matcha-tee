"""
Fix 3 currency converter bugs:
1. /de/ locale path now forces EUR (was location-only, ignoring language route)
2. USD/EUR broken when exchange rate API fails — fallback returned 1, which
   triggered the 'rate===1' early-return guard. Fixed with hardcoded fallback rates.
3. Cached rate of 0 caused false cache hit — fixed with 'cached > 0' check.
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
  tmt-currency — free geolocation currency converter (display only)
  US -> USD, eurozone -> EUR, /de/ locale path -> EUR, default GBP.
  Checkout always charged in GBP. Rates cached 12h.
  Test override: add ?currency=USD / EUR / GBP to any URL.
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
  // Hardcoded fallback rates (GBP base) used when live API is unreachable
  var FALLBACK = { USD: 1.27, EUR: 1.17 };
  var EUR_CC = ["DE","AT","BE","NL","FR","IT","ES","PT","IE","FI",
                "GR","LU","SK","SI","EE","LV","LT","CY","MT","HR"];
  var LOCALE = { USD:"en-US", EUR:"de-DE", GBP:"en-GB" };

  function ls(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } }
  function lset(k,v){ try{ localStorage.setItem(k,v); }catch(e){} }

  function ccyFor(cc){
    if (cc === "US") return "USD";
    if (EUR_CC.indexOf(cc) >= 0) return "EUR";
    return "GBP";
  }

  function urlOverride(){
    var m = window.location.search.match(/[?&]currency=(USD|EUR|GBP)/i);
    return m ? m[1].toUpperCase() : null;
  }

  function resolveCurrency(){
    // 1. URL param always wins
    var ov = urlOverride();
    if (ov){ lset("tmt-ccy-pref", ov); return Promise.resolve(ov); }
    // 2. Stored preference from a previous override
    var pref = ls("tmt-ccy-pref");
    if (pref) return Promise.resolve(pref);
    // 3. /de/ locale path -> EUR (German store route)
    var p = window.location.pathname;
    if (p === "/de" || p.indexOf("/de/") === 0) return Promise.resolve("EUR");
    // 4. Cached geo result
    var c = ls("tmt-country"), ts = parseInt(ls("tmt-country-ts")||"0",10);
    if (c && (Date.now()-ts) < GEO_TTL) return Promise.resolve(ccyFor(c));
    // 5. Live geo lookup
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
    var rk = "tmt-rate-"+ccy, tk = "tmt-rate-ts-"+ccy;
    var cached = parseFloat(ls(rk)||"0");
    var ts = parseInt(ls(tk)||"0",10);
    // Only trust cache if rate is a real positive number
    if (cached > 0 && (Date.now()-ts) < RATE_TTL) return Promise.resolve(cached);
    return fetch("https://open.er-api.com/v6/latest/GBP")
      .then(function(r){ return r.json(); })
      .then(function(d){
        var rate = d && d.rates && d.rates[ccy];
        if (rate && rate > 0){
          lset(rk, String(rate)); lset(tk, String(Date.now())); return rate;
        }
        // API returned but rate missing — use cache or hardcoded fallback
        return (cached > 0) ? cached : (FALLBACK[ccy] || 1.2);
      })
      .catch(function(){
        // Network failure — use cache or hardcoded fallback, never return 1
        return (cached > 0) ? cached : (FALLBACK[ccy] || 1.2);
      });
  }

  function makeConverter(ccy, rate){
    var fmt = new Intl.NumberFormat(LOCALE[ccy]||"en-US",
                {style:"currency",currency:ccy});
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
      var nodes=[], n;
      while((n=walker.nextNode())) nodes.push(n);
      nodes.forEach(function(node){
        node.nodeValue = node.nodeValue.replace(/\\u00a3\\s?[\\d,]+(?:\\.\\d{1,2})?/g, function(m){
          var num = parseFloat(m.replace(/[\\u00a3,\\s]/g,""));
          return isNaN(num) ? m : fmt.format(num * rate);
        });
      });
    };
  }

  function showBadge(ccy){
    var bar=document.getElementById("tmt-ccy-badge");
    var lab=document.getElementById("tmt-ccy-label");
    if (!bar||!lab) return;
    lab.textContent = "\\ud83c\\udf10 "+ccy+" \\u00b7 billed in GBP";
    bar.title = "Prices shown in "+ccy+". Checkout is charged in GBP.";
    bar.style.display = "block";
  }

  resolveCurrency().then(function(ccy){
    if (ccy === "GBP") return;
    getRate(ccy).then(function(rate){
      if (!rate || rate <= 0) return;   // guard: must be a positive number
      var convert = makeConverter(ccy, rate);
      function run(){ convert(document.body); }
      if (document.body) run();
      document.addEventListener("DOMContentLoaded", run);
      var t;
      var obs = new MutationObserver(function(){ clearTimeout(t); t=setTimeout(run,150); });
      function startObs(){
        if (document.body) obs.observe(document.body,{childList:true,subtree:true});
      }
      if (document.body) startObs(); else document.addEventListener("DOMContentLoaded",startObs);
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
    print("Done. Fixes applied:")
    print("  1. /de/ locale path now forces EUR")
    print("  2. USD/EUR fallback now uses hardcoded rates (not 1) when API fails")
    print("  3. Cached rate=0 no longer causes false cache hit")
else:
    print(r.text[:400])
