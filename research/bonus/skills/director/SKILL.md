---
name: openbot-director-synthesis
description: Reconcile research and risk reports and journal decisions in the existing Director role.
---

Require matching decision IDs and as-of clocks. Resolve factual disagreement against the cited frozen evidence, without averaging opinions or inventing a confluence score. Missing evidence, an expired trigger, a VETO or UNKNOWN mandatory risk review means NO_TRADE.

Produce `decision_id`, `asof`, `decision` (RESEARCH_TRADE/WATCH/NO_TRADE), `recipe_version`, `risk_review`, `evidence_ids`, `contradictions`, `reason`, `execution_authority` (`NONE`). A RESEARCH_TRADE is a journal recommendation, never permission for an engine order.

Journal native admission and fill results separately from the recommendation. Preserve negative results and immutable source hashes. Distinguish a valid losing trade from an evidence or execution failure. Attach improvements as new research hypotheses, never edits to frozen rules. Economic qualification requires independent evidence; the bonus results alone authorize no promotion.

No persistent service, owner alerts, credentials, paid data, paper start or live action is granted by this skill. See [validation cases](../cases.json).
