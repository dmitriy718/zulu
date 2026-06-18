from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    ".next",
    ".venv",
    "__pycache__",
    "node_modules",
    "playwright-report",
    "test-results",
}
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"\s]{16,}['\"]"),
    re.compile(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
ALLOWLIST = {
    "zulu_dev_password",
    "token-owner",
    "token-admin",
    "token-trader",
    "token-viewer",
    "token-operator",
    "token-support",
    "token-other",
    "fixture_webhook_secret",
    "[REDACTED]",
}


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".zip", ".lock"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scrubbed = text
        for allowed in ALLOWLIST:
            scrubbed = scrubbed.replace(allowed, "")
        for pattern in SECRET_PATTERNS:
            if pattern.search(scrubbed):
                findings.append(str(path.relative_to(ROOT)))
                break
    if findings:
        print("Potential committed secret patterns:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Secret scan passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
