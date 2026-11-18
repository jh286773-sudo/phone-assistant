

import re
import webbrowser

from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform
from kivy.core.window import Window

KV = """
BoxLayout:
    orientation: "vertical"
    padding: 20
    spacing: 15

    Label:
        text: "دستیار هوشمند فارسی"
        font_size: "25sp"
        size_hint_y: 0.2

    TextInput:
        id: command
        hint_text: "مثلاً تماس با شماره 09123456789"
        multiline: False
        size_hint_y: 0.15

    Button:
        text: "اجرا"
        size_hint_y: 0.15
        on_release: app.run_command()

    Label:
        id: result
        text: "آماده دریافت فرمان"
        halign: "center"
        size_hint_y: 0.3
"""


class PhoneAssistant(App):

    def build(self):
        self.title = "دستیار فارسی"
        return Builder.load_string(KV)

    def run_command(self):
        command = self.root.ids.command.text.strip()
        result = self.root.ids.result

        numbers = re.findall(r'09\d{9}', command)

        if "تماس" in command:
            if numbers:
                self.open_dialer(numbers[0])
                result.text = "شماره‌گیر باز شد."
            else:
                result.text = "شماره تلفن را وارد کن."

        elif "پیام" in command or "پیامک" in command:
            if numbers:
                self.open_sms(numbers[0])
                result.text = "برنامه پیامک باز شد."
            else:
                result.text = "شماره تلفن را وارد کن."

        elif "سلام" in command:
            result.text = "سلام! آماده انجام فرمان هستم."

        elif "ساعت" in command:
            from datetime import datetime
            result.text = datetime.now().strftime("%H:%M")

        else:
            result.text = "این فرمان را هنوز یاد نگرفته‌ام."

    def open_dialer(self, number):
        if platform == "android":
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Intent.ACTION_DIAL)
            intent.setData(Uri.parse("tel:" + number))
            self.open_android(intent)

    def open_sms(self, number):
        if platform == "android":
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Intent.ACTION_SENDTO)
            intent.setData(Uri.parse("smsto:" + number))
            self.open_android(intent)

    def open_android(self, intent):
        from jnius import autoclass
        PythonActivity = autoclass(
            "org.kivy.android.PythonActivity"
        )
        PythonActivity.mActivity.startActivity(intent)


if __name__ == "__main__":
    PhoneAssistant().run()
