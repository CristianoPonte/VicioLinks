import unittest
from urllib.parse import parse_qs, urlparse

from backend.app.utils import build_tracking_params, build_full_url


class TrackingParamsTests(unittest.TestCase):
    def test_captacao_keeps_utm_id_and_no_vendas_fields(self):
        params, src, sck, xcode = build_tracking_params(
            link_type="captacao",
            utm_source="instagram",
            utm_medium="feed",
            utm_campaign="campanha_2026",
            utm_content="bio",
            utm_term="cta_12-02-2026",
            utm_id="lnk_000123",
        )

        self.assertEqual(params["utm_id"], "lnk_000123")
        self.assertNotIn("xcode", params)
        self.assertNotIn("src", params)
        self.assertNotIn("sck", params)
        self.assertIsNone(src)
        self.assertIsNone(sck)
        self.assertIsNone(xcode)

    def test_vendas_replaces_utm_id_with_xcode_and_adds_src_sck(self):
        params, src, sck, xcode = build_tracking_params(
            link_type="vendas",
            utm_source="instagram",
            utm_medium="feed",
            utm_campaign="campanha_2026",
            utm_content="bio",
            utm_term="cta_12-02-2026",
            utm_id="lnk_000123",
        )

        self.assertNotIn("utm_id", params)
        self.assertEqual(params["xcode"], "lnk_000123")
        self.assertEqual(params["src"], "instagram_bio")
        self.assertEqual(params["sck"], "feed")
        self.assertEqual(src, "instagram_bio")
        self.assertEqual(sck, "feed")
        self.assertEqual(xcode, "lnk_000123")

    def test_vendas_url_contains_all_capture_utms_except_utm_id(self):
        params, _, _, _ = build_tracking_params(
            link_type="vendas",
            utm_source="email",
            utm_medium="newsletter",
            utm_campaign="lanc_0226",
            utm_content="lista_atual",
            utm_term="sequencia_12-02-2026",
            utm_id="lnk_000999",
        )
        full_url = build_full_url("https://lp.exemplo.com", "/checkout", params, {})
        parsed = parse_qs(urlparse(full_url).query)

        self.assertEqual(parsed.get("utm_source"), ["email"])
        self.assertEqual(parsed.get("utm_medium"), ["newsletter"])
        self.assertEqual(parsed.get("utm_campaign"), ["lanc_0226"])
        self.assertEqual(parsed.get("utm_content"), ["lista_atual"])
        self.assertEqual(parsed.get("utm_term"), ["sequencia_12-02-2026"])
        self.assertEqual(parsed.get("xcode"), ["lnk_000999"])
        self.assertEqual(parsed.get("src"), ["email_lista_atual"])
        self.assertEqual(parsed.get("sck"), ["newsletter"])
        self.assertNotIn("utm_id", parsed)


if __name__ == "__main__":
    unittest.main()
