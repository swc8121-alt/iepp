from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from azure_cvm_attester import AzureCvmAttesterError, _validate_maa_issuer


class AzureCvmAttesterTests(unittest.TestCase):
    def test_accepts_expected_azure_attestation_issuer(self):
        self.assertEqual(
            _validate_maa_issuer("https://sharedkrc.krc.attest.azure.net/"),
            "https://sharedkrc.krc.attest.azure.net",
        )

    def test_rejects_non_azure_or_url_with_credentials_and_path(self):
        invalid = (
            "http://sharedkrc.krc.attest.azure.net",
            "https://attacker.invalid",
            "https://user@sharedkrc.krc.attest.azure.net",
            "https://sharedkrc.krc.attest.azure.net/other",
        )
        for issuer in invalid:
            with self.subTest(issuer=issuer), self.assertRaises(AzureCvmAttesterError):
                _validate_maa_issuer(issuer)


if __name__ == "__main__":
    unittest.main()
