import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DenominatorAuditTests(unittest.TestCase):
    def setUp(self):
        self.audit = json.loads((ROOT / "docs/data/denominator_audit.json").read_text(encoding="utf-8"))

    def test_pair_reconciliation_across_distinct_country_sets(self):
        c = self.audit["counts"]
        self.assertEqual(c["full_geography_pairs"] - sum(self.audit["national_gbd_excluded_pairs"].values()), c["national_gbd_pairs"])
        self.assertEqual(c["website_pairs"] - self.audit["national_gbd_excluded_pairs"]["HKG"], c["website_burden_pairs"])
        self.assertLess(set(self.audit["country_sets"]["website_burden"]), set(self.audit["country_sets"]["national_gbd"]))

    def test_inequality_marker_uses_real_cumulative_coordinate(self):
        x = self.audit["inequality"]
        self.assertGreater(x["least_served_burden_share"], .5)
        self.assertAlmostEqual(x["least_served_evidence_share"], x["least_served_pairs"] / x["pairs"])
        self.assertLess(x["interpolated_evidence_share_at_half"], x["least_served_evidence_share"])
        self.assertNotEqual(set(x["top_study_countries"]), set(x["top_burden_countries"]))

    def test_gallery_captions_and_replacement_assets_agree(self):
        data = ROOT / "docs/data"
        content = json.loads((data / "content.json").read_text(encoding="utf-8"))
        copy = json.loads((data / "figure_copy.json").read_text(encoding="utf-8"))
        updates = json.loads((data / "figure_updates.json").read_text(encoding="utf-8"))
        entries = {f["file"]: f for section in content["gallery"] for f in section["figs"]}
        for file in ["fig_deficit.webp", "fig_inequality.webp", "fig_reach_time.webp"]:
            self.assertEqual(entries[file]["caption"], updates[file]["caption"])
            self.assertEqual(copy[file]["caption"], updates[file]["caption"])
            self.assertTrue((ROOT / "docs/figures" / updates[file]["file"]).is_file())
        # A later income-only rebuild must preserve these non-income updates.
        self.assertIn("paper05.webp", updates)


if __name__ == "__main__":
    unittest.main()
