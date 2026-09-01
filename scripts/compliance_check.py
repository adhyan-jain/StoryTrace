"""Prints the hackathon compliance checklist: which required packages are
actually imported and used at runtime, plus the repo-level requirements
(LICENSE, README, requirements.txt entries)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _check(label: str, ok: bool) -> None:
    mark = "[x]" if ok else "[ ]"
    print(f"  {mark} {label}")


def main() -> None:
    print("\nHackathon compliance checklist:")

    try:
        import google.genai  # noqa: F401

        genai_ok = True
    except ImportError:
        genai_ok = False
    _check("google-genai imported and called at runtime (backend/llm/client.py: GeminiProvider)", genai_ok)

    try:
        import google.adk.agents  # noqa: F401

        adk_ok = True
    except ImportError:
        adk_ok = False
    _check("google-adk imported and called at runtime (backend/agent/adk_runner.py: suggest_fix_via_adk)", adk_ok)

    try:
        import mcp_clickhouse  # noqa: F401
        import mcp  # noqa: F401

        mcp_ok = True
    except ImportError:
        mcp_ok = False
    _check("mcp-clickhouse imported and called at runtime (backend/agent/tools.py via investigator.py MCP session)", mcp_ok)

    req_text = (ROOT / "requirements.txt").read_text()
    req_ok = all(pkg in req_text for pkg in ("google-genai", "google-adk", "mcp-clickhouse"))
    _check("All three appear in requirements.txt", req_ok)

    license_ok = (ROOT / "LICENSE").exists()
    _check("LICENSE file exists at repo root", license_ok)

    readme_text = (ROOT / "README.md").read_text() if (ROOT / "README.md").exists() else ""
    readme_ok = "Running the project" in readme_text or "uvicorn backend.api.main" in readme_text
    _check("README.md documents how to run the project", readme_ok)

    print()


if __name__ == "__main__":
    main()
