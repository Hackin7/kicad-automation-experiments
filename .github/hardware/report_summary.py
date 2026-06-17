#!/usr/bin/env python3
"""Create a compact Markdown summary of KiBot ERC/DRC reports."""

import argparse
import html.parser
import json
import re
from pathlib import Path
from typing import List, Optional, Tuple


MAX_ISSUES_PER_REPORT = 40
MAX_LINE_LENGTH = 240


class TextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []  # type: List[str]
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip_depth += 1
        elif tag in {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        elif tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)

    def text(self):
        return "".join(self.parts)


def read_report(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        parser = TextExtractor()
        parser.feed(text)
        text = parser.text()
    return text


def normalize_lines(text):
    lines = []  # type: List[str]
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        line = re.sub(r"^\s*[•*-]\s*", "", line)
        if len(line) > MAX_LINE_LENGTH:
            line = line[: MAX_LINE_LENGTH - 1] + "..."
        lines.append(line)
    return lines


def looks_like_no_issues(lines):
    joined = "\n".join(lines).lower()
    has_nonzero_count = re.search(r"\b[1-9]\d*\s+(errors?|warnings?|violations?|issues?)\b", joined)
    if has_nonzero_count:
        return False
    no_issue_patterns = [
        r"\b0\s+errors?\b",
        r"\b0\s+warnings?\b",
        r"\b0\s+violations?\b",
        r"\b0\s+issues?\b",
        r"\bno\s+errors?\b",
        r"\bno\s+warnings?\b",
        r"\bno\s+violations?\b",
        r"\bno\s+issues?\b",
    ]
    return any(re.search(pattern, joined) for pattern in no_issue_patterns)


def interesting_lines(lines):
    skip_patterns = [
        r"^$", r"^date\b", r"^time\b", r"^kicad\b", r"^report\b", r"^file\b",
        r"^items? checked\b", r"^checking\b", r"^running\b", r"^board\b", r"^schematic\b",
    ]
    issue_patterns = [
        r"\berror\b", r"\bwarning\b", r"\bviolation\b", r"\bunconnected\b",
        r"\bclearance\b", r"\boverlap\b", r"\bshort\b", r"\bnot connected\b",
        r"\bmissing\b", r"\bconflict\b", r"\bdrilled\b", r"\bannular\b",
    ]

    selected = []  # type: List[str]
    for line in lines:
        lowered = line.lower()
        if any(re.search(pattern, lowered) for pattern in skip_patterns):
            continue
        if any(re.search(pattern, lowered) for pattern in issue_patterns):
            selected.append(line)
        elif selected and len(selected) < MAX_ISSUES_PER_REPORT and re.search(r"\([^)]+\)|\[[^]]+\]|\bat\b", lowered):
            selected.append(line)
        if len(selected) >= MAX_ISSUES_PER_REPORT:
            break

    return selected


def summarize_report(path):
    # type: (Path) -> Tuple[str, bool]
    lines = normalize_lines(read_report(path))
    if not lines or looks_like_no_issues(lines):
        return "No issues found in this report.", False

    issues = interesting_lines(lines)
    if not issues:
        issues = lines[:MAX_ISSUES_PER_REPORT]

    truncated = len(issues) >= MAX_ISSUES_PER_REPORT
    body = "\n".join(f"- {line}" for line in issues)
    if truncated:
        body += "\n- Report truncated in summary. See the full HTML/text artifact for details."
    return body, bool(issues)


def find_report(report_dir, kind, basename):
    # type: (Path, str, str) -> Optional[Path]
    candidates = []
    for path in report_dir.rglob("*"):
        if not path.is_file():
            continue
        lowered = path.name.lower()
        if kind not in lowered:
            continue
        if path.suffix.lower() not in {".html", ".htm", ".txt", ".rpt", ".log", ".md"}:
            continue
        score = 0
        if basename.lower() in lowered:
            score -= 10
        if path.suffix.lower() in {".html", ".htm"}:
            score -= 3
        elif path.suffix.lower() in {".txt", ".rpt", ".log"}:
            score -= 2
        score += len(path.parts)
        candidates.append((score, path))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item[0], str(item[1])))[0][1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects-json", required=True)
    parser.add_argument("--artifacts-dir", default="check-artifacts")
    args = parser.parse_args()

    projects = json.loads(args.projects_json)
    artifacts_dir = Path(args.artifacts_dir)

    print("## ERC and DRC Issues")
    print()
    print("The summary below is capped for readability. Full HTML/text reports are in the check-report artifacts and on the review site when Pages is published.")
    print()

    for project in projects:
        slug = project["slug"]
        name = project["name"]
        basename = project.get("basename", slug)
        report_dir = artifacts_dir / f"{slug}-check-reports"

        print(f"### {name}")
        print()
        if not report_dir.exists():
            print("_No check-report artifact was found for this project._")
            print()
            continue

        for label, kind in (("ERC", "erc"), ("DRC", "drc")):
            report = find_report(report_dir, kind, basename)
            print(f"<details open><summary>{label}</summary>")
            print()
            if report is None:
                print(f"_No {label} report file was found in `{report_dir}`._")
            else:
                summary, _ = summarize_report(report)
                print(f"_Source: `{report.as_posix()}`_")
                print()
                print(summary)
            print()
            print("</details>")
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
