"""Publication language for the Explorer's language filter.

Reads each eligible study's `language` (the language code in its CrossRef
record) from the team export and writes docs/data/languages.json:

  levels  language names, most studies first ("Not recorded" last)
  n       studies per language
  code    one entry per study (in studies.json order): index into levels

Codes that are not a plausible publication language (CrossRef's "ng") are
shown as "Unclear code". The map is almost entirely English-language: this
reflects how studies were searched, not the wider literature.

Usage:
    python scripts/build_language_filter.py [--raw data/raw]
"""
import argparse
import csv
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "docs", "data")
NAMES = {"en": "English", "de": "German", "es": "Spanish", "fr": "French", "ko": "Korean", "pt": "Portuguese",
         "fa": "Persian", "ja": "Japanese", "nl": "Dutch", "hu": "Hungarian", "it": "Italian", "ru": "Russian",
         "zh": "Chinese", "tr": "Turkish", "pl": "Polish"}
NOT_RECORDED, UNCLEAR = "Not recorded", "Unclear code"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"))
    args = ap.parse_args()
    csv.field_size_limit(10 ** 9)

    with open(os.path.join(DATA, "studies.json"), encoding="utf-8") as f:
        ids = [str(r) for r in json.load(f)["record_id"]]
    lang = {}
    with open(os.path.join(args.raw, "hee_analysis_master_v2.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["is_eligible"] == "TRUE":
                code = r["language"].strip().lower()
                lang[r["record_id"]] = NOT_RECORDED if code in ("", "na") else NAMES.get(code, UNCLEAR)
    missing = [i for i in ids if i not in lang]
    if missing:
        raise SystemExit(f"{len(missing)} web studies are not eligible records in the export, e.g. {missing[:3]}")

    per = [lang[i] for i in ids]
    counts = Counter(per)
    levels = sorted(counts, key=lambda k: (k in (NOT_RECORDED, UNCLEAR), k == NOT_RECORDED, -counts[k], k))
    pos = {k: i for i, k in enumerate(levels)}
    out = {"levels": levels, "n": [counts[k] for k in levels], "code": [pos[k] for k in per]}
    path = os.path.join(DATA, "languages.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"wrote {path}: " + ", ".join(f"{k} {counts[k]:,}" for k in levels))


if __name__ == "__main__":
    main()
