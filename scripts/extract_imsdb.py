"""Extract plain-text screenplay content from a saved IMSDB page.

IMSDB wraps the script body in <td class="scrtext"> containing a <pre> tag
(sometimes with nested formatting tags inside the <pre>). Strips all HTML
and writes clean text.

Usage: python3 scripts/extract_imsdb.py <input.html> <output.txt>
"""

import sys

from bs4 import BeautifulSoup


def extract(html_path: str) -> str:
    with open(html_path, encoding="utf-8", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("td", class_="scrtext")
    if container is None:
        raise ValueError(f"No <td class=\"scrtext\"> found in {html_path} -- not a real IMSDB script page")

    pre = container.find("pre")
    text = pre.get_text() if pre is not None else container.get_text()
    return text.strip()


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/extract_imsdb.py <input.html> <output.txt>")
        raise SystemExit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]
    text = extract(input_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Wrote {len(text)} chars to {output_path}")
    print(f"First 200 chars:\n{text[:200]}")


if __name__ == "__main__":
    main()
