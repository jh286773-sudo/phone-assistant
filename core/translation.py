"""Small online translation client with explicit timeout and bounded input."""
import requests

API = "https://api.mymemory.translated.net/get"

def is_persian(text):
    return any("\u0600" <= c <= "\u06ff" for c in text)

def translate(text, target_language="en"):
    text = (text or "").strip()
    target_language = (target_language or "en").strip().lower()
    if not text:
        raise ValueError("متنی برای ترجمه وارد نشده است.")
    if len(text) > 4500:
        raise ValueError("متن برای ترجمه بیش از حد طولانی است.")
    if not target_language.isalpha() or len(target_language) not in (2, 3):
        raise ValueError("کد زبان مقصد معتبر نیست.")
    pair = "fa|" + target_language if is_persian(text) else target_language + "|fa"
    response = requests.get(API, params={"q": text, "langpair": pair}, timeout=(5, 15))
    response.raise_for_status()
    payload = response.json()
    result = payload.get("responseData", {}).get("translatedText")
    if not result:
        raise RuntimeError("سرویس ترجمه پاسخی برنگرداند.")
    return result
