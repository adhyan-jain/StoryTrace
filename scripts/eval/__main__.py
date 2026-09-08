import asyncio
import sys

from scripts.eval.report import print_terminal_report, write_markdown_report
from scripts.eval.run_eval import run_full_eval


async def main() -> None:
    report = await run_full_eval()
    print_terminal_report(report)
    write_markdown_report(report, "EVAL_REPORT.md")

    if report.overall_f1 < 0.6:
        print("WARNING: Overall F1 below 0.6 threshold")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
