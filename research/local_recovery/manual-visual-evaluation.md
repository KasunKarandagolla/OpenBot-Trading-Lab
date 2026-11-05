# OpenBot manual visual evaluation

OpenBot image reception and host isolation are **NOT TESTED**. Use this packet through the owner's authorized research-only image input after verifying that the chosen environment provides no access to the lab, credentials, Docker, shell or trading administration.

1. Verify the packet using `scripts/local_recovery_verify_packet.py`. Copy only its `evidence-card.json`, `source-receipt.json`, and the two image files listed in the card to the isolated environment. Keep outcome files outside that environment.
2. Start with the insufficient-history control. Require `INPUT_INSUFFICIENT` and a list of the missing timeframe windows. The card for this control has no image files.
3. On each adequate case, run A with the card only and B with the identical card plus its two images. Use the same model and configuration. Use separate contexts for A and B. Keep all answer timestamps, model IDs, input and output token counts, latency and any cost. Record `VISION_RUNTIME_UNAVAILABLE` if actual image delivery cannot be verified.
4. Freeze A and B before looking at subsequent candles. Compare whether B identified a verifiable feature, corrected a contradiction, or changed the decision on the basis of evidence available at the cutoff. Use the numerical card to check quoted prices, states and clocks. These first cases are handoff checks.

## Paired pilot

From the lab checkout, register the fixed development sample using `scripts/lab-local-recovery.sh pilot register`. This writes `user_data/data/local_recovery/development/visual-pilot/trial-cases.json`. Render a listed case with `scripts/lab-local-recovery.sh pilot render DECISION_ID`. Four cases per playbook and state cover armed, invalidated and proposed decisions. The selector uses the frozen decision ledger and does not read economic results. Rendered cases go in the local pilot packet folder.

Record both replies as JSON under the ignored local data directory. Add `model_id`, `configuration_id`, `latency_ms`, `input_tokens`, `output_tokens` and `cost_usd` to the reply record. Put numeric claims in `numeric_claims` as objects with `field` (dotted card path, with zero-based indexes) and `value`. Use a list of exact filenames for `images_received`. Then run `scripts/lab-local-recovery.sh pilot compare CARD A B`, with paths relative to the lab checkout, to verify paired clocks and numeric claims and record reply hashes. Actual image delivery requires runtime evidence independent of the model's reply.

## Prompt

> Read the historical chart packet and return JSON with `decision_id`, `as_of`, `input_status`, `images_received`, `primary_thesis`, `alternative_thesis`, `levels`, `supporting_facts`, `opposing_facts`, `playbook`, `state`, `invalidation`, `required_5m_trigger`, and `unknowns`. For each numeric claim, give the evidence-card field and its exact value. Identify a visible feature independently for each attached image, or say which file was missing. Use the time and state in the historical packet. Separate a published taker share from evidence about executed-trade profiles or order-book depth. Treat a proposed order as a hypothesis. Describe contradictions and stop at the evidence cutoff.

The Market Researcher can write the analysis. The Independent Risk Reviewer checks the clock, source, invalidation and execution assumptions. The Director summarizes the two records. The deterministic backtest gates remain authoritative.
