# -*- coding: utf-8 -*-
import re
import threading
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
            hint_text: "کد زبان مقصد مثل en، fa، tr"
            multiline: False
        Button:
            text: "ترجمه"
            size_hint_x: 0.55
            on_release: app.translate_text()

    Label:
        id: result
        text: "آماده‌ام. برای فرمان صوتی دکمه میکروفون را بزن."
        halign: "center"
        valign: "middle"
        text_size: self.width - 20, None
"""

class PhoneAssistant(App):
    REQUEST_CODE = 731

    def build(self):
        self.title = "دستیار صوتی"
        self._activity_bound = False
        return Builder.load_string(KV)

    def say(self, text):
        self.root.ids.result.text = text
        if platform == "android":
            try:
                from plyer import tts
                tts.speak(text)
            except Exception:
                pass

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
                self.run_command()
        except Exception as exc:
            self.say("خطا در دریافت صدا: " + str(exc))

    def run_command(self):
        command = self.root.ids.command.text.strip()
        if not command:
            self.say("لطفاً فرمانت را بگو یا بنویس.")
            return
        numbers = re.findall(r'09\d{9}', command)
        if "تماس" in command:
            if numbers:
                self.open_dialer(numbers[0])
                self.say("شماره‌گیر باز شد؛ تماس را خودت تأیید کن.")
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

    def translate_text(self):
        source = self.root.ids.command.text.strip()
        target = self.root.ids.target.text.strip().lower() or "en"
        if not source:
            self.say("متنی برای ترجمه وارد کن.")
            return
        self.say("در حال ترجمه آنلاین...")
        threading.Thread(target=self._translate, args=(source, target), daemon=True).start()

    def _translate(self, source, target):
        try:
            url = "https://api.mymemory.translated.net/get?q=" + quote(source) + "&langpair=autodetect%7C" + quote(target)
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            if not translated:
                translated = "ترجمه‌ای دریافت نشد؛ کد زبان مقصد را بررسی کن."
        except Exception as exc:
            translated = "خطا در ترجمه آنلاین: " + str(exc)
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.say(translated), 0)

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
