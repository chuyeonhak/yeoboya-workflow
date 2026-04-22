"""Scan text for PII patterns (email, KR phone, KR resident registration number).

Input: text on stdin.
Output (stdout): JSON
{ "findings": [{"category": "email"|"phone"|"rrn", "sample": "...(masked)", "line": N}] }

This is a WARNING tool — never blocks the workflow. It helps developers catch
PII in PDFs before publishing to Notion.
"""
import json
import re
import sys

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
KR_PHONE_RE = re.compile(r"\b01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}\b")
KR_RRN_RE = re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b")

PATTERNS = [
    ("email", EMAIL_RE),
    ("phone", KR_PHONE_RE),
    ("rrn", KR_RRN_RE),
]


def mask(value: str, category: str) -> str:
    if category == "email":
        local, _, domain = value.partition("@")
        if len(local) <= 2:
            return f"*@{domain}"
        return f"{local[0]}***{local[-1]}@{domain}"
    if category == "phone":
        return f"{value[:3]}-****-{value[-4:]}"
    if category == "rrn":
        return f"{value[:6]}-*******"
    return "***"


def scan(text: str) -> list[dict]:
    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for category, pattern in PATTERNS:
            for match in pattern.finditer(line):
                findings.append({
                    "category": category,
                    "sample": mask(match.group(0), category),
                    "line": line_no,
                })
    return findings


def main() -> int:
    text = sys.stdin.read()
    findings = scan(text)
    json.dump({"findings": findings}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
