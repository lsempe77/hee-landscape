"""Check funder identity, theme overlap and incomplete-input safeguards."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wellcome_builder", ROOT / "scripts" / "build_wellcome_analysis.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class WellcomeAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.patch = patch.object(builder, "DATA", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.temporary.cleanup)
        self.rows = [
            self.row("1", "Costs of treatment", "Burroughs-Wellcome Fund", "Infectious"),
            self.row("2", "Heat-related illness and mental health", "Wellcome; Wellcome Trust; NIH", "Infectious;Mental & substance use"),
            self.row("3", "Climate Schools anxiety prevention", "the Wellcome Trust and the Royal Society", "Mental & substance use", scope="multi_country"),
            self.row("4", "Universal Basic Income", "None reported", "NA"),
        ]
        (self.root / "dict.json").write_text(json.dumps({"meta": {"n_studies": 4, "years": [2010, 2026], "built": "2026-10-08"}}))
        (self.root / "content.json").write_text(json.dumps({"gallery": [{"figs": [{"file": "fig_funder_funders.webp"}]}]}))

    def row(self, rid, title, funders, disease, scope="single_country"):
        return {"record_id": rid, "is_eligible": "TRUE", "title": title, "year": "2020",
                "funders": funders, "income_broad": "High income", "geo_scope": scope,
                "disease_groups": disease, "url": "", "primary_topic": "Climate Change and Health Impacts"}

    def write_master(self):
        import csv
        with (self.root / "hee_analysis_master.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(self.rows[0]))
            writer.writeheader()
            writer.writerows(self.rows)

    def analysis(self):
        self.write_master()
        rows, meta, _, _, source_hash = builder.load_inputs(self.root)
        return rows, builder.build_analysis(rows, meta, source_hash)

    def test_separate_foundations_and_deduplicated_acknowledgements(self):
        rows, analysis = self.analysis()
        self.assertEqual(analysis["wellcome"]["n"], 2)
        donors = {d["funder"]: d for d in analysis["donors"]}
        self.assertEqual(donors["Burroughs Wellcome Fund"]["n"], 1)
        self.assertEqual(donors["Wellcome Trust"]["n"], 2)
        self.assertEqual(donors["Royal Society"]["n"], 1)
        self.assertEqual(donors["Wellcome Trust"]["income_counts"], [1, 0, 1])
        self.assertFalse(rows[3]["named_funders"])

    def test_theme_overlap_and_climate_false_positives(self):
        rows, analysis = self.analysis()
        self.assertEqual(analysis["themes"]["infectious"]["n"], 2)
        self.assertEqual(analysis["themes"]["mental"]["n"], 2)
        self.assertEqual(analysis["themes"]["climate"]["n"], 1)
        self.assertEqual(rows[1]["themes"], {"infectious", "mental", "climate"})
        self.assertNotIn("climate", rows[2]["themes"])
        self.assertNotIn("climate", rows[3]["themes"])
        for t in analysis["themes"].values():
            self.assertLessEqual(t["wellcome"], t["named_funder"])
            for d in t["donors"]:
                self.assertEqual(sum(d["income_counts"]), d["n"])

    def test_incomplete_dataset_is_rejected_without_touching_output(self):
        self.rows.pop()
        self.write_master()
        output = self.root / "fig_funder_funders.svg"
        output.write_text("existing figure")
        with self.assertRaisesRegex(ValueError, "does not match web data"):
            builder.load_inputs(self.root)
        self.assertEqual(output.read_text(), "existing figure")

    def test_duplicate_record_ids_are_rejected(self):
        self.rows[3]["record_id"] = "1"
        self.write_master()
        with self.assertRaisesRegex(ValueError, "unique"):
            builder.load_inputs(self.root)


if __name__ == "__main__":
    unittest.main()
