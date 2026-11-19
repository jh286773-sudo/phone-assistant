# -*- coding: utf-8 -*-
"""Ava: Persian Android assistant. Android-only integrations are isolated."""
from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from core.commands import parse_command

KV = """
BoxLayout:
    orientation: "vertical"
    padding: "14dp"
    spacing: "8dp"
    Label:
        text: "آوا | دستیار صوتی"
        font_size: "24sp"
        size_hint_y: None
        height: "52dp"
    TextInput:
        id: command
        hint_text: "مثلاً: آوا جستجو وضعیت هوا"
        multiline: False
        size_hint_y: None
        height: "48dp"
    BoxLayout:
        size_hint_y: None
        height: "48dp"
        spacing: "8dp"
        Button:
            text: "اجرا"
            on_release: app.execute_command()
        Button:
            text: "شنیدن فرمان"
            on_release: app.listen_once()
    Label:
        id: status
        text: "آماده‌ام. برای فرمان صوتی، دکمه شنیدن را بزن."
        halign: "center"
        valign: "middle"
        text_size: self.width - 20, None
"""

class AvaApp(App):
    def build(self):
        self.title = "Ava"
        self.pending_call = None
        return Builder.load_string(KV)

    def say(self, message):
        self.root.ids.status.text = message
        if platform == "android":
            try:
                from plyer import tts
                tts.speak(message)
            except Exception:
                pass

    def listen_once(self):
        if platform != "android":
            self.say("تشخیص گفتار فقط در نسخه اندروید در دسترس است.")
            return
        try:
            from android.permissions import request_permissions, Permission
            def granted(_permissions, grants):
                if not grants or not all(grants):
                    self.say("مجوز میکروفون داده نشد.")
                    return
                self._launch_recognizer()
            request_permissions([Permission.RECORD_AUDIO], granted)
        except Exception as exc:
            self.say("دسترسی میکروفون ناموفق بود: " + str(exc))

    def _launch_recognizer(self):
        try:
            from jnius import autoclass
            from android import activity
            Intent = autoclass("android.content.Intent")
            RecognizerIntent = autoclass("android.speech.RecognizerIntent")
            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "fa-IR")
            activity.bind(on_activity_result=self._on_speech_result)
            self._speech_bound = True
            autoclass("org.kivy.android.PythonActivity").mActivity.startActivityForResult(intent, 731)
            self.say("گوش می‌دهم…")
        except Exception as exc:
            self.say("راه‌اندازی تشخیص گفتار ناموفق بود: " + str(exc))

    def _on_speech_result(self, request_code, result_code, data):
        if request_code != 731:
            return
        try:
            from android import activity
            if getattr(self, "_speech_bound", False):
                activity.unbind(on_activity_result=self._on_speech_result)
                self._speech_bound = False
            if data is None:
                self.say("صدایی دریافت نشد.")
                return
            values = data.getStringArrayListExtra("android.speech.extra.RESULTS")
            if values and values.size():
                self.root.ids.command.text = str(values.get(0))
                self.execute_command()
            else:
                self.say("گفتار قابل تشخیص نبود.")
        except Exception as exc:
            self.say("خطا در دریافت گفتار: " + str(exc))

    def execute_command(self):
        parsed = parse_command(self.root.ids.command.text)
        action = parsed["action"]
        value = parsed["value"]
        if action == "empty":
            self.say("فرمانت را بنویس یا بگو.")
        elif action == "search":
            self._open_url("https://www.google.com/search?q=" + __import__("urllib.parse").parse.quote(value))
            self.say("نتایج جستجو باز شد.")
        elif action == "website":
            self._open_url(value)
        elif action == "lock":
            self._lock_device()
        elif action == "call":
            self.pending_call = value
            self.say("برای تماس با " + value + "، دوباره شماره را بررسی کن و دکمه اجرا را پس از تأیید خودت بزن.")
        elif action == "back":
            self.say("برای بازگشت از دکمه بازگشت اندروید استفاده کن.")
        else:
            self.say("این فرمان هنوز پشتیبانی نمی‌شود.")

    def _open_url(self, url):
        if platform != "android":
            self.say("بازکردن پیوند فقط روی اندروید انجام می‌شود.")
            return
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            autoclass("org.kivy.android.PythonActivity").mActivity.startActivity(intent)
        except Exception as exc:
            self.say("بازکردن پیوند ناموفق بود: " + str(exc))

    def _lock_device(self):
        if platform != "android":
            self.say("قفل‌کردن گوشی فقط در اندروید ممکن است.")
            return
        try:
            from jnius import autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            component = autoclass("android.content.ComponentName")(
                activity, autoclass("org.example.phoneassistant.AvaDeviceAdminReceiver").class_)
            manager = activity.getSystemService("device_policy")
            if not manager.isAdminActive(component):
                self.say("ابتدا باید مدیر دستگاه آوا را از تنظیمات فعال کنی.")
                return
            manager.lockNow()
            self.say("گوشی قفل شد.")
        except Exception as exc:
            self.say("قفل‌کردن گوشی ممکن نشد: " + str(exc))

if __name__ == "__main__":
    AvaApp().run()
