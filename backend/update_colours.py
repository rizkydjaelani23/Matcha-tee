"""Apply the Matcha-Tees brand palette to all Horizon colour schemes."""
import json, os, sys, httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

STORE   = os.environ["SHOPIFY_STORE"]
H       = {"X-Shopify-Access-Token": os.environ["SHOPIFY_TOKEN"],
           "Content-Type": "application/json"}
API     = f"https://{STORE}/admin/api/2025-01"
THEME_ID = 143507587185
BASE    = os.path.dirname(__file__)

# ── palette ───────────────────────────────────────────────────────────────────
TAN     = "#9E7C5F"   # warm tan / brown
DBROWN  = "#6F5840"   # dark brown
SAGE    = "#658C5E"   # sage green (primary brand)
LSAGE   = "#91A287"   # light sage
CREAM   = "#FFF0D6"   # off-white / cream

# derived
SAGE_DIM    = "#537348"   # sage darkened ~10% for button hover
DBROWN_DIM  = "#5a4633"   # dark brown darkened for hover
TAN_DIM     = "#836348"


def scheme(bg, fg_heading, fg, btn_bg, btn_text, btn_hover_bg,
           sec_btn_text, sec_btn_border, input_bg="#ffffff14",
           input_text=None, input_border=None,
           sel_variant_bg=None, sel_variant_border=None):
    input_text   = input_text   or fg
    input_border = input_border or (fg + "80")
    sel_variant_bg     = sel_variant_bg     or btn_bg
    sel_variant_border = sel_variant_border or btn_bg
    return {"settings": {
        "background":                       bg,
        "foreground_heading":               fg_heading,
        "foreground":                       fg,
        "primary":                          fg,
        "primary_hover":                    fg_heading,
        "border":                           fg + "20",
        "shadow":                           DBROWN,
        # primary button
        "primary_button_background":        btn_bg,
        "primary_button_text":              btn_text,
        "primary_button_border":            btn_bg,
        "primary_button_hover_background":  btn_hover_bg,
        "primary_button_hover_text":        btn_text,
        "primary_button_hover_border":      btn_hover_bg,
        # secondary button
        "secondary_button_background":      "rgba(0,0,0,0)",
        "secondary_button_text":            sec_btn_text,
        "secondary_button_border":          sec_btn_border,
        "secondary_button_hover_background":"rgba(255,255,255,0.08)",
        "secondary_button_hover_text":      sec_btn_text,
        "secondary_button_hover_border":    sec_btn_border,
        # inputs
        "input_background":                 input_bg,
        "input_text_color":                 input_text,
        "input_border_color":               input_border,
        "input_hover_background":           "rgba(255,255,255,0.12)",
        # variant buttons
        "variant_background_color":         CREAM,
        "variant_text_color":               DBROWN,
        "variant_border_color":             DBROWN + "30",
        "variant_hover_background_color":   LSAGE + "40",
        "variant_hover_text_color":         DBROWN,
        "variant_hover_border_color":       SAGE,
        "selected_variant_background_color":   sel_variant_bg,
        "selected_variant_text_color":         CREAM,
        "selected_variant_border_color":       sel_variant_border,
        "selected_variant_hover_background_color": SAGE_DIM,
        "selected_variant_hover_text_color":       CREAM,
        "selected_variant_hover_border_color":     SAGE_DIM,
    }}


SCHEMES = {
    # scheme-1: main body — clean white, dark brown text, sage green buttons
    "scheme-1": scheme(
        bg="#ffffff", fg_heading=DBROWN, fg=DBROWN,
        btn_bg=SAGE, btn_text=CREAM, btn_hover_bg=SAGE_DIM,
        sec_btn_text=DBROWN, sec_btn_border=DBROWN,
        input_bg="#f9f9f9", input_text=DBROWN, input_border=DBROWN+"30",
    ),
    # scheme-2: light sage — trust badges, secondary panels
    "scheme-2": scheme(
        bg=LSAGE, fg_heading=CREAM, fg=CREAM,
        btn_bg=DBROWN, btn_text=CREAM, btn_hover_bg=DBROWN_DIM,
        sec_btn_text=CREAM, sec_btn_border=CREAM,
    ),
    # scheme-3: tan — sold-out badge, accent chips
    "scheme-3": scheme(
        bg=TAN, fg_heading=CREAM, fg=CREAM,
        btn_bg=DBROWN, btn_text=CREAM, btn_hover_bg=DBROWN_DIM,
        sec_btn_text=CREAM, sec_btn_border=CREAM,
    ),
    # scheme-4: sage green — marquee strip
    "scheme-4": scheme(
        bg=SAGE, fg_heading=CREAM, fg=CREAM,
        btn_bg=DBROWN, btn_text=CREAM, btn_hover_bg=DBROWN_DIM,
        sec_btn_text=CREAM, sec_btn_border=CREAM,
    ),
    # scheme-5: dark brown — footer email signup, dark feature panels
    "scheme-5": scheme(
        bg=DBROWN, fg_heading=CREAM, fg=CREAM,
        btn_bg=SAGE, btn_text=CREAM, btn_hover_bg=SAGE_DIM,
        sec_btn_text=CREAM, sec_btn_border=CREAM,
    ),
    # scheme-6: light sage solid — hero section (no image yet)
    "scheme-6": scheme(
        bg=LSAGE, fg_heading=CREAM, fg=CREAM,
        btn_bg=DBROWN, btn_text=CREAM, btn_hover_bg=DBROWN_DIM,
        sec_btn_text=CREAM, sec_btn_border=CREAM,
        input_bg="#ffffff20", input_text=CREAM, input_border=CREAM+"80",
        sel_variant_bg=DBROWN, sel_variant_border=DBROWN,
    ),
}


def main():
    # download current settings_data
    r = httpx.get(f"{API}/themes/{THEME_ID}/assets.json", headers=H,
                  params={"asset[key]": "config/settings_data.json"}, timeout=30)
    data = json.loads(r.json()["asset"]["value"])

    # replace colour schemes
    data["current"]["color_schemes"].update(SCHEMES)

    # also update global button radius to be slightly softer
    data["current"]["button_border_radius_primary"]   = 8
    data["current"]["button_border_radius_secondary"] = 8
    data["current"]["card_corner_radius"]             = 8
    data["current"]["product_corner_radius"]          = 8
    data["current"]["badge_corner_radius"]            = 6

    new_value = json.dumps(data, indent=2)

    # save locally
    out = os.path.join(BASE, "config_settings_data.json")
    with open(out, "w", encoding="utf-8") as f:
        f.write(new_value)

    # push to theme
    rr = httpx.put(f"{API}/themes/{THEME_ID}/assets.json", headers=H, timeout=60,
                   json={"asset": {"key": "config/settings_data.json",
                                   "value": new_value}})
    print(f"PUT config/settings_data.json: {rr.status_code}",
          "" if rr.status_code == 200 else rr.text[:400])


if __name__ == "__main__":
    main()
