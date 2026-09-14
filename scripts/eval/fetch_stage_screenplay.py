"""Fetch and clean screenplay text for STAGE_v0 corpus films.

STAGE_v0 (github.com/roytian1992/STAGE_v0) does not distribute screenplay
text itself -- data/stage/english_movie_info.csv records a per-film
`script_url` (mostly IMSDb) that the user is responsible for resolving under
that source's own terms. This script fetches one film's page, strips the
HTML down to plain screenplay text, and writes it to
data/eval/screenplays/{film_slug}.txt for the pipeline to ingest.

Fetched text is for local research/evaluation use only -- see
data/stage/README.md's "Screenplay policy" and "Rights" sections. Raw
screenplay text is gitignored (see data/eval/screenplays/.gitignore); only
short excerpts (via raw_excerpt provenance fields) are meant to ever appear
in committed outputs or the paper/patent drafts.
"""

import argparse
import csv
import html
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
MOVIE_INFO_CSV = REPO_ROOT / "data" / "stage" / "english_movie_info.csv"
OUT_DIR = REPO_ROOT / "data" / "eval" / "screenplays"

_UA = "Mozilla/5.0 (research; StoryTrace eval corpus build)"
_SCENE_HEADER_RE = re.compile(r"^\s*(INT|EXT|INT\./EXT|I/E)[./ ]", re.MULTILINE | re.IGNORECASE)


def slugify(title: str) -> str:
    slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_").lower()
    return slug


def load_manifest_rows() -> list[dict]:
    with open(MOVIE_INFO_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch_html(url: str) -> str:
    req = Request(url, headers={"User-Agent": _UA})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def clean_imsdb_text(raw_html: str) -> str:
    match = re.search(r"<pre>(.*?)</pre>", raw_html, re.S | re.I)
    if not match:
        raise ValueError("no <pre> block found -- page structure may differ from IMSDb norm")
    text = match.group(1)
    text = re.sub(r"<b>|</b>|<i>|</i>", "", text)
    text = re.sub(r"<a\b[^>]*>", "", text)
    text = re.sub(r"</a>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def real_scene_count(text: str) -> int:
    return len(_SCENE_HEADER_RE.findall(text))


def fetch_one(title: str, script_url: str, out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(title)
    out_path = out_dir / f"{slug}.txt"

    raw_html = fetch_html(script_url)
    text = clean_imsdb_text(raw_html)
    out_path.write_text(text, encoding="utf-8")

    return {
        "film": title,
        "film_slug": slug,
        "script_url": script_url,
        "out_path": str(out_path.relative_to(REPO_ROOT)),
        "word_count": len(text.split()),
        "real_scene_count": real_scene_count(text),
        "char_count": len(text),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("titles", nargs="+", help="Exact 'title' values from english_movie_info.csv")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds to sleep between fetches (be polite to IMSDb)")
    args = parser.parse_args()

    rows_by_title = {r["title"]: r for r in load_manifest_rows()}
    results = []
    for i, title in enumerate(args.titles):
        row = rows_by_title.get(title)
        if row is None:
            print(f"ERROR: '{title}' not found in {MOVIE_INFO_CSV}", file=sys.stderr)
            continue
        if i > 0:
            time.sleep(args.delay)
        try:
            info = fetch_one(title, row["script_url"])
            print(
                f"OK  {info['film']!r:40s} real_scenes={info['real_scene_count']:>4d} "
                f"words={info['word_count']:>6d}  csv_num_scenes={row['num_scenes']} "
                f"csv_word_count={row['word_count']}"
            )
            results.append(info)
        except Exception as exc:
            print(f"FAIL {title!r}: {exc}", file=sys.stderr)

    print(f"\nFetched {len(results)}/{len(args.titles)} screenplays -> {OUT_DIR}")


if __name__ == "__main__":
    main()
