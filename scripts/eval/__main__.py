import asyncio
import sys

from scripts.eval.report import print_terminal_report, write_markdown_report
from scripts.eval.run_eval import run_full_eval


async def main() -> None:
    # Support --v2 flag to run against controlled_test_v2.txt instead of
    # controlled_test.txt, for overfitting validation (see EVAL_IMPROVEMENT_LOG.md).
    use_v2 = "--v2" in sys.argv

    golden = None
    report_path = "EVAL_REPORT.md"
    if use_v2:
        from data.eval.golden_dataset_v2 import GOLDEN_DATASET_V2
        golden = GOLDEN_DATASET_V2
        report_path = "EVAL_REPORT_V2.md"
        print("Running eval against controlled_test_v2.txt (overfitting check)...")

    report = await run_full_eval(golden=golden)
    print_terminal_report(report)
    write_markdown_report(report, report_path)

    if report.overall_f1 < 0.6:
        print("WARNING: Overall F1 below 0.6 threshold")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
