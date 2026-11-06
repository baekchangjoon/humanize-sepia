"""Mechanical post-edit check for technical channels (PR · Jira · Confluence · plan).

Compares the source draft and the edited draft and reports:
  - protected tokens that disappeared (inline code, paths, URLs, REQ/issue IDs, numbers, checkboxes, status emoji)
  - length ratio against an optional budget (optionally excluding fenced code blocks such as ASCII diagrams)
  - mixed sentence-ending registers (한다체 / 합니다체 / 해요체)
  - prose lines that hold two or more sentences or exceed a length limit (optional)

Exit code 0 = pass, 1 = protected token missing, budget exceeded or long lines (with --max-line), 2 = usage error.

Usage:
    python3 check_preservation.py <source.md> <edited.md> [--max-ratio 1.0] [--exclude-fenced] [--max-line 80] [--json]
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
    "handa": r"(?<!니)(?:다|까)\.(?=\s|$)",
    "hamnida": r"(?:니다|니까)\.(?=\s|$)",
    "haeyo": r"(?:요)\.(?=\s|$)",
}
SENTENCE_END = r"(?<=[가-힣A-Za-z0-9)\]`*\"'])[.?!](?=\s|$)"
LIST_MARKER = r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?"
SKIPPED_LINE_PREFIXES = ("|", "#")


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


def measured_length(markdown_text, exclude_fenced):
    text = strip_fenced_code(markdown_text) if exclude_fenced else markdown_text
    return len(text.strip())


def measured_line(line_text):
    body = re.sub(LIST_MARKER, "", line_text.strip())
    body = re.sub(r"`[^`\n]+`", "C", body)
    return re.sub(r"https?://\S+", "U", body)


def long_lines(markdown_text, max_length):
    flagged = []
    in_fence = False
    for line_number, line_text in enumerate(markdown_text.splitlines(), start=1):
        if line_text.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line_text.strip() or line_text.strip().startswith(SKIPPED_LINE_PREFIXES):
            continue
        body = measured_line(line_text)
        sentences = len(re.findall(SENTENCE_END, body))
        if len(body) > max_length or sentences >= 2:
            flagged.append({"line": line_number, "length": len(body), "sentences": sentences, "text": line_text.strip()[:60]})
    return flagged


def build_report(source_text, edited_text, max_ratio, exclude_fenced=False, max_line=None):
    source_length = measured_length(source_text, exclude_fenced)
    length_ratio = measured_length(edited_text, exclude_fenced) / max(source_length, 1)
    missing = missing_tokens(source_text, edited_text)
    registers = register_counts(edited_text)
    return {
        "length_ratio": round(length_ratio, 3),
        "over_budget": max_ratio is not None and length_ratio > max_ratio,
        "missing": missing,
        "missing_count": sum(len(items) for items in missing.values()),
        "registers": registers,
        "mixed_register": is_mixed_register(registers),
        "long_lines": long_lines(edited_text, max_line) if max_line else [],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mechanical post-edit check for technical channels.")
    parser.add_argument("source")
    parser.add_argument("edited")
    parser.add_argument("--max-ratio", type=float, default=None)
    parser.add_argument("--exclude-fenced", action="store_true",
                        help="measure length without fenced code blocks (diagrams, code)")
    parser.add_argument("--max-line", type=int, default=None,
                        help="flag prose lines longer than this or holding 2+ sentences")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        source_text = Path(args.source).read_text(encoding="utf-8")
        edited_text = Path(args.edited).read_text(encoding="utf-8")
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    report = build_report(source_text, edited_text, args.max_ratio, args.exclude_fenced, args.max_line)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"length_ratio={report['length_ratio']} over_budget={report['over_budget']} "
              f"missing={report['missing_count']} mixed_register={report['mixed_register']} {report['registers']} "
              f"long_lines={len(report['long_lines'])}")
        for kind, items in report["missing"].items():
            print(f"  missing {kind}: {', '.join(items[:8])}")
        for item in report["long_lines"][:8]:
            print(f"  long line {item['line']} (len={item['length']}, sentences={item['sentences']}): {item['text']}")
    failed = report["missing_count"] > 0 or report["over_budget"] or bool(report["long_lines"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
