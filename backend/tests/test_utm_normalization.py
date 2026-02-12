import unittest

from backend.app.utils import normalize_campaign, normalize_utm_term


class UTMNormalizationTests(unittest.TestCase):
    def test_campaign_normalizes_mm_yy_suffix(self):
        self.assertEqual(normalize_campaign("vde1f_90d_evento_0124"), "vde1f_90d_evento_01-24")
        self.assertEqual(normalize_campaign("vde1f_90d_evento_01-24"), "vde1f_90d_evento_01-24")

    def test_term_normalizes_dd_mm_yyyy_suffix(self):
        self.assertEqual(normalize_utm_term("aaa_12022026"), "aaa_12-02-2026")
        self.assertEqual(normalize_utm_term("aaa_12-02-2026"), "aaa_12-02-2026")


if __name__ == "__main__":
    unittest.main()
