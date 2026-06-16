"""
Inject a German language detection banner into the Horizon theme.
Shows a bottom bar for visitors with German browser language,
offering to switch to the /de/ locale.
No new scopes needed — uses existing write_themes access.
"""
import os, sys, base64, httpx
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
    themes = r.json().get("themes", [])
    published = next((t for t in themes if t["role"] == "main"), None)
    if not published:
        print("ERROR: No published theme found"); sys.exit(1)
    print(f"Theme: {published['name']} (id={published['id']})")
    return published["id"]

def get_asset(theme_id, key):
    r = httpx.get(f"{API}/themes/{theme_id}/assets.json",
                  headers=RH, params={"asset[key]": key}, timeout=15)
    if r.status_code == 404: return None
    return r.json().get("asset", {}).get("value","")

def put_asset(theme_id, key, value):
    r = httpx.put(f"{API}/themes/{theme_id}/assets.json",
                  headers=H, timeout=30,
                  json={"asset": {"key": key, "value": value}})
    if r.status_code not in (200, 201):
        print(f"PUT error {r.status_code}: {r.text[:200]}")
        return False
    return True

# ── snippet content ───────────────────────────────────────────────────────────
SNIPPET = """\
{%- comment -%}
  tmt-de-popup — German language banner
  Shows for German-language browsers. Stores preference in localStorage.
  Once /de/ locale is enabled + Translate & Adapt is installed, /de/ routes work.
{%- endcomment -%}

<div id="tmt-de-bar" role="dialog" aria-label="Language selection" style="
  display:none;
  position:fixed;
  bottom:0;left:0;right:0;
  background:#1c1c1c;
  color:#f5f5f5;
  padding:14px 20px;
  align-items:center;
  justify-content:center;
  gap:16px;
  z-index:99999;
  font-family:inherit;
  font-size:14px;
  border-top:3px solid #5a8a6a;
  flex-wrap:wrap;
  box-shadow:0 -4px 16px rgba(0,0,0,0.35);
">
  <div style="text-align:center;line-height:1.5;">
    <strong>Diese Website ist auch auf Deutsch verfügbar.</strong><br>
    <span style="opacity:0.75;font-size:13px;">This store is available in German. Would you like to switch?</span>
  </div>
  <div style="display:flex;gap:10px;flex-shrink:0;">
    <button
      onclick="tmtDEswitch()"
      style="background:#5a8a6a;color:#fff;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:700;letter-spacing:0.3px;">
      Auf Deutsch wechseln
    </button>
    <button
      onclick="tmtDEdismiss()"
      style="background:transparent;color:#ccc;border:1px solid #555;padding:10px 16px;border-radius:6px;cursor:pointer;font-size:13px;">
      Stay in English
    </button>
  </div>
</div>

<script>
(function() {
  try {
    if (localStorage.getItem('tmt-lang-set')) return;
    var lang = (navigator.language || navigator.userLanguage || '').toLowerCase();
    if (!lang.startsWith('de')) return;
    // Don't show if already on /de/ path
    if (window.location.pathname.startsWith('/de/') || window.location.pathname === '/de') return;
    var bar = document.getElementById('tmt-de-bar');
    if (bar) bar.style.display = 'flex';
  } catch(e) {}
})();

function tmtDEswitch() {
  try { localStorage.setItem('tmt-lang-set', 'de'); } catch(e) {}
  var path = window.location.pathname;
  var search = window.location.search;
  // If path already starts with /de strip it to avoid /de/de
  path = path.replace(/^\\/de(\\/|$)/, '/');
  window.location.href = '/de' + (path === '/' ? '' : path) + search;
}

function tmtDEdismiss() {
  try { localStorage.setItem('tmt-lang-set', 'en'); } catch(e) {}
  var bar = document.getElementById('tmt-de-bar');
  if (bar) bar.style.display = 'none';
}
</script>
"""

# ── main ──────────────────────────────────────────────────────────────────────
theme_id = get_theme_id()

# 1. Upload snippet
print("Uploading snippets/tmt-de-popup.liquid...")
if put_asset(theme_id, "snippets/tmt-de-popup.liquid", SNIPPET):
    print("  OK — snippet uploaded")
else:
    print("  FAILED"); sys.exit(1)

# 2. Read theme.liquid
print("Reading layout/theme.liquid...")
layout = get_asset(theme_id, "layout/theme.liquid")
if not layout:
    print("  ERROR: could not read theme.liquid"); sys.exit(1)
print(f"  Read OK ({len(layout)} chars)")

# 3. Check if render tag already injected
RENDER_TAG = "{% render 'tmt-de-popup' %}"
if RENDER_TAG in layout:
    print("  Already injected — skipping theme.liquid update")
else:
    # Inject just before </body>
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
German language banner is now LIVE.

What happens:
  • German-language browsers see a bottom bar:
      "Diese Website ist auch auf Deutsch verfügbar"
      [Auf Deutsch wechseln] [Stay in English]
  • "Switch" stores preference in localStorage + redirects to /de/...
  • "Stay" stores preference + hides bar permanently
  • Won't re-show once dismissed

NEXT STEPS to make /de/ routes fully work:
  1. In Shopify Admin → Settings → Languages:
       Add German and publish it
  2. Install 'Translate & Adapt' (free Shopify app):
       Auto-translates all storefront text to German
  3. After Markets setup script runs:
       German visitors see EUR prices + German text
══════════════════════════════════════════════════════
""")
