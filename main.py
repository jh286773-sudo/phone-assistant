# -*- coding: utf-8 -*-
"""Ava Persian Android assistant."""
import threading
from urllib.parse import quote

from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock

from core.commands import parse_command, normalize
from core.translation import translate
from core.crypto import price

KV = """
BoxLayout:
    orientation: "vertical"
    padding: "12dp"
    spacing: "7dp"
    Label:
        text: "آوا | دستیار صوتی"
        font_size: "23sp"
        size_hint_y: None
        height: "42dp"
    TextInput:
        id: command
        hint_text: "فرمان را بنویس یا با صدا بگو…"
        multiline: False
        size_hint_y: None
        height: "46dp"
    BoxLayout:
        size_hint_y: None
        height: "44dp"
        spacing: "6dp"
        Button:
            text: "اجرا"
            on_release: app.execute_command()
        Button:
            text: "🎙 شنیدن"
            on_release: app.listen_once()
        Button:
            id: wake_button
            text: "شنود دائمی: روشن/خاموش"
            on_release: app.toggle_wake_service()
    BoxLayout:
        size_hint_y: None
        height: "40dp"
        spacing: "6dp"
        TextInput:
            id: target_lang
            text: "en"
            hint_text: "زبان دوم (en/tr/ar)"
            multiline: False
        Button:
            text: "ترجمه متن"
            on_release: app.translate_current()
        Button:
            text: "ترجمه گفتار"
            on_release: app.listen_for_translation()
    Label:
        id: status
        text: "آماده‌ام. برای فعال‌سازی شنود دائمی، مجوز میکروفون را بده."
        halign: "center"
        valign: "middle"
        text_size: self.width - 16, None
    Label:
        id: hint
        text: "تماس و پیامک پس از تأیید شما باز می‌شوند؛ ارسال نهایی با خود شماست."
        font_size: "12sp"
        halign: "center"
        text_size: self.width - 16, None
"""

class AvaApp(App):
    def build(self):
        self.title = "Ava"
        self.pending = None
        self._wake_enabled = False
        self._speech_mode = "command"
        self._speech_bound = False
        self._call_callback = None
        return Builder.load_string(KV)

    def on_start(self):
        Clock.schedule_interval(self._poll_service_message, 0.7)
        self._consume_intent()
        self._start_call_monitor()

    def on_stop(self):
        try:
            from android import activity
            if self._speech_bound:
                activity.unbind(on_activity_result=self._on_speech_result)
        except Exception:
            pass

    def say(self, message):
        self.root.ids.status.text = message
        if platform == "android":
            try:
                from plyer import tts
                tts.speak(message)
            except Exception:
                pass

    def _activity(self):
        from jnius import autoclass
        return autoclass("org.kivy.android.PythonActivity").mActivity

    def _consume_intent(self):
        if platform != "android":
            return
        try:
            activity = self._activity()
            intent = activity.getIntent()
            phrase = intent.getStringExtra("ava_command")
            if phrase:
                intent.removeExtra("ava_command")
                activity.setIntent(intent)
                activity.getSharedPreferences("ava_wake", 0).edit().remove("pending_command").apply()
                self.root.ids.command.text = str(phrase)
                self.execute_command()
        except Exception:
            pass

    def _poll_service_message(self, _dt):
        if platform != "android":
            return
        try:
            prefs = self._activity().getSharedPreferences("ava_wake", 0)
            phrase = prefs.getString("pending_command", "")
            if phrase:
                prefs.edit().remove("pending_command").apply()
                self.root.ids.command.text = str(phrase)
                self.execute_command()
        except Exception:
            pass

    def toggle_wake_service(self):
        if self._wake_enabled:
            self.stop_wake_service()
            return
        if platform != "android":
            self.say("شنود پس‌زمینه فقط روی اندروید فعال است.")
            return
        try:
            from android.permissions import request_permissions, Permission
            def granted(_perms, results):
                if not results or not all(results):
                    self.say("مجوز میکروفون لازم است.")
                    return
                try:
                    from jnius import autoclass
                    Intent = autoclass("android.content.Intent")
                    Service = autoclass("org.example.phoneassistant.AvaWakeService")
                    intent = Intent(self._activity(), Service)
                    intent.setAction("START")
                    if int(autoclass("android.os.Build$VERSION").SDK_INT) >= 26:
                        self._activity().startForegroundService(intent)
                    else:
                        self._activity().startService(intent)
                    self._wake_enabled = True
                    self.root.ids.wake_button.text = "خاموش کردن شنود"
                    self.say("شنود فعال شد؛ اعلان آوا نمایش داده می‌شود.")
                except Exception as exc:
                    self.say("شروع سرویس ناموفق بود: " + str(exc))
            request_permissions([Permission.RECORD_AUDIO], granted)
        except Exception as exc:
            self.say("درخواست مجوز ناموفق بود: " + str(exc))

    def stop_wake_service(self):
        if platform != "android":
            return
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Service = autoclass("org.example.phoneassistant.AvaWakeService")
            intent = Intent(self._activity(), Service)
            intent.setAction("STOP")
            self._activity().startService(intent)
            self._wake_enabled = False
            self.root.ids.wake_button.text = "فعال‌سازی شنود دائمی"
            self.say("شنود دائمی خاموش شد.")
        except Exception as exc:
            self.say("توقف سرویس ناموفق بود: " + str(exc))

    def listen_once(self):
        self._speech_mode = "command"
        self._request_speech()

    def listen_for_translation(self):
        self._speech_mode = "translate"
        self._request_speech()

    def _request_speech(self):
        if platform != "android":
            self.say("تشخیص گفتار فقط روی اندروید در دسترس است.")
            return
        try:
            from android.permissions import request_permissions, Permission
            def granted(_p, results):
                if not results or not all(results):
                    self.say("مجوز میکروفون داده نشد.")
                    return
                try:
                    from jnius import autoclass
                    from android import activity
                    Intent = autoclass("android.content.Intent")
                    RI = autoclass("android.speech.RecognizerIntent")
                    intent = Intent(RI.ACTION_RECOGNIZE_SPEECH)
                    intent.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM)
                    intent.putExtra(RI.EXTRA_LANGUAGE, "fa-IR")
                    intent.putExtra(RI.EXTRA_MAX_RESULTS, 1)
                    if not self._speech_bound:
                        activity.bind(on_activity_result=self._on_speech_result)
                        self._speech_bound = True
                    self._activity().startActivityForResult(intent, 731)
                    self.say("گوش می‌دهم…")
                except Exception as exc:
                    self.say("تشخیص گفتار شروع نشد: " + str(exc))
            request_permissions([Permission.RECORD_AUDIO], granted)
        except Exception as exc:
            self.say("خطای مجوز میکروفون: " + str(exc))

    def _on_speech_result(self, request_code, result_code, data):
        if request_code != 731:
            return
        try:
            from android import activity
            if self._speech_bound:
                activity.unbind(on_activity_result=self._on_speech_result)
                self._speech_bound = False
            if data is None:
                self.say("صدایی دریافت نشد.")
                return
            results = data.getStringArrayListExtra("android.speech.extra.RESULTS")
            if not results or not results.size():
                self.say("گفتار تشخیص داده نشد.")
                return
            self.root.ids.command.text = str(results.get(0))
            if self._speech_mode == "translate":
                self.translate_current()
            else:
                self.execute_command()
        except Exception as exc:
            self.say("خطا در دریافت گفتار: " + str(exc))

    def execute_command(self):
        parsed = parse_command(self.root.ids.command.text)
        action, value = parsed["action"], parsed["value"]
        if self.pending:
            if action == "yes":
                pending = self.pending
                self.pending = None
                self._execute_confirmed(pending)
            elif action == "no":
                self.pending = None
                self.say("لغو شد.")
            else:
                self.say("برای تأیید بگو بله؛ برای لغو بگو نه.")
            return
        if action == "empty":
            self.say("فرمانت را بگو.")
        elif action in ("yes", "no"):
            self.say("درخواستی برای تأیید وجود ندارد.")
        elif action == "search":
            self._open_url("https://www.google.com/search?q=" + quote(value))
            self.say("نتایج جستجو باز شد.")
        elif action == "website":
            if value:
                self._open_url(value)
            else:
                self.say("نشانی سایت معتبر نیست؛ فقط HTTPS پشتیبانی می‌شود.")
        elif action == "lock":
            self._lock_device()
        elif action == "home":
            self._go_home()
        elif action == "back":
            self.say("برای بازگشت از دکمه بازگشت گوشی استفاده کن.")
        elif action == "call":
            self._resolve_contact(value)
        elif action == "sms":
            name, body = value.split("|", 1)
            self._resolve_contact(name, mode="sms", body=body)
        elif action == "translate":
            self._translate_async(value)
        elif action == "crypto":
            self._crypto_async(value)
        elif action == "answer_call":
            self.pending = {"kind": "answer"}
            self.say("آیا تماس ورودی را پاسخ بدهم؟ بگو بله یا نه.")
        elif action == "reject_call":
            self.say("رد تماس از طریق برنامه تلفن گوشی انجام می‌شود.")
        else:
            self.say("این فرمان را نشناختم. جستجو، تماس، پیامک، ترجمه یا قفل گوشی را امتحان کن.")

    def _execute_confirmed(self, pending):
        if pending["kind"] == "call":
            self._open_dialer(pending["number"])
        elif pending["kind"] == "sms":
            self._open_sms(pending["number"], pending["body"])
        elif pending["kind"] == "answer":
            self._answer_incoming_call()

    def _resolve_contact(self, query, mode="call", body=""):
        normalized = normalize(query)
        digits = "".join(c for c in normalized if c.isdigit())
        if len(digits) >= 8:
            number = "".join(c for c in normalized if c.isdigit() or c == "+")
            self._confirm_contact_action(number, mode, body)
            return
        if platform != "android":
            self.say("جستجوی مخاطب فقط روی اندروید انجام می‌شود.")
            return
        try:
            from android.permissions import request_permissions, Permission
            def granted(_p, results):
                if not results or not all(results):
                    self.say("مجوز مخاطبین داده نشد.")
                    return
                try:
                    from jnius import autoclass
                    Phone = autoclass("android.provider.ContactsContract$CommonDataKinds$Phone")
                    cursor = self._activity().getContentResolver().query(Phone.CONTENT_URI, None, None, None, None)
                    matches = []
                    if cursor:
                        name_col = cursor.getColumnIndex(Phone.DISPLAY_NAME)
                        number_col = cursor.getColumnIndex(Phone.NUMBER)
                        while cursor.moveToNext():
                            name = str(cursor.getString(name_col) or "")
                            number = str(cursor.getString(number_col) or "")
                            if normalized.casefold() in name.casefold():
                                matches.append((name, number))
                        cursor.close()
                    if not matches:
                        self.say("مخاطبی با این نام پیدا نکردم.")
                    elif len(matches) > 1:
                        self.say("چند مخاطب پیدا شد؛ لطفاً نام کامل‌تری بگو.")
                    else:
                        self._confirm_contact_action(matches[0][1], mode, body, matches[0][0])
                except Exception as exc:
                    self.say("خواندن مخاطبین ناموفق بود: " + str(exc))
            request_permissions([Permission.READ_CONTACTS], granted)
        except Exception as exc:
            self.say("دسترسی مخاطبین ناموفق بود: " + str(exc))

    def _confirm_contact_action(self, number, mode, body="", name=""):
        self.pending = {"kind": mode, "number": number, "body": body}
        verb = "تماس بگیرم" if mode == "call" else "پیامک را آماده کنم"
        self.say("با " + (name or number) + " " + verb + "؟ برای تأیید بگو بله.")

    def _open_dialer(self, number):
        self._launch_intent("android.intent.action.DIAL", "tel:" + number)
        self.say("شماره در شماره‌گیر باز شد؛ برای برقراری تماس دکمه تماس را بزن.")

    def _open_sms(self, number, body):
        if platform != "android":
            self.say("پیامک فقط روی گوشی باز می‌شود.")
            return
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Intent.ACTION_SENDTO)
            intent.setData(Uri.parse("smsto:" + number))
            intent.putExtra("sms_body", body)
            self._activity().startActivity(intent)
            self.say("پیامک آماده شد؛ ارسال نهایی با تأیید خودت انجام می‌شود.")
        except Exception as exc:
            self.say("بازکردن پیامک ناموفق بود: " + str(exc))

    def _launch_intent(self, action, uri):
        if platform != "android":
            self.say("این قابلیت فقط روی اندروید در دسترس است.")
            return
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        intent = Intent(action)
        intent.setData(Uri.parse(uri))
        self._activity().startActivity(intent)

    def _open_url(self, url):
        try:
            self._launch_intent("android.intent.action.VIEW", url)
        except Exception as exc:
            self.say("بازکردن پیوند ناموفق بود: " + str(exc))

    def _go_home(self):
        if platform == "android":
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                intent = Intent(Intent.ACTION_MAIN)
                intent.addCategory(Intent.CATEGORY_HOME)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                self._activity().startActivity(intent)
            except Exception as exc:
                self.say("بازگشت به صفحه اصلی ناموفق بود: " + str(exc))

    def _lock_device(self):
        if platform != "android":
            self.say("قفل گوشی فقط در اندروید ممکن است.")
            return
        try:
            from jnius import autoclass
            activity = self._activity()
            component = autoclass("android.content.ComponentName")(
                activity, autoclass("org.example.phoneassistant.AvaDeviceAdminReceiver").class_)
            manager = activity.getSystemService("device_policy")
            if not manager.isAdminActive(component):
                Intent = autoclass("android.content.Intent")
                Policy = autoclass("android.app.admin.DevicePolicyManager")
                intent = Intent(Policy.ACTION_ADD_DEVICE_ADMIN)
                intent.putExtra(Policy.EXTRA_DEVICE_ADMIN, component)
                intent.putExtra(Policy.EXTRA_ADD_EXPLANATION, "برای اجرای فرمان قفل گوشی، آوا به مجوز مدیر دستگاه نیاز دارد.")
                activity.startActivity(intent)
                self.say("صفحه فعال‌سازی مدیر دستگاه باز شد؛ آوا را فعال کن و دوباره فرمان قفل را بگو.")
                return
            manager.lockNow()
            self.say("گوشی قفل شد.")
        except Exception as exc:
            self.say("قفل گوشی ممکن نشد: " + str(exc))

    def _start_call_monitor(self):
        if platform != "android":
            return
        try:
            from android.permissions import request_permissions, Permission
            from jnius import autoclass, PythonJavaClass, java_method
            app = self
            class Callback(PythonJavaClass):
                __javainterfaces__ = ["org/example/phoneassistant/IncomingCallMonitor$Callback"]
                __javacontext__ = "app"
                @java_method("()V")
                def onIncomingCall(self):
                    Clock.schedule_once(lambda _dt: app._incoming_call_notice(), 0)
                @java_method("()V")
                def onCallEnded(self):
                    Clock.schedule_once(lambda _dt: app.say("تماس پایان یافت."), 0)
            def granted(_p, results):
                if results and all(results):
                    try:
                        self._call_callback = Callback()
                        autoclass("org.example.phoneassistant.IncomingCallMonitor").register(self._activity(), self._call_callback)
                    except Exception as exc:
                        self.say("پایش تماس فعال نشد: " + str(exc))
            request_permissions([Permission.READ_PHONE_STATE], granted)
        except Exception:
            pass

    def _incoming_call_notice(self):
        self.pending = {"kind": "answer"}
        self.say("تماس ورودی داری. برای پاسخ‌دادن بگو بله؛ برای لغو بگو نه.")

    def _answer_incoming_call(self):
        if platform != "android":
            self.say("پاسخ تماس فقط روی اندروید ممکن است.")
            return
        try:
            from android.permissions import request_permissions
            def granted(_p, results):
                if not results or not all(results):
                    self.say("مجوز پاسخ تماس داده نشد؛ از صفحه تماس استفاده کن.")
                    return
                try:
                    from jnius import autoclass
                    telecom = self._activity().getSystemService("telecom")
                    telecom.acceptRingingCall()
                    self.say("درخواست پاسخ تماس ارسال شد.")
                except Exception as exc:
                    self.say("اندروید اجازه پاسخ خودکار نداد: " + str(exc))
            request_permissions(["android.permission.ANSWER_PHONE_CALLS"], granted)
        except Exception as exc:
            self.say("پاسخ تماس ممکن نشد: " + str(exc))

    def translate_current(self):
        self._translate_async(self.root.ids.command.text)

    def _translate_async(self, text):
        target = self.root.ids.target_lang.text.strip() or "en"
        self.say("در حال ترجمه…")
        def work():
            try:
                result = translate(text, target)
                Clock.schedule_once(lambda _dt, value=result: self._translation_done(value), 0)
            except Exception as exc:
                message = str(exc)
                Clock.schedule_once(lambda _dt, value=message: self.say("ترجمه ناموفق بود: " + value), 0)
        threading.Thread(target=work, daemon=True).start()

    def _translation_done(self, result):
        self.root.ids.command.text = result
        self.say(result)

    def _crypto_async(self, query):
        self.say("در حال دریافت قیمت ارز…")
        def work():
            try:
                coin, value, currency = price(query)
                message = coin + ": " + str(value) + " " + currency.upper()
                Clock.schedule_once(lambda _dt, value=message: self.say(value), 0)
            except Exception as exc:
                message = str(exc)
                Clock.schedule_once(lambda _dt, value=message: self.say("دریافت قیمت ناموفق بود: " + value), 0)
        threading.Thread(target=work, daemon=True).start()

if __name__ == "__main__":
    AvaApp().run()
