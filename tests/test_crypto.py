import unittest
from core.crypto import COINS

class CryptoTests(unittest.TestCase):
    def test_supported_aliases(self):
        self.assertEqual(COINS["btc"], "bitcoin")
        self.assertEqual(COINS["اتریوم"], "ethereum")
