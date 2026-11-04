"""Mechanical post-edit check for technical channels (PR · Jira · Confluence · plan).

Compares the source draft and the edited draft and reports:
  - protected tokens that disappeared (inline code, paths, URLs, REQ/issue IDs, numbers, checkboxes, status emoji)
  - length ratio against an optional budget
  - mixed sentence-ending registers (한다체 / 합니다체 / 해요체)

Exit code 0 = pass, 1 = protected token missing or budget exceeded, 2 = usage error.

Usage:
    python3 check_preservation.py <source.md> <edited.md> [--max-ratio 1.0] [--json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

PROTECTED_PATTERNS = {
    "inline_code": r"`[^`\n]+`",
    "url": r"https?://[^\s)>\]`]+",
    "path": r"(?<![\w`])(?:\.{0,2}/)?(?:[\w.-]+/)+[\w.-]*\.[A-Za-z]\w*",
    "issue_id": r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)*-\d+\b|#\d+\b",
    "number": r"(?<![\w.])\d+(?:[.,:]\d+)*(?:%|ms|s|x|배|건|회|개|명)?",
    "checkbox": r"^\s*[-*] \[[ xX]\]",
    "status_emoji": r"[🟢🟡🔴🔵✅❌⚠️]",
}
REGISTER_PATTERNS = {
    "handa": r"(?:다|까)\.(?=\s|$)",
    "hamnida": r"(?:니다|니까)\.(?=\s|$)",
    "haeyo": r"(?:요)\.(?=\s|$)",
}


def strip_fenced_code(markdown_text):
    return re.sub(r"```.*?```", " ", markdown_text, flags=re.S)


def protected_tokens(markdown_text):
    found = {}
    for kind, pattern in PROTECTED_PATTERNS.items():
        flags = re.M if kind == "checkbox" else 0
        matches = re.findall(pattern, markdown_text, flags)
        found[kind] = [match.strip() for match in matches]
    return found


def normalize(text):
    return re.sub(r"[`\s]", "", text)


def missing_tokens(source_text, edited_text):
    edited_plain = normalize(edited_text)
    missing = {}
    for kind, tokens in protected_tokens(source_text).items():
        if kind == "checkbox":
            lost_count = len(tokens) - len(protected_tokens(edited_text)["checkbox"])
            if lost_count > 0:
                missing[kind] = [f"{lost_count} checkbox line(s)"]
            continue
        lost = sorted({token for token in tokens if normalize(token) not in edited_plain})
        if lost:
            missing[kind] = lost
    return missing


def register_counts(markdown_text):
    prose = strip_fenced_code(markdown_text)
    return {name: len(re.findall(pattern, prose, re.M)) for name, pattern in REGISTER_PATTERNS.items()}


def is_mixed_register(counts):
    used = [count for count in counts.values() if count > 0]
    return len(used) > 1 and min(used) >= 2


def build_report(source_text, edited_text, max_ratio):
    length_ratio = len(edited_text.strip()) / max(len(source_text.strip()), 1)
    missing = missing_tokens(source_text, edited_text)
    registers = register_counts(edited_text)
    return {
        "length_ratio": round(length_ratio, 3),
        "over_budget": max_ratio is not None and length_ratio > max_ratio,
        "missing": missing,
        "missing_count": sum(len(items) for items in missing.values()),
        "registers": registers,
        "mixed_register": is_mixed_register(registers),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mechanical post-edit check for technical channels.")
    parser.add_argument("source")
    parser.add_argument("edited")
    parser.add_argument("--max-ratio", type=float, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        source_text = Path(args.source).read_text(encoding="utf-8")
        edited_text = Path(args.edited).read_text(encoding="utf-8")
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    report = build_report(source_text, edited_text, args.max_ratio)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"length_ratio={report['length_ratio']} over_budget={report['over_budget']} "
              f"missing={report['missing_count']} mixed_register={report['mixed_register']} {report['registers']}")
        for kind, items in report["missing"].items():
            print(f"  missing {kind}: {', '.join(items[:8])}")
    failed = report["missing_count"] > 0 or report["over_budget"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
