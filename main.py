# -*- coding: utf-8 -*-
import re
import threading
from datetime import datetime
from urllib.parse import quote

import requests
from langdetect import detect
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
        return Builder.load_string(KV)

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
        command = self.root.ids.command.text.strip()
        if not command:
            self.say("لطفاً فرمانت را بگو یا بنویس.")
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
                number = re.sub(r"[\s-]", "", numbers[0])
                self.pending_call_number = number
                self.say("با شماره " + number + " تماس بگیرم؟ برای تأیید بگو بله؛ برای لغو بگو نه.")
            else:
                self.say("شماره تلفن را هم بگو.")
        elif "پیام" in command or "پیامک" in command:
            if numbers:
                body = command.split("بنویس", 1)[-1].strip() if "بنویس" in command else ""
                self.open_sms(numbers[0], body)
                self.say("برنامه پیامک باز شد؛ متن را بررسی و ارسال کن.")
            else:
                self.say("شماره تلفن را هم بگو.")
        elif "ساعت" in command:
            self.say("ساعت " + datetime.now().strftime("%H:%M"))
        elif "ترجمه" in command:
            self.translate_text()
        elif "سلام" in command:
            self.say("سلام! آماده‌ام.")
        else:
            self.say("فرمان را دریافت کردم. برای ترجمه، متن را وارد کن و زبان مقصد را بنویس.")

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

    def _translate(self, source, phone_language, other_language, speak_result=False):
        try:
            try:
                source_language = detect(source).lower().split("-")[0]
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
