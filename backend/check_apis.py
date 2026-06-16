import httpx, sys
sys.stdout.reconfigure(encoding="utf-8")

print("== open.er-api.com (GBP rates) ==")
d = httpx.get("https://open.er-api.com/v6/latest/GBP", timeout=20).json()
print("  result:", d.get("result"))
print("  GBP->USD:", d["rates"].get("USD"))
print("  GBP->EUR:", d["rates"].get("EUR"))
print("  last update:", d.get("time_last_update_utc"))

print("\n== get.geojs.io (country by IP) ==")
g = httpx.get("https://get.geojs.io/v1/ip/country.json", timeout=20).json()
print("  ", g)

print("\n== sample conversion ==")
gbp = 27.00
usd = gbp * d["rates"]["USD"]
eur = gbp * d["rates"]["EUR"]
print(f"  GBP {gbp:.2f}  ->  USD {usd:.2f}  /  EUR {eur:.2f}")
