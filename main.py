# -*- coding: utf-8 -*-
import re
import threading
import socket
import ipaddress
from datetime import datetime
from urllib.parse import quote

import requests
from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform

KV = """
BoxLayout:
    orientation: "vertical"
    padding: 16
    spacing: 10

    Label:
        text: "دستیار صوتی هوشمند"
        font_size: "24sp"
        size_hint_y: None
        height: "52dp"

    TextInput:
        id: command
        hint_text: "فرمان یا متن برای ترجمه..."
        multiline: True
        size_hint_y: 0.24

    BoxLayout:
        size_hint_y: None
        height: "48dp"
        spacing: 8
        Button:
            text: "🎙 صحبت کن"
            on_release: app.listen()
        Button:
            text: "اجرا"
            on_release: app.run_command()
        Button:
            text: "🎧 ترجمه گفتار"
            on_release: app.listen_for_translation()

    Label:
        text: "ترجمه خودکار دوطرفه: زبان گوشی و زبان دوم را یک‌بار تنظیم کن؛ مترجم جهت ترجمه را از روی گفتار تشخیص می‌دهد."
        size_hint_y: None
        height: "52dp"
        halign: "center"
        valign: "middle"
        text_size: self.width - 20, None

    Label:
        text: "ترجمه آنلاین"
        size_hint_y: None
        height: "28dp"

    BoxLayout:
        size_hint_y: None
        height: "46dp"
        spacing: 8
        TextInput:
            id: target
            text: "en"
            hint_text: "زبان دوم مثل en، tr، ar"
            multiline: False
        Button:
            text: "ترجمه"
            size_hint_x: 0.55
            on_release: app.translate_text()

    Label:
        id: result
        text: "آماده‌ام. زبان گوشی و زبان دوم به‌صورت خودکار در دو جهت ترجمه می‌شوند."
        halign: "center"
        valign: "middle"
        text_size: self.width - 20, None
"""

class PhoneAssistant(App):
    REQUEST_CODE = 731

    def build(self):
        self.title = "دستیار صوتی"
        self._activity_bound = False
        self._translation_listen = False
        self.pending_call_number = None
        self._incoming_call_pending = False
        self._call_callback = None
        return Builder.load_string(KV)

    def on_start(self):
        self.start_incoming_call_monitor()

    def start_incoming_call_monitor(self):
        if platform != "android":
            return
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            from android.permissions import request_permissions

            class CallCallback(PythonJavaClass):
                __javainterfaces__ = ["org/example/phoneassistant/IncomingCallMonitor$Callback"]
                __javacontext__ = "app"

                def __init__(callback_self, app):
                    super().__init__()
                    callback_self.app = app

                @java_method("()V")
                def onIncomingCall(callback_self):
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt: callback_self.app.ask_to_answer_call(), 0)

                @java_method("()V")
                def onCallEnded(callback_self):
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt: setattr(callback_self.app, "_incoming_call_pending", False), 0)

            def on_permissions(permissions, grants):
                if not grants or not all(grants):
                    self.say("برای تشخیص تماس ورودی، مجوز تلفن لازم است.")
                    return
                try:
                    PythonActivity = autoclass("org.kivy.android.PythonActivity")
                    Monitor = autoclass("org.example.phoneassistant.IncomingCallMonitor")
                    self._call_callback = CallCallback(self)
                    Monitor.register(PythonActivity.mActivity, self._call_callback)
                except Exception as exc:
                    self.say("فعال‌سازی تشخیص تماس ناموفق بود: " + str(exc))

            request_permissions(["android.permission.READ_PHONE_STATE"], on_permissions)
        except Exception as exc:
            self.say("پایش تماس ورودی فعال نشد: " + str(exc))

    def ask_to_answer_call(self):
        if self._incoming_call_pending:
            return
        self._incoming_call_pending = True
        self.say("گوشی زنگ می‌خورد؛ اگر می‌خواهی پاسخ بدهم، بگو بله؛ برای هیچ اقدامی بگو نه.")
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.listen(), 1.8)

    def answer_incoming_call(self):
        if platform != "android":
            self.say("پاسخ تماس فقط روی گوشی اندرویدی ممکن است.")
            return
        try:
            from android.permissions import request_permissions
            from jnius import autoclass

            def on_permissions(permissions, grants):
                if not grants or not all(grants):
                    self.say("مجوز پاسخ‌دادن به تماس داده نشد.")
                    return
                try:
                    PythonActivity = autoclass("org.kivy.android.PythonActivity")
                    TelecomManager = autoclass("android.telecom.TelecomManager")
                    telecom = PythonActivity.mActivity.getSystemService("telecom")
                    telecom.acceptRingingCall()
                    self._incoming_call_pending = False
                    self.say("تماس پاسخ داده شد.")
                except Exception as exc:
                    self.say("پاسخ‌دادن به تماس ممکن نشد: " + str(exc))

            request_permissions(["android.permission.ANSWER_PHONE_CALLS"], on_permissions)
        except Exception as exc:
            self.say("خطا در پاسخ‌دادن به تماس: " + str(exc))

    def say(self, text):
        self.root.ids.result.text = text
        if platform == "android":
            try:
                from plyer import tts
                tts.speak(text)
            except Exception:
                pass

    def listen_for_translation(self):
        """Capture one spoken turn, translate it, and read the translation aloud."""
        self._translation_listen = True
        self.listen()

    def listen(self):
        if platform != "android":
            self.say("تشخیص صدا فقط روی گوشی اندرویدی فعال است.")
            return
        try:
            from jnius import autoclass
            from android import activity
            Intent = autoclass("android.content.Intent")
            RecognizerIntent = autoclass("android.speech.RecognizerIntent")
            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                           RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "صحبت کنید")
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, False)
            if not self._activity_bound:
                activity.bind(on_activity_result=self.on_activity_result)
                self._activity_bound = True
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            PythonActivity.mActivity.startActivityForResult(intent, self.REQUEST_CODE)
            self.say("در انتظار صدای شما...")
        except Exception as exc:
            self.say("فعال‌سازی میکروفون ناموفق بود: " + str(exc))

    def on_activity_result(self, request_code, result_code, data):
        if request_code != self.REQUEST_CODE or data is None:
            return
        try:
            from jnius import autoclass
            Activity = autoclass("android.app.Activity")
            if result_code != Activity.RESULT_OK:
                self.say("تشخیص صدا انجام نشد؛ دوباره تلاش کن.")
                return
            results = data.getStringArrayListExtra(
                "android.speech.extra.RESULTS")
            if results and results.size() > 0:
                text = str(results.get(0))
                self.root.ids.command.text = text
                if self._translation_listen:
                    self._translation_listen = False
                    self.translate_text(speak_result=True)
                else:
                    self.run_command()
        except Exception as exc:
            self.say("خطا در دریافت صدا: " + str(exc))

    def run_command(self):
        command = self.root.ids.command.text.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if not command:
            self.say("لطفاً فرمانت را بگو یا بنویس.")
            return
        if self._incoming_call_pending:
            answer = command.strip().lower()
            if any(word in answer for word in ("بله", "آره", "تأیید", "تایید", "yes")):
                self.answer_incoming_call()
            elif any(word in answer for word in ("نه", "خیر", "لغو", "cancel")):
                self._incoming_call_pending = False
                self.say("باشه؛ به تماس دست نمی‌زنم.")
            else:
                self.say("متوجه نشدم؛ فقط بگو بله یا نه.")
            return
        if self.pending_call_number:
            answer = command.strip().lower()
            if any(word in answer for word in ("بله", "آره", "تأیید", "تایید", "yes")):
                number = self.pending_call_number
                self.pending_call_number = None
                self.place_call(number)
            elif any(word in answer for word in ("نه", "خیر", "لغو", "cancel")):
                self.pending_call_number = None
                self.say("تماس لغو شد.")
            else:
                self.say("برای تماس بگو بله؛ برای لغو بگو نه.")
            return

        numbers = re.findall(r'(?:\+?\d[\d\s-]{7,16}\d)', command)
        if "تماس" in command or "زنگ" in command:
            if numbers:
                number = re.sub(r"[\\s-]", "", numbers[0])
                self.pending_call_number = number
                self.say("با شماره " + number + " تماس بگیرم؟ برای تأیید بگو بله؛ برای لغو بگو نه.")
            else:
                name = re.sub(r"^(لطفاً\\s*)?(با|به)?\\s*", "", command)
                name = re.sub(r"(تماس بگیرم?|زنگ بزنم?)$", "", name).strip()
                if name:
                    self.lookup_contact(name)
                else:
                    self.say("نام مخاطب یا شماره تلفن را بگو.")
        elif "پیام" in command or "پیامک" in command:
            if numbers:
                body = command.split("بنویس", 1)[-1].strip() if "بنویس" in command else ""
                self.open_sms(numbers[0], body)
                self.say("برنامه پیامک باز شد؛ متن را بررسی و ارسال کن.")
            else:
                self.say("شماره تلفن را هم بگو.")
        elif "جستجو" in command or "سرچ" in command:
            query = re.sub(r"^(لطفاً\\s*)?(جستجو|سرچ)(\\s+کن)?", "", command).strip()
            if query:
                self.open_web_search(query)
                self.say("در حال باز کردن نتایج جست‌وجو در مرورگر...")
            else:
                self.say("موضوع جست‌وجو را هم بگو.")
        elif "باز کن" in command or "وارد سایت" in command:
            address = re.sub(r"^(لطفاً\\s*)?(باز کن|وارد سایت)(\\s+شو)?", "", command).strip()
            if address:
                if not re.match(r"^https?://", address, re.I):
                    address = "https://" + address
                self.open_url(address)
                self.say("در حال باز کردن سایت در مرورگر...")
            else:
                self.say("نام سایت یا نشانی آن را بگو.")
        elif "بررسی امنیت سایت" in command or "تست امنیت سایت" in command:
            target = re.sub(r"^(بررسی امنیت سایت|تست امنیت سایت)\s*", "", command).strip()
            if not target:
                self.say("دامنه وب‌سایتی را وارد کن که مالک آن هستی یا اجازه بررسی‌اش را داری.")
            else:
                self.audit_website(target)
        elif "اسکن شبکه" in command or "بررسی شبکه" in command or "بررسی امنیت" in command:
            # Defensive scan limited to a private LAN CIDR explicitly supplied by the user.
            match = re.search(r"(?:اسکن شبکه|بررسی شبکه|بررسی امنیت)\\s+([0-9.]+/\\d{1,2})", command)
            if not match:
                self.say("برای بررسی شبکه محلی، محدوده خصوصی خودت را وارد کن؛ مثال: اسکن شبکه 192.168.1.0/24")
            else:
                self.scan_local_network(match.group(1))
        elif "ساعت" in command:
            self.say("ساعت " + datetime.now().strftime("%H:%M"))
        elif "ترجمه" in command:
            self.translate_text()
        elif "سلام" in command:
            self.say("سلام! آماده‌ام.")
        else:
            self.say("فرمان را دریافت کردم. برای ترجمه، متن را وارد کن و زبان مقصد را بنویس.")

    def scan_local_network(self, cidr):
        """Basic defensive TCP inventory of an explicitly supplied private LAN only."""
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            private_ranges = [ipaddress.ip_network("10.0.0.0/8"),
                              ipaddress.ip_network("172.16.0.0/12"),
                              ipaddress.ip_network("192.168.0.0/16")]
            if not any(network.subnet_of(private_net) for private_net in private_ranges):
                self.say("برای ایمنی فقط شبکه خصوصی محلی قابل بررسی است.")
                return
            if network.num_addresses > 256:
                self.say("محدوده خیلی بزرگ است؛ حداکثر ۲۵۶ نشانی را وارد کن.")
                return
        except ValueError:
            self.say("محدوده شبکه معتبر نیست. مثال: 192.168.1.0/24")
            return

        self.say("بررسی دفاعی شبکه محلی شروع شد؛ فقط چند پورت رایج بررسی می‌شوند...")
        threading.Thread(target=self._scan_local_network, args=(network,), daemon=True).start()

    def _scan_local_network(self, network):
        common_ports = (22, 53, 80, 443, 554, 8080)
        found = []
        for host in network.hosts():
            ip = str(host)
            open_ports = []
            for port in common_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.18)
                try:
                    if sock.connect_ex((ip, port)) == 0:
                        open_ports.append(port)
                except OSError:
                    pass
                finally:
                    sock.close()
            if open_ports:
                found.append(ip + ": " + ", ".join(str(p) for p in open_ports))
        if found:
            report = "دستگاه‌ها و پورت‌های پاسخ‌گو در شبکه محلی:\\n" + "\\n".join(found[:30])
        else:
            report = "در پورت‌های رایج بررسی‌شده، مورد بازی پیدا نشد."
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.say(report), 0)

    def audit_website(self, target):
        """Run non-invasive HTTP/TLS posture checks for an authorized website."""
        self.say("بررسی غیرتهاجمی امنیت وب‌سایت شروع شد...")
        def worker():
            try:
                from security_audit import audit_website
                report = audit_website(target)
            except Exception as exc:
                report = "بررسی انجام نشد: " + str(exc)
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.say(report), 0)
        threading.Thread(target=worker, daemon=True).start()

    def device_language(self):
        """Return the phone's language; Persian is the desktop/test fallback."""
        if platform == "android":
            try:
                from jnius import autoclass
                return str(autoclass("java.util.Locale").getDefault().getLanguage()).lower()
            except Exception:
                pass
        return "fa"

    def translate_text(self, speak_result=False):
        source = self.root.ids.command.text.strip()
        other_language = self.root.ids.target.text.strip().lower() or "en"
        if not source:
            self.say("متنی برای ترجمه وارد کن.")
            return
        if not re.fullmatch(r"[a-z]{2,3}(-[a-z]{2})?", other_language):
            self.say("کد زبان دوم معتبر نیست؛ مثل en یا tr وارد کن.")
            return
        phone_language = self.device_language()
        self.say("در حال تشخیص زبان و ترجمه آنلاین...")
        threading.Thread(
            target=self._translate,
            args=(source, phone_language, other_language, speak_result),
            daemon=True
        ).start()

    @staticmethod
    def detect_language(text):
        """Lightweight script-based language detection; avoids a native package."""
        if re.search(r"[\\u0600-\\u06FF]", text):
            return "fa" if re.search(r"[\\u067E\\u0686\\u0698\\u06AF]", text) or re.search(r"[\\u06A9\\u06CC]", text) else "ar"
        if re.search(r"[\\u0400-\\u04FF]", text):
            return "ru"
        return "en"

    def _translate(self, source, phone_language, other_language, speak_result=False):
        try:
            try:
                source_language = self.detect_language(source)
            except Exception:
                source_language = "unknown"

            # Translate between the phone language and the configured second language.
            if source_language == other_language.split("-")[0]:
                destination_language = phone_language
            elif source_language == phone_language:
                destination_language = other_language
            else:
                destination_language = phone_language

            source_pair = "autodetect" if source_language == "unknown" else source_language
            if source_pair != "autodetect" and source_pair == destination_language:
                translated = "زبان گفتار با زبان مقصد یکسان است."
            else:
                langpair = source_pair + "|" + destination_language
                url = ("https://api.mymemory.translated.net/get?q=" + quote(source)
                       + "&langpair=" + quote(langpair, safe="|"))
                response = requests.get(url, timeout=25)
                response.raise_for_status()
                data = response.json()
                result = data.get("responseData", {}).get("translatedText", "")
                if not result:
                    translated = "ترجمه‌ای دریافت نشد؛ این جفت‌زبان ممکن است پشتیبانی نشود."
                else:
                    translated = "ترجمه (" + source_pair + " به " + destination_language + "): " + result
        except Exception as exc:
            translated = "خطا در ترجمه آنلاین: " + str(exc)
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.say(translated), 0)

    def lookup_contact(self, name):
        """Find a saved contact by name and request confirmation before calling."""
        if platform != "android":
            self.say("جست‌وجوی مخاطبین فقط روی اندروید امکان‌پذیر است.")
            return
        try:
            from android.permissions import request_permissions, Permission
            def on_permissions(permissions, grants):
                if not grants or not all(grants):
                    self.say("مجوز مخاطبین داده نشد.")
                    return
                try:
                    from jnius import autoclass
                    PythonActivity = autoclass("org.kivy.android.PythonActivity")
                    Phone = autoclass("android.provider.ContactsContract$CommonDataKinds$Phone")
                    resolver = PythonActivity.mActivity.getContentResolver()
                    cursor = resolver.query(Phone.CONTENT_URI, None, None, None, None)
                    matches = []
                    if cursor:
                        name_col = cursor.getColumnIndex(Phone.DISPLAY_NAME)
                        number_col = cursor.getColumnIndex(Phone.NUMBER)
                        while cursor.moveToNext():
                            contact_name = str(cursor.getString(name_col) or "")
                            phone = str(cursor.getString(number_col) or "")
                            if name.lower() in contact_name.lower() and phone:
                                matches.append((contact_name, phone))
                        cursor.close()
                    if not matches:
                        self.say("مخاطبی با این نام پیدا نکردم.")
                    elif len(matches) > 1:
                        self.say("چند مخاطب پیدا شد؛ لطفاً نام کامل‌تری بگو.")
                    else:
                        contact_name, phone = matches[0]
                        self.pending_call_number = re.sub(r"[^+0-9]", "", phone)
                        self.say("با " + contact_name + " تماس بگیرم؟ برای تأیید بگو بله؛ برای لغو بگو نه.")
                except Exception as exc:
                    self.say("خواندن مخاطبین ناموفق بود: " + str(exc))
            request_permissions([Permission.READ_CONTACTS], on_permissions)
        except Exception as exc:
            self.say("دسترسی به مخاطبین ممکن نشد: " + str(exc))

    def place_call(self, number):
        if platform != "android":
            self.say("برقراری تماس فقط روی گوشی اندرویدی امکان‌پذیر است.")
            return
        try:
            from android.permissions import request_permissions, Permission
            from jnius import autoclass

            def on_permissions(permissions, grants):
                if grants and all(grants):
                    try:
                        Intent = autoclass("android.content.Intent")
                        Uri = autoclass("android.net.Uri")
                        intent = Intent(Intent.ACTION_CALL)
                        intent.setData(Uri.parse("tel:" + number))
                        self.open_android(intent)
                        from kivy.clock import Clock
                        Clock.schedule_once(lambda dt: self.say("در حال برقراری تماس با " + number), 0)
                    except Exception as exc:
                        from kivy.clock import Clock
                        Clock.schedule_once(lambda dt: self.say("برقراری تماس ناموفق بود: " + str(exc)), 0)
                else:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt: self.say("مجوز تماس داده نشد؛ تماس برقرار نشد."), 0)

            request_permissions([Permission.CALL_PHONE], on_permissions)
        except Exception as exc:
            self.say("امکان برقراری تماس وجود ندارد: " + str(exc))

    def open_web_search(self, query):
        self.open_url("https://www.google.com/search?q=" + quote(query))

    def open_url(self, address):
        """Open a normal HTTP(S) website in the Android browser."""
        if platform != "android":
            self.say("باز کردن سایت در مرورگر گوشی اندرویدی انجام می‌شود.")
            return
        if not re.match(r"^https?://", address, re.I):
            self.say("فقط نشانی‌های وب با http یا https مجاز هستند.")
            return
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(address))
            self.open_android(intent)
        except Exception as exc:
            self.say("باز کردن سایت ناموفق بود: " + str(exc))

    def open_dialer(self, number):
        if platform == "android":
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Intent.ACTION_DIAL)
            intent.setData(Uri.parse("tel:" + number))
            self.open_android(intent)

    def open_sms(self, number, body=""):
        if platform == "android":
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Intent.ACTION_SENDTO)
            intent.setData(Uri.parse("smsto:" + number))
            if body:
                intent.putExtra("sms_body", body)
            self.open_android(intent)

    def open_android(self, intent):
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        PythonActivity.mActivity.startActivity(intent)

if __name__ == "__main__":
    PhoneAssistant().run()
