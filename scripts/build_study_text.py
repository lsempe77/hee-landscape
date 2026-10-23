"""Build the title and abstract files the Explorer download reads.

The download used to take titles from the per-country drill shards, so the
studies naming no country (about 11,000) had a blank title. This script writes
the title and abstract of every study on the site, from the analysis master,
in fixed-size chunks by site study index:

  docs/data/text/index.json    {"n", "chunk", "files", "bytes", "source"}
  docs/data/text/NNN.json      {"start", "t": [titles], "a": [abstracts]}

Whitespace is collapsed (the master keeps some non-breaking spaces the drill
titles do not); text is otherwise unchanged. Existing chunk files are replaced.

Run: python scripts/build_study_text.py [--master data/raw/hee_analysis_master_v2_who.csv]
"""
import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = ROOT / "docs" / "data"
OUT = SITE_DATA / "text"
CHUNK = 2000


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", default=str(ROOT / "data" / "raw" / "hee_analysis_master_v2_who.csv"))
    args = parser.parse_args()
    master_path = Path(args.master)

    ids = json.loads((SITE_DATA / "studies.json").read_text(encoding="utf-8"))["record_id"]
    csv.field_size_limit(1 << 30)
    with master_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"record_id", "title", "abstract"}.issubset(reader.fieldnames or []):
            raise ValueError("The analysis master lacks record_id, title or abstract.")
        master = {r["record_id"]: r for r in reader}
    missing = [rid for rid in ids if rid not in master]
    if missing:
        raise ValueError(f"{len(missing)} site studies are not in the master, e.g. {missing[:5]}")

    titles = [clean(master[rid]["title"]) for rid in ids]
    abstracts = [clean(master[rid]["abstract"]) for rid in ids]
    OUT.mkdir(parents=True, exist_ok=True)
    files, sizes = [], []
    for start in range(0, len(ids), CHUNK):
        name = f"{start // CHUNK:03d}.json"
        payload = {"start": start, "t": titles[start:start + CHUNK], "a": abstracts[start:start + CHUNK]}
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        (OUT / name).write_bytes(data)
        files.append(name)
        sizes.append(len(data))  # the download's progress bar uses these
    index = {"n": len(ids), "chunk": CHUNK, "files": files, "bytes": sizes, "source": master_path.name}
    (OUT / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"{len(ids)} studies in {len(files)} files; "
          f"{sum(1 for t in titles if not t)} without title, {sum(1 for a in abstracts if not a)} without abstract")


if __name__ == "__main__":
    main()
