import unittest

from trp2_attack_profiles import PROFILES


class TRP2AttackProfileTests(unittest.TestCase):
    def test_profile_capabilities_are_explicit(self):
        self.assertFalse(PROFILES["A0"].code_copy)
        self.assertTrue(PROFILES["A3"].snapshot)
        self.assertFalse(PROFILES["A3"].signing_key)
        self.assertTrue(PROFILES["A5"].signing_key)
        self.assertTrue(PROFILES["A6"].registry_influence)


if __name__ == "__main__":
    unittest.main()
