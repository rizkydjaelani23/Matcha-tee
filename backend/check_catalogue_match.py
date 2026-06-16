import csv, json, os, re

def norm(s):
    return re.sub(r'[^a-z0-9 ]', '', (s or '').lower().split(',')[0].strip())

with open(os.path.join(os.path.dirname(__file__), '../scraper/catalogue.csv'), encoding='utf-8') as f:
    catalogue = list(csv.DictReader(f))

cp = json.load(open(os.path.join(os.path.dirname(__file__), 'full_checkpoint.json'), encoding='utf-8'))
seen, products = set(), []
for v in cp.values():
    if v.get('status') != 'done' or not v.get('new_shopify_id'): continue
    t = (v.get('title') or '').strip().lower()
    if t in seen: continue
    seen.add(t)
    products.append(v)

cat_norm = {norm(r['TITLE']): r for r in catalogue}

matched = unmatched = 0
for p in products:
    pn = norm(p['title'])
    row = cat_norm.get(pn)
    if row:
        img1 = row.get('IMAGE1_LOCAL', '')
        has_local = os.path.exists(img1) if img1 else False
        has_url   = bool(row.get('IMAGE1_URL', ''))
        matched += 1
        src = 'local' if has_local else ('url' if has_url else 'NONE')
        print(f"  OK [{src}] {p['title'][:50]}")
    else:
        title = p['title']
        print(f'  NO MATCH: {title[:55]}')
        unmatched += 1

print(f'\nMatched: {matched}/{len(products)}  Unmatched: {unmatched}')
