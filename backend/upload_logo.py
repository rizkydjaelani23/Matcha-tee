"""Upload logo to Shopify theme and set it in theme settings."""
import base64, json, os, sys
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE    = os.environ["SHOPIFY_STORE"]
H        = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"], "Content-Type": "application/json"}
RH       = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"]}
API      = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "scraper", "Matchatee logo.jpeg")
ASSET_KEY = "assets/tmt-logo.jpeg"

# ── 1. Upload logo as theme asset ─────────────────────────────────────────────
print("1. Reading logo file...")
with open(LOGO_PATH, "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode("ascii")

print("2. Uploading to Shopify theme assets...")
r = httpx.put(
    f"{API}/themes/{THEME_ID}/assets.json",
    headers=H,
    json={"asset": {"key": ASSET_KEY, "attachment": logo_b64}},
    timeout=60,
)
print(f"   PUT {ASSET_KEY}: {r.status_code}")
if r.status_code not in (200, 201):
    print(f"   Error: {r.text[:300]}")
    sys.exit(1)

asset_url = r.json()["asset"]["public_url"]
print(f"   Public URL: {asset_url}")

# ── 2. Read current theme settings_data.json ──────────────────────────────────
print("\n3. Fetching theme settings_data.json...")
r2 = httpx.get(
    f"{API}/themes/{THEME_ID}/assets.json",
    headers=RH,
    params={"asset[key]": "config/settings_data.json"},
    timeout=30,
)
settings = json.loads(r2.json()["asset"]["value"])

# ── 3. Inject logo into header section settings ───────────────────────────────
print("4. Injecting logo into theme settings...")

# Shopify Horizon stores logo in sections > header > settings
# The logo setting key is typically "logo" and the value is the asset filename
changed = False

# Try sections-based settings (Horizon theme)
sections = settings.get("current", {}).get("sections", {})
for key, section in sections.items():
    if section.get("type") in ("header", "header-group", "announcement-bar"):
        continue  # skip non-header sections
    # header section is usually keyed as "header"

# Direct approach: set in the header section
header_section = sections.get("header", {})
if header_section:
    if "settings" not in header_section:
        header_section["settings"] = {}
    header_section["settings"]["logo"] = ASSET_KEY.replace("assets/", "")
    settings["current"]["sections"]["header"] = header_section
    changed = True
    print("   Set logo in sections.header.settings.logo")

# Also try top-level current settings
if not changed:
    current = settings.get("current", {})
    if "settings" not in current:
        current["settings"] = {}
    current["settings"]["logo"] = ASSET_KEY.replace("assets/", "")
    settings["current"] = current
    print("   Set logo in current.settings.logo")
    changed = True

# ── 4. Push updated settings_data.json ───────────────────────────────────────
print("\n5. Pushing updated settings_data.json...")
r3 = httpx.put(
    f"{API}/themes/{THEME_ID}/assets.json",
    headers=H,
    json={"asset": {"key": "config/settings_data.json", "value": json.dumps(settings, ensure_ascii=False)}},
    timeout=60,
)
print(f"   PUT config/settings_data.json: {r3.status_code}")
if r3.status_code not in (200, 201):
    print(f"   Error: {r3.text[:300]}")

print(f"""
Done!
Logo uploaded to: {asset_url}

If the logo doesn't appear in the header automatically, go to:
  Shopify Admin → Online Store → Themes → Customize → Header
  and select the uploaded logo from the image picker.
""")
