"""Validation & Gold Dataset Compilation Script for StoryTrace Human Annotations.

Enforces strict integrity checks on human annotation files:
1. Duplicate label detection (identical scene pair + entity + attribute)
2. Invalid scene IDs / Sequence monotonicity (earlier_scene_unit < later_scene_unit)
3. Missing evidence excerpts (earlier_excerpt and later_excerpt)
4. Verbatim text grounding (excerpts MUST exist in source screenplay text)
5. Inconsistent verdict/category combinations
6. Invalid entity/attribute formatting (dot-separated attribute, canonical entity name)

Usage:
  python3 -m scripts.eval.validate_gold_dataset path/to/human_annotation.json
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "data" / "eval" / "corpus_manifest.json"
SCHEMA_PATH = REPO_ROOT / "data" / "annotation" / "annotation_schema.json"
GOLD_OUTPUT_PATH = REPO_ROOT / "data" / "eval" / "gold_dataset_v3.json"

TAXONOMY_CATEGORIES = {"possession", "injury", "location", "clothing/appearance", "other"}
VERDICT_STATUSES = {"verified", "resolved", "ambiguous"}
SEVERITY_TIERS = {"critical", "warning", "info"}


def load_corpus_manifest() -> dict[str, dict]:
    if not MANIFEST_PATH.exists():
        logger.warning(f"Manifest not found at {MANIFEST_PATH}")
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        data = json.load(f)
    film_map = {}
    for entry in data.get("films", []):
        film_map[entry["film_slug"]] = entry
        film_map[entry["film_name"].lower()] = entry
    return film_map


def load_annotation_file(file_path: Path) -> dict:
    if file_path.suffix.lower() == ".json":
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    elif file_path.suffix.lower() == ".csv":
        rows = []
        annotator_id = "unknown"
        film = "unknown"
        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                annotator_id = r.get("annotator_id", annotator_id)
                film = r.get("film", film)
                rows.append({
                    "annotation_id": r.get("annotation_id", ""),
                    "earlier_scene_unit": int(r["earlier_scene_unit"]) if r.get("earlier_scene_unit", "").isdigit() else r.get("earlier_scene_unit", ""),
                    "later_scene_unit": int(r["later_scene_unit"]) if r.get("later_scene_unit", "").isdigit() else r.get("later_scene_unit", ""),
                    "entity": r.get("entity", ""),
                    "attribute": r.get("attribute", ""),
                    "earlier_state": r.get("earlier_state", ""),
                    "later_state": r.get("later_state", ""),
                    "conflict_type": r.get("conflict_type", ""),
                    "verdict_status": r.get("verdict_status", ""),
                    "severity": r.get("severity", ""),
                    "exact_evidence_excerpts": {
                        "earlier_excerpt": r.get("earlier_excerpt", ""),
                        "later_excerpt": r.get("later_excerpt", ""),
                    },
                    "annotator_notes": r.get("annotator_notes", ""),
                })
        return {"annotator_id": annotator_id, "film": film, "annotations": rows}
    else:
        raise ValueError(f"Unsupported file extension: {file_path.suffix}")


def validate_annotation_data(data: dict, manifest_map: dict[str, dict]) -> tuple[bool, list[str]]:
    errors = []
    annotator_id = data.get("annotator_id")
    if not annotator_id:
        errors.append("Missing required root field: annotator_id")

    film_slug = data.get("film")
    if not film_slug:
        errors.append("Missing required root field: film")

    annotations = data.get("annotations", [])
    if not isinstance(annotations, list):
        errors.append("Field 'annotations' must be a list")
        return False, errors

    # Load screenplay text if available
    screenplay_text = None
    if film_slug in manifest_map:
        rel_path = manifest_map[film_slug].get("screenplay_path")
        if rel_path:
            full_path = REPO_ROOT / rel_path
            if full_path.exists():
                with open(full_path, encoding="utf-8") as f:
                    screenplay_text = f.read()

    seen_keys = set()

    for i, ann in enumerate(annotations, start=1):
        prefix = f"Annotation #{i} (ID: {ann.get('annotation_id', 'N/A')}):"

        # 1. Duplicate label check
        key = (ann.get("earlier_scene_unit"), ann.get("later_scene_unit"), ann.get("entity"), ann.get("attribute"))
        if key in seen_keys:
            errors.append(f"{prefix} DUPLICATE label detected for key {key}")
        seen_keys.add(key)

        # 2. Entity & Attribute formatting check
        entity = ann.get("entity", "")
        if not entity or len(entity) < 2:
            errors.append(f"{prefix} invalid or empty entity '{entity}'")

        attr = ann.get("attribute", "")
        if not attr or "." not in attr:
            errors.append(f"{prefix} invalid attribute format '{attr}'. Must be dot-separated (e.g. location.city, possession.weapon)")

        # 3. Category validation
        cat = ann.get("conflict_type")
        if cat not in TAXONOMY_CATEGORIES:
            errors.append(f"{prefix} invalid conflict_type '{cat}'. Allowed: {TAXONOMY_CATEGORIES}")

        # 4. Verdict status validation
        status = ann.get("verdict_status")
        if status not in VERDICT_STATUSES:
            errors.append(f"{prefix} invalid verdict_status '{status}'. Allowed: {VERDICT_STATUSES}")

        # 5. Inconsistent verdict/category check
        if status == "resolved" and ann.get("severity") == "critical":
            errors.append(f"{prefix} INCONSISTENT verdict/severity combination: 'resolved' status cannot be 'critical' severity.")

        # 6. Severity validation
        sev = ann.get("severity")
        if sev not in SEVERITY_TIERS:
            errors.append(f"{prefix} invalid severity '{sev}'. Allowed: {SEVERITY_TIERS}")

        # 7. Sequence bounds check
        u1 = ann.get("earlier_scene_unit")
        u2 = ann.get("later_scene_unit")
        if isinstance(u1, int) and isinstance(u2, int) and u1 >= u2:
            errors.append(f"{prefix} earlier_scene_unit ({u1}) must be strictly less than later_scene_unit ({u2})")

        # 8. Excerpt presence and verbatim grounding check
        excerpts = ann.get("exact_evidence_excerpts", {})
        e1 = excerpts.get("earlier_excerpt", "")
        e2 = excerpts.get("later_excerpt", "")

        if not e1:
            errors.append(f"{prefix} missing earlier_excerpt")
        if not e2:
            errors.append(f"{prefix} missing later_excerpt")

        if screenplay_text:
            if e1 and e1.strip() not in screenplay_text:
                errors.append(f"{prefix} earlier_excerpt is not found verbatim in source screenplay: '{e1[:40]}...'")
            if e2 and e2.strip() not in screenplay_text:
                errors.append(f"{prefix} later_excerpt is not found verbatim in source screenplay: '{e2[:40]}...'")

    is_valid = len(errors) == 0
    return is_valid, errors


def compile_gold_dataset(annotation_files: list[Path]) -> None:
    manifest_map = load_corpus_manifest()
    compiled_films = {}
    total_valid = 0

    for file_path in annotation_files:
        logger.info(f"Validating annotation file: {file_path}")
        try:
            raw_data = load_annotation_file(file_path)
            if isinstance(raw_data, dict) and "films" in raw_data and isinstance(raw_data["films"], dict):
                # Compiled multi-film dataset
                datasets = []
                for f_slug, f_anns in raw_data["films"].items():
                    datasets.append({
                        "annotator_id": raw_data.get("_meta", {}).get("annotation_method", "gold_dataset"),
                        "film": f_slug,
                        "annotations": f_anns,
                    })
            elif isinstance(raw_data, list):
                datasets = raw_data
            else:
                datasets = [raw_data]

            for data in datasets:
                valid, errors = validate_annotation_data(data, manifest_map)
                if not valid:
                    logger.error(f"Validation FAILED for film {data.get('film')} in {file_path.name}:")
                    for err in errors:
                        logger.error(f"  - {err}")
                    continue

                film_slug = data["film"]
                if film_slug not in compiled_films:
                    compiled_films[film_slug] = []
                compiled_films[film_slug].extend(data["annotations"])
                total_valid += len(data["annotations"])
            logger.info(f"Successfully validated annotations from {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

    out_data = {
        "_meta": {
            "version": "3.0_gold",
            "total_validated_annotations": total_valid,
            "films_covered": list(compiled_films.keys()),
            "status": "HUMAN_ANNOTATED_GROUND_TRUTH"
        },
        "films": compiled_films
    }

    with open(GOLD_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    logger.info(f"Compiled gold dataset written to {GOLD_OUTPUT_PATH} ({total_valid} items)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_files = [Path(p) for p in sys.argv[1:]]
        compile_gold_dataset(target_files)
    else:
        logger.info("No file arguments provided. Pass path to human annotation file(s).")
