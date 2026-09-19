"""Regenerates the parsed Reverend Insanity dataset from data/raw/*.epub via
NovelParser. data/ itself is gitignored (large, regeneratable); this script
is what makes data/processed/ri_parsed.json reproducible.

Usage: python3 -m scripts.generate_ri_parsed_dataset
"""

import json
import os

from backend.ingestion.parsers import NovelParser


def generate_ri_parsed_dataset() -> None:
    parser = NovelParser(document_id="RI")
    units = parser.parse("data/raw/reverend-insanity-c1-c500.epub")
    print(f"Parsed {len(units)} units")

    os.makedirs("data/processed", exist_ok=True)
    out_path = "data/processed/ri_parsed.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([u.model_dump() for u in units], f, indent=2, ensure_ascii=False)

    print(f"Successfully saved all {len(units)} units to {out_path}")


if __name__ == "__main__":
    generate_ri_parsed_dataset()
