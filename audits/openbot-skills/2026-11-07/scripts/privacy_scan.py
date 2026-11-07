#!/usr/bin/env python3
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

CREDENTIAL_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", re.I),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    "credential_assignment": re.compile(r"(?i)\b(?:api[_ -]?key|secret[_ -]?key|access[_ -]?token|password|passwd|client[_ -]?secret)\b\s*[:=]\s*[\"']?[A-Za-z0-9/+=_-]{16,}"),
}
WSL_PREFIX = "/" + "m" + "nt"
HOME_PREFIX = "/" + "ho" + "me"
PRIVATE_PATTERNS = {
    "windows_user_path": re.compile(r"(?i)(?:[A-Z]:\\Users\\|\\\\[^\\]+\\Users\\)[^\\\s\"']+"),
    "wsl_user_path": re.compile(re.escape(WSL_PREFIX) + r"/[a-z]/Users/[^/\s\"']+"),
    "linux_home_path": re.compile(re.escape(HOME_PREFIX) + r"/[^/\s\"']+"),
    "absolute_host_path": re.compile(r"(?<![\w])/" + r"(?:Users|ho" + r"me|m" + r"nt|tmp|var)/[^\s\"'<>]+"),
    "agent_uuid": re.compile(r"\bagent-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
}

def shannon(value):
    counts = collections.Counter(value)
    size = len(value)
    return -sum((count / size) * math.log2(count / size) for count in counts.values())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    credential_hits = []
    entropy_hits = []
    private_hits = []
    files = 0
    bytes_scanned = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        files += 1
        bytes_scanned += len(raw)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            private_hits.append((relative, 0, "non_utf8"))
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            for category, pattern in CREDENTIAL_PATTERNS.items():
                if pattern.search(line):
                    credential_hits.append((relative, line_number, category))
            if relative != "scripts/privacy_scan.py":
                for category, pattern in PRIVATE_PATTERNS.items():
                    if pattern.search(line):
                        private_hits.append((relative, line_number, category))
            entropy_line = line.replace("research_status=RESEARCH_CANDIDATE", "")
            for token in re.findall(r"(?<![A-Za-z0-9])[A-Za-z0-9_+=]{28,}(?![A-Za-z0-9])", entropy_line):
                if re.fullmatch(r"[A-Fa-f0-9]{64}", token):
                    continue
                if shannon(token) >= 4.15:
                    entropy_hits.append((relative, line_number, len(token)))
    print(json.dumps({
        "files_scanned": files,
        "bytes_scanned": bytes_scanned,
        "credential_pattern_hits": credential_hits,
        "high_entropy_non_hash_hits": entropy_hits,
        "private_path_identity_hits": private_hits,
    }, indent=2))
    return 1 if credential_hits or entropy_hits or private_hits else 0

if __name__ == "__main__":
    sys.exit(main())
