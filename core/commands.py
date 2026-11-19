"""Deterministic Persian command parsing, independent of Android."""
import re
from urllib.parse import urlparse

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
YES = ("بله", "آره", "تایید", "تأیید", "yes", "ok")
NO = ("نه", "خیر", "لغو", "cancel", "no")

def normalize(text):
    text = (text or "").translate(_DIGITS).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    return re.sub(r"\s+", " ", text).strip()

def _url(value):
    value = value.strip()
    candidate = value if "://" in value else "https://" + value
    parsed = urlparse(candidate)
    if parsed.scheme != "https" or not parsed.hostname or "." not in parsed.hostname:
        return None
    if parsed.username or parsed.password:
        return None
    return candidate

def parse_command(text):
    command = normalize(text)
    command = re.sub(r"^(?:سلام\s+)?آوا[،, ]*", "", command).strip()
    low = command.lower()
    if not command:
        return {"action": "empty", "value": ""}
    if any(w in low for w in YES):
        return {"action": "yes", "value": ""}
    if any(w in low for w in NO):
        return {"action": "no", "value": ""}
    if any(x in command for x in ("پاسخ بده", "جواب بده", "تماس را جواب", "تماس رو جواب")):
        return {"action": "answer_call", "value": ""}
    if any(x in command for x in ("رد تماس", "قطع تماس ورودی")):
        return {"action": "reject_call", "value": ""}
    if any(x in command for x in ("قفل کن", "قفلش کن", "صفحه را قفل", "گوشی رو قفل")):
        return {"action": "lock", "value": ""}
    if any(x in command for x in ("صفحه رو ببند", "برنامه رو ببند", "برو صفحه اصلی")):
        return {"action": "home", "value": ""}
    if any(x in command for x in ("بازگشت", "برگرد عقب", "برو عقب")):
        return {"action": "back", "value": ""}
    m = re.match(r"^(?:جستجو|سرچ)(?: کن)?\s+(.+)$", command)
    if m:
        return {"action": "search", "value": m.group(1).strip()}
    m = re.match(r"^(?:باز کن|وارد سایت)\s+(.+)$", command)
    if m:
        url = _url(m.group(1))
        return {"action": "website", "value": url} if url else {"action": "unsupported", "value": command}
    m = re.match(r"^(?:ترجمه کن|ترجمه)\s+(.+)$", command)
    if m:
        return {"action": "translate", "value": m.group(1).strip()}
    m = re.match(r"^(?:پیامک|پیام)\s+(?:به\s+)?(.+?)\s+(?:بنویس|بفرست)\s+(.+)$", command)
    if m:
        return {"action": "sms", "value": m.group(1).strip() + "|" + m.group(2).strip()}
    m = re.search(r"(?:با|به)\s+(.+?)\s+(?:تماس بگیر|زنگ بزن)", command)
    if m:
        return {"action": "call", "value": m.group(1).strip()}
    m = re.search(r"(?:با|به)\s*(\+?[0-9][0-9 -]{6,18}[0-9])\s*(?:تماس بگیر|زنگ بزن)", command)
    if m:
        return {"action": "call", "value": re.sub(r"[ -]", "", m.group(1))}
    if "قیمت" in command and any(x in command.lower() for x in ("بیت کوین", "bitcoin", "اتریوم", "ethereum")):
        return {"action": "crypto", "value": command}
    return {"action": "unsupported", "value": command}
