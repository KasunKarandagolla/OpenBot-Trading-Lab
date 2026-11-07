# Inventory

## Count and scope

The persistent agent records identify five Codex-backed Trading Lab profiles. Their effective Codex root is each profile's .agents/skills directory. The alternative .claude/skills roots had the same skill directory names and byte-for-byte contents; they are provider mirrors, not additional assignments.

| Profile | Effective assignments installed | Trading Lab / Chart-Vision assignments in this snapshot | Generic OpenBot baseline assignments listed only | Exported skill folders |
|---|---:|---:|---:|---:|
| AstraBot Lead | 12 | 9 | 3 | 9 |
| Trading Lab Director | 9 | 6 | 3 | 6 |
| Trading Lab Market Researcher | 9 | 6 | 3 | 6 |
| Chart-Vision Analyst | 4 | 1 | 3 | 1 |
| Independent Risk Reviewer | 8 | 5 | 3 | 5 |
| Total | 42 | 27 | 15 | 27 |

The owner-reported 27 count matches the 27 specialist assignments after separating three generic baseline skills installed in each profile. The full observed installed count is 42. The 15 generic baseline assignments are listed below but their contents are not part of this Trading Lab-specific export.

## Specialist assignments exported separately by owner

### AstraBot Lead — 9 assignments

- openbot-chart-vision-analyst
- trading-lab-director-synthesis
- trading-lab-independent-risk-review
- trading-lab-market-regime-structure
- trading-lab-news-macro-operations
- trading-lab-opportunity-screening
- trading-lab-orderflow-volume-profile
- trading-lab-research-contract
- trading-lab-trade-geometry-management

### Trading Lab Director — 6 assignments

- trading-lab-director-synthesis
- trading-lab-independent-risk-review
- trading-lab-market-regime-structure
- trading-lab-news-macro-operations
- trading-lab-opportunity-screening
- trading-lab-research-contract

### Trading Lab Market Researcher — 6 assignments

- trading-lab-market-regime-structure
- trading-lab-news-macro-operations
- trading-lab-opportunity-screening
- trading-lab-orderflow-volume-profile
- trading-lab-research-contract
- trading-lab-trade-geometry-management

### Chart-Vision Analyst — 1 assignment

- openbot-chart-vision-analyst

### Independent Risk Reviewer — 5 assignments

- trading-lab-independent-risk-review
- trading-lab-news-macro-operations
- trading-lab-orderflow-volume-profile
- trading-lab-research-contract
- trading-lab-trade-geometry-management

## Generic OpenBot baseline assignments listed only

Each of the five profiles also has the following three installed skill IDs: openbot-data, openbot-site-hosting and openbot-skill-creator. This gives 15 baseline assignments in total. Their names and owners are listed for count transparency; their source contents are not exported in this specialist snapshot.

## Repeated specialist names across owners

| Skill ID | Assignment count | Owning profiles |
|---|---:|---|
| openbot-chart-vision-analyst | 2 | AstraBot Lead; Chart-Vision Analyst |
| trading-lab-director-synthesis | 2 | AstraBot Lead; Trading Lab Director |
| trading-lab-independent-risk-review | 3 | AstraBot Lead; Trading Lab Director; Independent Risk Reviewer |
| trading-lab-market-regime-structure | 3 | AstraBot Lead; Trading Lab Director; Trading Lab Market Researcher |
| trading-lab-news-macro-operations | 4 | AstraBot Lead; Trading Lab Director; Trading Lab Market Researcher; Independent Risk Reviewer |
| trading-lab-opportunity-screening | 3 | AstraBot Lead; Trading Lab Director; Trading Lab Market Researcher |
| trading-lab-orderflow-volume-profile | 3 | AstraBot Lead; Trading Lab Market Researcher; Independent Risk Reviewer |
| trading-lab-research-contract | 4 | AstraBot Lead; Trading Lab Director; Trading Lab Market Researcher; Independent Risk Reviewer |
| trading-lab-trade-geometry-management | 3 | AstraBot Lead; Trading Lab Market Researcher; Independent Risk Reviewer |

There are 9 unique specialist skill IDs and 27 assignments. Repeated contents are preserved in each owner directory; no shared or merged directory is used.

## Supporting files

- Chart-Vision Analyst and AstraBot Lead each contain the 15-file openbot-chart-vision-analyst skill: SKILL.md, nine references, two cases, two JSON schemas and one changelog.
- Each of the other 25 specialist assignments contains its original SKILL.md.
- No scripts, image assets, binary attachments or external files were present inside the 27 specialist skill directories.
- All local skill-relative references found in the exported files resolved within that owning skill directory. Some prose cites research implementation and evidence paths outside the skill package; those files are not moved into this snapshot.
- The sixth unrelated OpenBot profile was excluded. Only its identity/root metadata and skill directory names were used to distinguish it; its skill content was not read or hashed.
