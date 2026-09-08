"""Rendering of EvalReport objects to a terminal (ANSI color) and Markdown.

Pure stdlib. Sibling module `scripts/eval/engine.py` defines the data shapes
this module consumes: `EvalReport` and `PhaseMetrics`.
"""

from __future__ import annotations

from typing import Any

from scripts.eval.engine import EvalReport, PhaseMetrics

# --------------------------------------------------------------------------
# ANSI color helpers
# --------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_MAGENTA = "\033[35m"


def _color_for_score(score: float) -> str:
    if score >= 0.8:
        return _GREEN
    if score >= 0.6:
        return _YELLOW
    return _RED


def _colorize(text: str, color: str) -> str:
    return f"{color}{text}{_RESET}"


def _grade_label(score: float) -> str:
    if score >= 0.9:
        return "EXCELLENT"
    if score >= 0.8:
        return "GOOD"
    if score >= 0.6:
        return "ACCEPTABLE"
    if score >= 0.4:
        return "NEEDS WORK"
    return "FAILING"


def _emoji_for_score(score: float) -> str:
    if score >= 0.8:
        return ":white_check_mark:"
    if score >= 0.6:
        return ":warning:"
    return ":x:"


# --------------------------------------------------------------------------
# Shared golden/predicted field access
# --------------------------------------------------------------------------


def _golden_field(golden: Any, name: str, default: Any = "?") -> Any:
    if golden is None:
        return default
    return getattr(golden, name, default)


def _predicted_field(predicted: Any, name: str, default: Any = "?") -> Any:
    if predicted is None:
        return default
    return predicted.get(name, default)


def _describe_predicted(predicted: dict | None, phase: str) -> str:
    if predicted is None:
        return "(none)"
    entity = _predicted_field(predicted, "entity_name")
    attribute = _predicted_field(predicted, "attribute")
    if phase == "extraction":
        value = _predicted_field(predicted, "value")
        return f"{entity} / {attribute} = {value}"
    status = predicted.get("status")
    if status:
        return f"{entity} / {attribute} (status: {status})"
    return f"{entity} / {attribute}"


def _describe_golden(golden: Any, phase: str) -> str:
    if golden is None:
        return "(none)"
    entity = _golden_field(golden, "entity_name")
    attribute = _golden_field(golden, "attribute")
    if phase == "extraction":
        value = _golden_field(golden, "value")
        seq = _golden_field(golden, "sequence_number")
        return f"{entity} / {attribute} = {value} @ unit {seq}"
    expected = _golden_field(golden, "expected_verdict")
    description = _golden_field(golden, "description", "")
    suffix = f" -- {description}" if description else ""
    return f"{entity} / {attribute} (expected: {expected}){suffix}"


# --------------------------------------------------------------------------
# Terminal report
# --------------------------------------------------------------------------


def _print_phase_terminal(metrics: PhaseMetrics) -> None:
    color = _color_for_score(metrics.f1)
    title = metrics.phase.upper()
    print(f"\n{_BOLD}{_CYAN}== {title} =={_RESET}")
    print(
        f"  Precision: {_colorize(f'{metrics.precision:.3f}', _color_for_score(metrics.precision))}"
        f"   Recall: {_colorize(f'{metrics.recall:.3f}', _color_for_score(metrics.recall))}"
        f"   F1: {_colorize(f'{metrics.f1:.3f}', color)}"
    )
    print(
        f"  {_GREEN}TP={metrics.true_positives}{_RESET}  "
        f"{_RED}FP={metrics.false_positives}{_RESET}  "
        f"{_YELLOW}FN={metrics.false_negatives}{_RESET}"
    )

    false_positives = [d for d in metrics.details if d.get("status") == "FP"][:3]
    false_negatives = [d for d in metrics.details if d.get("status") == "FN"][:3]

    if false_positives:
        print(f"  {_RED}Example false positives:{_RESET}")
        for detail in false_positives:
            print(f"    - {_describe_predicted(detail.get('predicted'), metrics.phase)}")

    if false_negatives:
        print(f"  {_YELLOW}Example false negatives:{_RESET}")
        for detail in false_negatives:
            print(f"    - {_describe_golden(detail.get('golden'), metrics.phase)}")


def _print_per_unit_terminal(per_unit: dict) -> None:
    if not per_unit:
        return
    print(f"\n{_BOLD}{_CYAN}== PER-UNIT EXTRACTION BREAKDOWN =={_RESET}")
    for seq in sorted(per_unit.keys()):
        row = per_unit[seq]
        extracted = row.get("extracted", 0)
        matched = row.get("matched", 0)
        missed_attrs = row.get("missed_attrs", []) or []
        missed = extracted - matched if extracted >= matched else len(missed_attrs)
        # Prefer explicit missed_attrs length if provided and consistent.
        missed = len(missed_attrs) if missed_attrs else max(extracted - matched, 0)

        if missed == 0:
            marker = _colorize("✓", _GREEN)
        elif missed <= 1:
            marker = _colorize("⚠", _YELLOW)
        else:
            marker = _colorize("✗", _RED)

        line = f"  {marker} Unit {seq}: extracted={extracted} matched={matched} missed={missed}"
        if missed > 0 and missed_attrs:
            line += f" (missed: {', '.join(str(a) for a in missed_attrs)})"
        print(line)


def print_terminal_report(report: EvalReport) -> None:
    """Print a color-coded terminal report for an EvalReport."""
    print(f"{_BOLD}{_MAGENTA}{'=' * 60}{_RESET}")
    print(f"{_BOLD}{_MAGENTA}StoryTrace Evaluation Report{_RESET}")
    print(f"{_DIM}Document:  {report.document}{_RESET}")
    print(f"{_DIM}Timestamp: {report.timestamp}{_RESET}")
    print(f"{_BOLD}{_MAGENTA}{'=' * 60}{_RESET}")

    for metrics in (report.extraction, report.detection, report.investigation):
        _print_phase_terminal(metrics)

    _print_per_unit_terminal(report.per_unit)

    overall_color = _color_for_score(report.overall_f1)
    grade = _grade_label(report.overall_f1)
    print(f"\n{_BOLD}{_CYAN}== OVERALL =={_RESET}")
    print(
        f"  Overall F1: {_colorize(f'{report.overall_f1:.3f}', overall_color)}"
        f"  [{_colorize(grade, overall_color)}]"
    )

    if report.adversarial is not None:
        adversarial = report.adversarial
        baseline = adversarial.get("baseline_f1", 0.0)
        engineered = adversarial.get("engineered_f1", 0.0)
        units_tested = adversarial.get("units_tested", 0)
        delta = engineered - baseline
        delta_color = _GREEN if delta >= 0 else _RED
        print(f"\n{_BOLD}{_CYAN}== PROMPT ENGINEERING IMPACT =={_RESET}")
        print(f"  Units tested: {units_tested}")
        print(
            f"  Baseline (no constraints):        "
            f"{_colorize(f'{baseline:.3f}', _color_for_score(baseline))}"
        )
        print(
            f"  Engineered (vocabulary+few-shot):  "
            f"{_colorize(f'{engineered:.3f}', _color_for_score(engineered))}"
        )
        print(f"  Delta: {_colorize(f'{delta:+.3f}', delta_color)}")

    if report.notes:
        print(f"\n{_BOLD}{_CYAN}== NOTES =={_RESET}")
        for note in report.notes:
            print(f"  - {note}")

    print()


# --------------------------------------------------------------------------
# Markdown report
# --------------------------------------------------------------------------


def _phase_row_markdown(metrics: PhaseMetrics) -> str:
    emoji = _emoji_for_score(metrics.f1)
    return (
        f"| {metrics.phase.capitalize()} | {metrics.precision:.3f} | {metrics.recall:.3f} | "
        f"{metrics.f1:.3f} {emoji} | {metrics.true_positives} | {metrics.false_positives} | "
        f"{metrics.false_negatives} |"
    )


def _per_unit_table_markdown(per_unit: dict) -> list[str]:
    if not per_unit:
        return []
    lines = [
        "## Per-Unit Extraction Breakdown",
        "",
        "| Unit | Extracted | Matched | Missed | Missed Attributes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for seq in sorted(per_unit.keys()):
        row = per_unit[seq]
        extracted = row.get("extracted", 0)
        matched = row.get("matched", 0)
        missed_attrs = row.get("missed_attrs", []) or []
        missed = len(missed_attrs) if missed_attrs else max(extracted - matched, 0)
        missed_str = ", ".join(str(a) for a in missed_attrs) if missed_attrs else ""
        lines.append(f"| {seq} | {extracted} | {matched} | {missed} | {missed_str} |")
    lines.append("")
    return lines


def _false_positives_section_markdown(report: EvalReport) -> list[str]:
    lines = ["## False Positives", ""]
    any_fp = False
    for metrics in (report.extraction, report.detection, report.investigation):
        fps = [d for d in metrics.details if d.get("status") == "FP"]
        if not fps:
            continue
        any_fp = True
        lines.append(f"### {metrics.phase.capitalize()}")
        lines.append("")
        for detail in fps:
            predicted = detail.get("predicted")
            entity = _predicted_field(predicted, "entity_name")
            attribute = _predicted_field(predicted, "attribute")
            if metrics.phase == "extraction":
                value = _predicted_field(predicted, "value")
                lines.append(f"- `{entity}` / `{attribute}` = `{value}`")
            else:
                lines.append(f"- `{entity}` / `{attribute}`")
        lines.append("")
    if not any_fp:
        lines.append("_None._")
        lines.append("")
    return lines


def _false_negatives_section_markdown(report: EvalReport) -> list[str]:
    lines = ["## False Negatives", ""]
    any_fn = False
    for metrics in (report.extraction, report.detection, report.investigation):
        fns = [d for d in metrics.details if d.get("status") == "FN"]
        if not fns:
            continue
        any_fn = True
        lines.append(f"### {metrics.phase.capitalize()}")
        lines.append("")
        for detail in fns:
            golden = detail.get("golden")
            entity = _golden_field(golden, "entity_name")
            attribute = _golden_field(golden, "attribute")
            if metrics.phase == "extraction":
                value = _golden_field(golden, "value")
                seq = _golden_field(golden, "sequence_number")
                lines.append(f"- `{entity}` / `{attribute}` = `{value}` @ unit {seq}")
            else:
                expected = _golden_field(golden, "expected_verdict")
                description = _golden_field(golden, "description", "")
                suffix = f" -- {description}" if description else ""
                lines.append(
                    f"- `{entity}` / `{attribute}` (expected: {expected}){suffix}"
                )
        lines.append("")
    if not any_fn:
        lines.append("_None._")
        lines.append("")
    return lines


def _adversarial_section_markdown(report: EvalReport) -> list[str]:
    if report.adversarial is None:
        return []
    adversarial = report.adversarial
    baseline = adversarial.get("baseline_f1", 0.0)
    engineered = adversarial.get("engineered_f1", 0.0)
    units_tested = adversarial.get("units_tested", 0)
    lines = [
        "## Prompt Engineering Impact",
        "",
        f"Units tested: {units_tested}",
        "",
        "| Condition | F1 |",
        "| --- | --- |",
        f"| No constraints | {baseline:.3f} |",
        f"| With vocabulary + few-shot | {engineered:.3f} |",
        "",
    ]
    return lines


def _notes_section_markdown(report: EvalReport) -> list[str]:
    if not report.notes:
        return []
    lines = ["## Pipeline Notes", ""]
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return lines


def write_markdown_report(report: EvalReport, path: str) -> None:
    """Write a Markdown rendering of an EvalReport to `path`."""
    overall_emoji = _emoji_for_score(report.overall_f1)

    lines: list[str] = []
    lines.append("# StoryTrace Evaluation Report")
    lines.append("")
    lines.append(f"**Document:** {report.document}")
    lines.append("")
    lines.append(f"**Timestamp:** {report.timestamp}")
    lines.append("")
    lines.append(f"**Overall F1:** {report.overall_f1:.3f} {overall_emoji}")
    lines.append("")

    lines.append("## Phase Metrics")
    lines.append("")
    lines.append("| Phase | Precision | Recall | F1 | TP | FP | FN |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for metrics in (report.extraction, report.detection, report.investigation):
        lines.append(_phase_row_markdown(metrics))
    lines.append("")

    lines.extend(_per_unit_table_markdown(report.per_unit))
    lines.extend(_false_positives_section_markdown(report))
    lines.extend(_false_negatives_section_markdown(report))
    lines.extend(_adversarial_section_markdown(report))
    lines.extend(_notes_section_markdown(report))

    content = "\n".join(lines).rstrip() + "\n"

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)

    print(f"Report written to {path}")
