#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

EXPECTED = {
    "astrabot-lead": 9,
    "trading-lab-director": 6,
    "trading-lab-market-researcher": 6,
    "chart-vision-analyst": 1,
    "independent-risk-reviewer": 5,
}
LOCAL_REF = re.compile(r"(?:references|cases|schemas|scripts)/[A-Za-z0-9_./-]+\.(?:md|json|py|js|sh)")

def resolve_refs(value, output):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str) and not child.startswith(("http://", "https://", "#")):
                output.append(child)
            resolve_refs(child, output)
    elif isinstance(value, list):
        for child in value:
            resolve_refs(child, output)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    errors = []
    if manifest.get("source_count_verified") is not True:
        errors.append("source_count_verified is not true")
    if manifest.get("scope_assignment_count") != 27:
        errors.append("scope assignment count is not 27")
    if manifest.get("observed_total_effective_assignments") != 42:
        errors.append("observed total assignment count is not 42")
    if manifest.get("generic_baseline_assignments_excluded") != 15:
        errors.append("generic baseline count is not 15")
    if manifest.get("unique_scope_skill_ids") != 9:
        errors.append("unique specialist ID count is not 9")
    if len(manifest.get("agents", [])) != 5:
        errors.append("expected five agent manifests")

    for agent in manifest.get("agents", []):
        alias = agent.get("directory")
        expected = EXPECTED.get(alias)
        if expected is None:
            errors.append("unknown agent directory: " + str(alias))
            continue
        if agent.get("scope_assignments") != expected or agent.get("exported_assignments") != expected:
            errors.append("assignment count mismatch for " + alias)
        if agent.get("source_count_verified") is not True:
            errors.append("source count is unverified for " + alias)
        local_path = root / "agents" / alias / "MANIFEST.json"
        try:
            local = json.loads(local_path.read_text(encoding="utf-8"))
            safe = {
                "snapshot_date": manifest["snapshot_date"],
                "role": agent["role"],
                "directory": alias,
                "source_count_verified": agent["source_count_verified"],
                "observed_effective_assignments": agent["observed_effective_assignments"],
                "generic_baseline_assignments_excluded": agent["generic_baseline_assignments_excluded"],
                "scope_assignments": agent["scope_assignments"],
                "exported_assignments": agent["exported_assignments"],
                "baseline_skill_ids": agent["baseline_skill_ids"],
                "skills": agent["skills"],
            }
            if local != safe:
                errors.append("per-agent manifest differs for " + alias)
        except Exception as exc:
            errors.append("cannot read per-agent manifest for " + alias + ": " + type(exc).__name__)

    assignments = manifest.get("assignments", [])
    if len(assignments) != 27:
        errors.append("manifest assignment row count is not 27")
    statuses = {"EXACT_COPY": 0, "REDACTED_NOT_VERBATIM": 0}
    actual_files = set()
    relative_reference_count = 0
    case_keys = {}
    for item in assignments:
        alias = item["agent_directory"]
        skill = item["skill_id"]
        if item.get("directory") != "agents/" + alias + "/skills/" + skill:
            errors.append("unexpected assignment path for " + alias + "/" + skill)
        skill_root = root / "agents" / alias / "skills" / skill
        if not (skill_root / "SKILL.md").is_file():
            errors.append("missing SKILL.md for " + alias + "/" + skill)
        for file in item.get("files", []):
            rel = Path(file["relative_filename"])
            if rel.is_absolute() or ".." in rel.parts:
                errors.append("unsafe relative filename for " + alias + "/" + skill)
                continue
            key = (alias, unicodedata.normalize("NFC", rel.as_posix()).casefold())
            if key in case_keys and case_keys[key] != rel.as_posix():
                errors.append("case-insensitive filename collision for " + alias + "/" + skill)
            case_keys[key] = rel.as_posix()
            path = skill_root / rel
            actual_files.add(path.relative_to(root).as_posix())
            if not path.is_file():
                errors.append("missing file " + str(path.relative_to(root)))
                continue
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if len(data) != file["bytes"] or digest != file["sha256"]:
                errors.append("size/hash mismatch: " + str(path.relative_to(root)))
            status = file.get("status")
            if status not in statuses:
                errors.append("invalid copy status for " + str(path.relative_to(root)))
            else:
                statuses[status] += 1
            if item.get("status") == "EXACT_COPY" and status != "EXACT_COPY":
                errors.append("exact skill contains a non-exact file: " + str(path.relative_to(root)))
            if path.suffix.lower() == ".json":
                try:
                    payload = json.loads(data.decode("utf-8"))
                    refs = []
                    resolve_refs(payload, refs)
                    for target in refs:
                        relative_reference_count += 1
                        if not (path.parent / target).is_file():
                            errors.append("unresolved JSON reference " + target)
                except Exception as exc:
                    errors.append("invalid JSON: " + str(path.relative_to(root)) + " (" + type(exc).__name__ + ")")
            if path.suffix.lower() == ".md":
                body = data.decode("utf-8")
                for target in LOCAL_REF.findall(body):
                    relative_reference_count += 1
                    if not (skill_root / target).is_file():
                        errors.append("unresolved skill reference " + target + " in " + str(path.relative_to(root)))

    found_files = {
        path.relative_to(root).as_posix()
        for path in (root / "agents").rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    }
    if actual_files != found_files:
        errors.append("skill file tree does not exactly match root manifest")
    if len(actual_files) != 55:
        errors.append("expected 55 skill files")
    if statuses != {"EXACT_COPY": 53, "REDACTED_NOT_VERBATIM": 2}:
        errors.append("copy-status totals are unexpected")
    if relative_reference_count != 24:
        errors.append("expected 24 resolved skill-relative references")
    total_bytes = sum(file["bytes"] for item in assignments for file in item["files"])
    if total_bytes != manifest.get("exported_bytes") or total_bytes != 248981:
        errors.append("exported byte total mismatch")

    print(json.dumps({
        "agents": len(manifest.get("agents", [])),
        "observed_total_effective_assignments": manifest.get("observed_total_effective_assignments"),
        "scope_assignments": len(assignments),
        "unique_skill_ids": manifest.get("unique_scope_skill_ids"),
        "skill_files": len(actual_files),
        "exact_copy_files": statuses["EXACT_COPY"],
        "redacted_files": statuses["REDACTED_NOT_VERBATIM"],
        "skill_relative_references_resolved": relative_reference_count,
        "exported_bytes": total_bytes,
        "errors": errors,
    }, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
