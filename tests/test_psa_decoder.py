import unittest
import importlib.util
import sys
from pathlib import Path


def load_psa_decoder_module():
    """Import the legacy PSA decoder from its current mia-agents location."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "orchestration"
        / "mia-agents"
        / "agents"
        / "psa_decoder.py"
    )
    spec = importlib.util.spec_from_file_location("mia_agents_psa_decoder", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


psa_decoder = load_psa_decoder_module()


class TestPsaDecoder(unittest.TestCase):

    def test_decode_soot_mass(self):
        # Example: 21 01 -> hex data 1234
        # clean_hex = "1234" -> 0x1234 = 4660
        # Result = 4660 / 100 = 46.60
        
        # Test valid hex response (simulating "41 21 12 34")
        # The decoder logic as implemented expects the caller to strip prefix or handles cleanup if " " present
        # But looking at psa_decoder.py, it takes first 4 chars.
        
        # If input is just data bytes "1234"
        self.assertAlmostEqual(psa_decoder.decode_soot_mass("1234"), 46.60)
        
        # If input has spaces "12 34"
        self.assertAlmostEqual(psa_decoder.decode_soot_mass("12 34"), 46.60)
        
        # If input is invalid
        self.assertEqual(psa_decoder.decode_soot_mass("ZZ"), 0.0)

    def test_decode_oil_temp(self):
        # Example: 21 02 -> hex data 50
        # 0x50 = 80
        # Result = 80 - 40 = 40 deg C
        
        self.assertAlmostEqual(psa_decoder.decode_oil_temp("50"), 40.0)
        self.assertAlmostEqual(psa_decoder.decode_oil_temp("28"), 0.0)  # 0x28 = 40 -> 0C
    
    def test_decode_eolys_level(self):
        # Example: 0x64 = 100
        # 100% -> 100 * 0.03 = 3 Liters
        
        pct, liters = psa_decoder.decode_eolys_level("64")
        self.assertEqual(pct, 100.0)
        self.assertEqual(liters, 3.0)

    def test_decode_dpf_status(self):
        # 0x00 -> Normal
        self.assertEqual(psa_decoder.decode_dpf_status("00"), 0)
        # 0x01 -> Regenerating
        self.assertEqual(psa_decoder.decode_dpf_status("01"), 1)
        # 0x02 -> Warning
        self.assertEqual(psa_decoder.decode_dpf_status("02"), 2)


if __name__ == '__main__':
    unittest.main()
