import unittest
from core.commands import normalize, parse_command

class CommandTests(unittest.TestCase):
    def test_persian_digits(self):
        self.assertEqual(normalize("۱۲۳۴۵"), "12345")

    def test_wake_prefix_and_search(self):
        self.assertEqual(parse_command("سلام آوا جستجو قیمت بیت کوین"),
                         {"action": "search", "value": "قیمت بیت کوین"})

    def test_lock(self):
        self.assertEqual(parse_command("آوا گوشی رو قفل کن")["action"], "lock")

    def test_call_number(self):
        self.assertEqual(parse_command("آوا به 09123456789 زنگ بزن")["value"], "09123456789")

    def test_reject_javascript_url(self):
        self.assertEqual(parse_command("آوا باز کن javascript:alert(1)")["action"], "unsupported")

    def test_empty(self):
        self.assertEqual(parse_command("سلام آوا")["action"], "empty")

if __name__ == "__main__":
    unittest.main()
