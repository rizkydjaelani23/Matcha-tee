"""
Phase 5: Create SEO blog articles targeting real search intent.
Renames the default blog, publishes 6 keyword-optimised posts with internal links,
and sets SEO title/description metafields on each.
"""
import os, sys, json, time
import httpx
from dotenv import load_dotenv
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
STORE = os.environ["SHOPIFY_STORE"]
TOKEN = os.environ["SHOPIFY_TOKEN"]
RH    = {"X-Shopify-Access-Token": TOKEN}
H     = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
API   = f"https://{STORE}/admin/api/2025-01"
GQL   = f"https://{STORE}/admin/api/2025-01/graphql.json"
BASE  = "https://thematchatee.com"

# ── 1. rename the default 'News' blog to something topical ────────────────────
blogs = httpx.get(f"{API}/blogs.json", headers=RH, timeout=15).json().get("blogs", [])
blog = blogs[0]
blog_id = blog["id"]
httpx.put(f"{API}/blogs/{blog_id}.json", headers=H,
          json={"blog": {"id": blog_id, "title": "Style Guide", "handle": "style-guide"}}, timeout=20)
print(f"Blog -> 'Style Guide' (id {blog_id})")

# ── 2. articles ───────────────────────────────────────────────────────────────
ARTICLES = [
{
 "title": "The Best Vintage Celebrity T-Shirts to Wear in 2026",
 "tags": "vintage tees, celebrity shirts, style",
 "seo_title": "Best Vintage Celebrity T-Shirts 2026 | The Matcha Tee",
 "seo_desc": "Discover the best vintage celebrity t-shirts to wear in 2026 — from retro film icons to music legends. Soft cotton, unisex fit, fast UK delivery.",
 "body": """
<p>Vintage celebrity t-shirts are having a major moment in 2026. What started as a niche corner of streetwear has become one of the most-searched styles in fashion — and for good reason. A great <a href="{base}/collections/t-shirts">vintage graphic tee</a> instantly signals taste, nostalgia and personality, all from a single piece of soft cotton.</p>
<h2>Why vintage celebrity tees are so popular right now</h2>
<p>The appeal is simple: these shirts tell a story. Whether it's a retro photo print of a film legend or a faded-look band graphic, a vintage celebrity tee feels personal in a way that a plain logo never will. They pair effortlessly with denim, cargos or a blazer, and they work just as well dressed up or down.</p>
<h2>The icons people are wearing in 2026</h2>
<p>Across our <a href="{base}/collections/best-sellers">best sellers</a>, a few themes keep coming back: golden-age film stars, music legends, and cult TV characters. These designs resonate because they're recognisable yet unexpected — a conversation starter without saying a word.</p>
<h2>How to choose the right one</h2>
<p>Pick a design that genuinely means something to you — a film you love, an artist you grew up on, a character you quote constantly. Authenticity always reads better than trend-chasing. Then make sure the fit and fabric are right: our tees use premium, garment-dyed cotton with a relaxed unisex cut for that lived-in feel from day one.</p>
<p>Ready to find yours? Browse the latest <a href="{base}/collections/new-releases">new releases</a> or explore the full <a href="{base}/collections/t-shirts">t-shirt collection</a> at The Matcha Tee.</p>
"""
},
{
 "title": "How to Style Vintage Graphic Tees: 7 Outfit Ideas",
 "tags": "style, outfit ideas, graphic tees",
 "seo_title": "How to Style Vintage Graphic Tees: 7 Outfits | The Matcha Tee",
 "seo_desc": "Learn how to style vintage graphic tees with 7 easy outfit ideas — from smart-casual to streetwear. Tips for layering, fit and colour. The Matcha Tee.",
 "body": """
<p>A <a href="{base}/collections/t-shirts">vintage graphic tee</a> is one of the most versatile things you can own. The trick is knowing how to wear it. Here are seven simple, repeatable outfit ideas that work for almost everyone.</p>
<h2>1. The classic: tee + straight denim</h2>
<p>You can't beat a graphic tee tucked loosely into straight-leg jeans and clean trainers. It's the foundation everything else builds on.</p>
<h2>2. Smart-casual with a blazer</h2>
<p>Throw an unstructured blazer over your tee for instant polish. The contrast between a relaxed graphic and tailored layer is what makes it work.</p>
<h2>3. Layered over a long sleeve</h2>
<p>In cooler weather, layer your tee over a plain long-sleeve top. It adds depth and lets you wear your favourite graphics year-round.</p>
<h2>4. Tucked into trousers</h2>
<p>Swap denim for pleated or wide-leg trousers and tuck the tee in for a more elevated, intentional look.</p>
<h2>5. Streetwear with cargos</h2>
<p>Oversized tee, cargo trousers, chunky trainers. Effortless and modern.</p>
<h2>6. Under a <a href="{base}/collections/hoodies-sweatshirts">sweatshirt or hoodie</a></h2>
<p>Let just the hem and collar of your tee peek out from under a crewneck for a subtle layered finish.</p>
<h2>7. Dressed down with shorts</h2>
<p>In summer, a vintage tee and tailored shorts is the easiest warm-weather uniform there is.</p>
<p>Build your rotation from our <a href="{base}/collections/best-sellers">best-selling tees</a> — premium cotton, unisex fit, fast UK delivery.</p>
"""
},
{
 "title": "Comfort Colors vs Standard Tees: Which Should You Buy?",
 "tags": "buyer guide, comfort colors, fabric",
 "seo_title": "Comfort Colors vs Standard Tees: Which Is Better? | The Matcha Tee",
 "seo_desc": "Comfort Colors vs standard t-shirts — what's the real difference? We break down fabric weight, fit, dye and feel to help you choose. The Matcha Tee.",
 "body": """
<p>If you've shopped for vintage-style tees, you've seen the term "Comfort Colors." But what actually makes them different from a standard t-shirt, and are they worth it? Here's the honest breakdown.</p>
<h2>What is a Comfort Colors tee?</h2>
<p>Comfort Colors are garment-dyed, heavyweight cotton tees known for their soft, broken-in feel and rich, slightly faded colours. They're dyed after being sewn, which gives each piece a subtle, lived-in character.</p>
<h2>Fabric weight and feel</h2>
<p>Standard tees are usually lighter and crisper. Garment-dyed heavyweight tees feel substantial and soft from the first wear — closer to a tee you've owned and loved for years.</p>
<h2>Fit</h2>
<p>Garment-dyed tees tend to have a relaxed, slightly boxy fit that suits the vintage aesthetic. Standard tees run closer to a classic fit. Our <a href="{base}/collections/t-shirts">vintage graphic tees</a> use the relaxed, unisex cut on purpose — it's what makes a retro print look right.</p>
<h2>Colour and longevity</h2>
<p>The garment-dye process gives deeper, more characterful colour that ages beautifully. Prints sit into the fabric rather than on top of it, so they feel and look more authentic over time.</p>
<h2>So which should you buy?</h2>
<p>If you want that genuine vintage feel — soft, heavyweight, lived-in — garment-dyed is the way to go. That's exactly what we use across the range. Explore our <a href="{base}/collections/best-sellers">best sellers</a> to feel the difference.</p>
"""
},
{
 "title": "What Makes a Great Vintage Graphic Tee? A Buyer's Guide",
 "tags": "buyer guide, vintage tees, quality",
 "seo_title": "What Makes a Great Vintage Graphic Tee? Buyer's Guide | The Matcha Tee",
 "seo_desc": "A buyer's guide to vintage graphic tees — what to look for in fabric, print quality, fit and design before you buy. Tips from The Matcha Tee.",
 "body": """
<p>Not all graphic tees are created equal. If you're investing in a <a href="{base}/collections/t-shirts">vintage graphic tee</a>, here's what separates a great one from a forgettable one.</p>
<h2>1. Print quality</h2>
<p>The best vintage prints have a soft hand-feel and a slightly distressed finish that looks authentically retro — not a stiff, plasticky block sitting on top of the fabric.</p>
<h2>2. Fabric</h2>
<p>Look for premium, garment-dyed cotton. It's softer, heavier and ages better than cheap blends. This is the single biggest factor in how a tee feels and lasts.</p>
<h2>3. Fit</h2>
<p>A relaxed, unisex cut suits the vintage look and flatters more body types. Too tight and it loses the aesthetic; too baggy and it loses shape.</p>
<h2>4. Design that means something</h2>
<p>The best tees feature designs you genuinely connect with — an icon, era or reference that's personal to you. That's what makes a shirt a favourite instead of a one-time wear.</p>
<h2>5. The brand behind it</h2>
<p>Buy from a store that stands behind the product with clear sizing, easy returns and responsive support. At The Matcha Tee, every order ships fast across the UK with hassle-free 30-day returns.</p>
<p>Put it into practice — browse our <a href="{base}/collections/new-releases">latest drops</a> and find a tee worth keeping.</p>
"""
},
{
 "title": "Unisex T-Shirt Sizing Guide: How to Get the Perfect Fit",
 "tags": "sizing, buyer guide, fit",
 "seo_title": "Unisex T-Shirt Sizing Guide | Perfect Fit | The Matcha Tee",
 "seo_desc": "Our unisex t-shirt sizing guide helps you get the perfect fit every time. How unisex sizing works, how to measure and how to choose. The Matcha Tee.",
 "body": """
<p>Unisex sizing is brilliant for vintage tees — it gives you that relaxed, slightly oversized look the style is known for. But it can be confusing if you're used to men's or women's cuts. Here's how to get it right.</p>
<h2>How unisex sizing works</h2>
<p>Unisex tees are based on a classic men's-style block. If you prefer a fitted look, consider sizing down. If you want the relaxed, vintage drape, stick to your usual size or size up.</p>
<h2>How to measure</h2>
<p>Take a t-shirt you already love and lay it flat. Measure the chest (armpit to armpit) and the length (shoulder to hem). Compare those numbers to the size chart on each product page — it's the most reliable way to choose.</p>
<h2>Fit preferences</h2>
<ul>
<li><strong>Fitted look:</strong> size down one.</li>
<li><strong>True relaxed fit:</strong> your normal size.</li>
<li><strong>Oversized/vintage drape:</strong> size up one.</li>
</ul>
<h2>Still unsure?</h2>
<p>Message us before you order and we'll help you pick — it's faster than guessing. Browse the <a href="{base}/collections/t-shirts">full t-shirt range</a> and check the size chart on any product page.</p>
"""
},
{
 "title": "The History of the Bootleg Rap Tee & Vintage Band Shirts",
 "tags": "history, vintage tees, culture",
 "seo_title": "History of the Bootleg Rap Tee & Vintage Band Shirts | The Matcha Tee",
 "seo_desc": "The story behind bootleg rap tees and vintage band shirts — how they started, why they exploded, and why they're collectable today. The Matcha Tee.",
 "body": """
<p>The vintage graphic tee has roots that run deeper than fashion. To understand why these shirts feel so iconic, it helps to know where they came from.</p>
<h2>The rise of the band shirt</h2>
<p>Concert and band tees became cultural artefacts in the 1970s and 80s — proof you were there, worn until they faded and softened into something personal. That worn-in look is exactly what the vintage aesthetic celebrates today.</p>
<h2>The bootleg rap tee era</h2>
<p>In the 1990s, unofficial "bootleg" rap and celebrity tees exploded — bold photo collages, mixed fonts and high-contrast graphics. They were raw, expressive and instantly recognisable, and they've become some of the most collectable designs in streetwear.</p>
<h2>Why they're loved today</h2>
<p>Modern <a href="{base}/collections/t-shirts">vintage graphic tees</a> carry that same energy: nostalgic, characterful and a little rebellious. The difference now is quality — premium garment-dyed cotton and prints designed to look authentically retro without falling apart.</p>
<h2>Wear a piece of the story</h2>
<p>Our designs are a love letter to that era. Explore the <a href="{base}/collections/best-sellers">best sellers</a> or the <a href="{base}/collections/new-releases">newest drops</a> and find a tee with a story worth wearing.</p>
"""
},
]

# ── 3. create articles + set SEO metafields ───────────────────────────────────
MUT = """mutation set($mf: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $mf) { metafields { id } userErrors { field message } }
}"""

created = 0
for a in ARTICLES:
    body_html = a["body"].format(base=BASE).strip()
    payload = {"article": {
        "title": a["title"],
        "author": "The Matcha Tee",
        "tags": a["tags"],
        "body_html": body_html,
        "published": True,
    }}
    r = httpx.post(f"{API}/blogs/{blog_id}/articles.json", headers=H, json=payload, timeout=30)
    if r.status_code not in (200, 201):
        print(f"  FAIL create '{a['title'][:40]}': {r.status_code} {r.text[:160]}")
        continue
    art = r.json()["article"]
    aid = art["id"]
    # SEO metafields
    oid = f"gid://shopify/Article/{aid}"
    mf = [
        {"ownerId": oid, "namespace": "global", "key": "title_tag",
         "type": "single_line_text_field", "value": a["seo_title"]},
        {"ownerId": oid, "namespace": "global", "key": "description_tag",
         "type": "single_line_text_field", "value": a["seo_desc"]},
    ]
    httpx.post(GQL, headers=H, json={"query": MUT, "variables": {"mf": mf}}, timeout=30)
    created += 1
    print(f"  + {a['title']}")
    time.sleep(0.5)

print(f"\nBlog done. {created} articles published at {BASE}/blogs/style-guide")
