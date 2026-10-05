"""Trivial reference systems (task records only)."""
import re


def always_keep(task):
    return {c["id"]: ("KEEP", "") for c in task["claims"]}


def mention_rule(task):
    """Revise any claim whose entity is mentioned in the evidence and whose day >= the evidence day (label only; value unknown)."""
    day = int(re.search(r"\d+", task["evidence"]).group())
    return {c["id"]: (("REVISE", "") if re.search(rf"\b{re.escape(c['entity'])}\b", task["evidence"]) and c["slot"] >= day else ("KEEP", ""))
            for c in task["claims"]}
