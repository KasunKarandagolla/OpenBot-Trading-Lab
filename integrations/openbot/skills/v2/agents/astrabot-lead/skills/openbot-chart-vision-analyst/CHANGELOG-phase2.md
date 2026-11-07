# v2.0.0-research integration revision

Replaced hosted-only pilot with source-sealed local CHART, exact v2 schemas, causal feature definitions and pixel/source checks. Installed state remains unchanged. Current revision provenance is in the per-agent MIGRATION.json.

## Historical Phase 2 changelog (not current activation state)

# Phase 2 candidate skill changes

The supplied pack is preserved in the user's transfer folder. This working copy is version `0.1.3-research`; it is staged in the agent workspace and is **not registered or installed** in OpenBot.

## Change 1 — fail closed when no pixels reach the model

- Finding: the original `vision-assessment.schema.json` accepted `research_status=RESEARCH_CANDIDATE` while both `vision_pixels_seen` and every chart evidence `pixels_seen` were false.
- Change: the staged schema now restricts `research_status` to `WATCH`, `UNQUALIFIED`, or `REJECT_RESEARCH_THESIS` when `vision_pixels_seen=false`. The staged `SKILL.md` explicitly requires no visual claims and `UNQUALIFIED` if the model receives only URL/filename/metadata.
- Test: before change, 7 schema checks returned 7 schema-valid results, including the unsafe no-pixels candidate. After change, the same seven checks pass with that case rejected. Test command: `wsl.exe -d Ubuntu-24.04 -- python3 [REDACTED_PRIVATE_LOCAL_PATH]`.
- Remaining validation: per-image source authenticity, chart-symbol identity and missing/wrong-symbol refusal require runtime checks; JSON Schema alone cannot prove pixels or exchange mapping.

## Change 2 — reject unknown timestamp strings and un-timed candidates

- Finding: historical assessments used `UNKNOWN` for missing capture timestamps. The schema used `format: date-time`, but the earlier local validator omitted a `FormatChecker`, so malformed timestamps passed. Unknown values must be represented as JSON `null`; an actionable candidate must have a valid decision time, request time, receipt time, and last-closed-bar time.
- Change: timestamp fields now allow `null` for non-candidate research records and document that `UNKNOWN` is not a string value. Candidate status conditionally requires valid timestamps and visible pixels for every chart evidence item. The validator now enables JSON Schema date-time format checking.
- Test: the validator covers no-pixel and unknown-time fail-closed cases, null timestamps for a non-candidate, and a fully timestamped candidate. Results are stored beside the Phase 2 report.

## Change 3 — make timestamp format checks portable

- Finding: this environment's `jsonschema.FormatChecker` did not register the optional `date-time` checker, so a malformed timestamp still passed even with `FormatChecker()` enabled.
- Change: timestamp fields also have an RFC3339 lexical pattern. The test harness registers a strict `date-time` check that validates calendar values and timezone offsets, so both a string like `UNKNOWN` and an impossible date such as February 30 fail.
- Test: the local suite includes unknown strings, impossible dates, null timestamps on non-candidates, and complete candidate timestamps.

## No other modifications

The nine reference modules, two instructional cases, request schema and frozen trading recipes were retained without strategy-threshold edits. The changes are staged only; they have not been registered or installed in OpenBot.

Historical source: [immutable PR #19 file](https://github.com/KasunKarandagolla/OpenBot-Trading-Lab/blob/6f1a378269d962e019498369099bf1a5039c70a4/audits/openbot-skills/2026-11-07/agents/astrabot-lead/skills/openbot-chart-vision-analyst/CHANGELOG-phase2.md). Original SHA-256 `ea0be3f2d0cc134360b7fe64abbca7d777c4d5c1c051526e9788d189636feb64`. Revision `v2.0.0-research`; current instructions supersede historical venue/tool assumptions without modifying frozen studies.
