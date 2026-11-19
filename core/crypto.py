"""Read-only public crypto price lookup using CoinGecko's public API."""
import requests

COINS = {"بیت کوین": "bitcoin", "bitcoin": "bitcoin", "btc": "bitcoin",
         "اتریوم": "ethereum", "ethereum": "ethereum", "eth": "ethereum",
         "تتر": "tether", "usdt": "tether"}

def price(query, currency="usd"):
    q = (query or "").lower()
    coin = next((v for k, v in COINS.items() if k in q), None)
    if not coin:
        raise ValueError("فعلاً بیت‌کوین، اتریوم و تتر پشتیبانی می‌شوند.")
    currency = (currency or "usd").lower()
    if currency not in ("usd", "eur", "try", "irr"):
        raise ValueError("واحد قیمت پشتیبانی نمی‌شود.")
    r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                     params={"ids": coin, "vs_currencies": currency},
                     headers={"accept": "application/json"}, timeout=(5, 15))
    r.raise_for_status()
    value = r.json().get(coin, {}).get(currency)
    if value is None:
        raise RuntimeError("قیمت از سرویس دریافت نشد.")
    return coin, value, currency
