"""Pure command parsing; kept Android-independent for reliable unit tests."""
import re
from urllib.parse import urlparse

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def normalize(text):
    text = (text or "").translate(_DIGITS).replace("ي", "ی").replace("ك", "ک")
    text = text.replace("\u200c", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def parse_command(text):
    command = normalize(text)
    command = re.sub(r"^(?:سلام\s+)?آوا[،, ]*", "", command).strip()
    if not command:
        return {"action": "empty", "value": ""}
    if any(x in command for x in ("قفل کن", "قفلش کن", "صفحه را قفل", "گوشی رو قفل")):
        return {"action": "lock", "value": ""}
    if any(x in command for x in ("بازگشت", "برگرد عقب", "برو عقب")):
        return {"action": "back", "value": ""}
    if command.startswith(("جستجو", "سرچ")):
        value = re.sub(r"^(جستجو|سرچ)( کن)?\s*", "", command).strip()
        return {"action": "search", "value": value} if value else {"action": "empty", "value": ""}
    if "تماس" in command or "زنگ بزن" in command:
        match = re.search(r"\+?[0-9][0-9 -]{6,18}[0-9]", command)
        return {"action": "call", "value": re.sub(r"[ -]", "", match.group(0))} if match else {"action": "unsupported", "value": command}
    if command.startswith(("باز کن ", "وارد سایت ")):
        value = command.split(" ", 1)[1].strip()
        candidate = value if "://" in value else "https://" + value
        parsed = urlparse(candidate)
        if parsed.scheme == "https" and parsed.hostname and "." in parsed.hostname and not parsed.username and not parsed.password:
            return {"action": "website", "value": candidate}
    return {"action": "unsupported", "value": command}
