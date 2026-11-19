import unittest
from core.commands import normalize, parse_command

class CommandTests(unittest.TestCase):
    def test_persian_digits(self):
        self.assertEqual(normalize("۱۲۳۴۵"), "12345")
    def test_wake_search(self):
        self.assertEqual(parse_command("سلام آوا جستجو قیمت بیت کوین"),
                         {"action": "search", "value": "قیمت بیت کوین"})
    def test_lock(self):
        self.assertEqual(parse_command("آوا گوشی رو قفل کن")["action"], "lock")
    def test_call_number(self):
        self.assertEqual(parse_command("آوا به 09123456789 زنگ بزن")["value"], "09123456789")
    def test_call_name(self):
        self.assertEqual(parse_command("آوا به علی زنگ بزن")["value"], "علی")
    def test_sms(self):
        self.assertEqual(parse_command("آوا پیامک به علی بنویس سلام")["value"], "علی|سلام")
    def test_translation(self):
        self.assertEqual(parse_command("آوا ترجمه کن good morning")["action"], "translate")
    def test_https_validation(self):
        self.assertEqual(parse_command("آوا باز کن example.com")["value"], "https://example.com")
        self.assertEqual(parse_command("آوا باز کن javascript:alert(1)")["action"], "unsupported")
    def test_answer_call(self):
        self.assertEqual(parse_command("آوا پاسخ بده")["action"], "answer_call")
    def test_confirm_cancel(self):
        self.assertEqual(parse_command("بله")["action"], "yes")
        self.assertEqual(parse_command("نه")["action"], "no")
        self.assertEqual(parse_command("پیامک به نهال بنویس سلام")["action"], "sms")
        self.assertEqual(parse_command("به علی زنگ بزن")["action"], "call")
    def test_empty(self):
        self.assertEqual(parse_command("سلام آوا")["action"], "empty")

if __name__ == "__main__":
    unittest.main()
