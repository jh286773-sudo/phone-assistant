# -*- coding: utf-8 -*-
"""Non-invasive security posture checks for websites the user owns or is authorized to assess."""
import ipaddress
import socket
from urllib.parse import urlparse

import requests


def audit_website(target):
    target = target.strip()
    if not target.startswith(("https://", "http://")):
        target = "https://" + target
    parsed = urlparse(target)
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        raise ValueError("نشانی وب معتبر نیست.")

    host = parsed.hostname
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except OSError:
        raise ValueError("دامنه پیدا نشد یا DNS پاسخ نداد.")
    if not addresses:
        raise ValueError("نشانی IP برای دامنه پیدا نشد.")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("برای جلوگیری از دسترسی به شبکه‌های داخلی، این مقصد مجاز نیست.")

    response = requests.get(
        target, timeout=12, allow_redirects=False,
        headers={"User-Agent": "PhoneAssistant-SecurityCheck/1.0"}
    )
    headers = {key.lower(): value for key, value in response.headers.items()}
    checks = []
    checks.append(("HTTPS", "مناسب" if parsed.scheme == "https" else "نیازمند اصلاح"))
    checks.append(("HSTS", "فعال" if "strict-transport-security" in headers else "یافت نشد"))
    checks.append(("Content-Security-Policy", "فعال" if "content-security-policy" in headers else "یافت نشد"))
    checks.append(("X-Content-Type-Options", "فعال" if "x-content-type-options" in headers else "یافت نشد"))
    checks.append(("X-Frame-Options", "فعال" if "x-frame-options" in headers or "content-security-policy" in headers else "یافت نشد"))
    checks.append(("وضعیت HTTP", str(response.status_code)))
    if "server" in headers:
        checks.append(("Server header", "نمایش داده می‌شود"))
    else:
        checks.append(("Server header", "نمایش داده نمی‌شود"))
    if 300 <= response.status_code < 400:
        checks.append(("تغییر مسیر", "سایت تغییر مسیر می‌دهد؛ مقصد جداگانه بررسی شود"))

    lines = ["گزارش بررسی غیرتهاجمی " + host]
    lines.extend(name + ": " + value for name, value in checks)
    lines.append("این بررسی محدود به پاسخ HTTP و هدرهای امنیتی است؛ آزمون بهره‌برداری انجام نشده.")
    return "\n".join(lines)
