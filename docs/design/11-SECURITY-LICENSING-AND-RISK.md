# 11 — Security, Legal/Data Rights and Financial Safety

## Threat model in plain language

OpenBot preview agents can execute commands and access files; market and web content may contain instructions; Freqtrade API includes commands controlling the bot; the owner is a beginner who should not be expected to detect subtle permission errors. The product must be safe by technical separation, not only by asking an AI agent to 'be careful'.

## Host separation rule

**MVP needs two isolation domains:**

- **Trading lab domain:** Freqtrade dry-run instance, configs, DB, FreqUI admin endpoint, exporter. No exchange trade credentials in the MVP. Owner controls config changes and host lifecycle.
- **Agent research domain:** OpenBot with a sanitized, read-only copy of reports; no access to trading lab writable paths or management network routes; no Docker socket/host administrator privileges; no private API tokens.

The security acceptance must test that even an agent able to run arbitrary shell commands cannot reach or modify trading runtime state. If this cannot be achieved on the user's actual computer, fall back to **manual CSV/JSON report exchange**; do not deploy automatic OpenBot orchestration unsafely.

## Practical controls

1. No real or testnet exchange API keys for initial installation. Empty key/secret values are supported in Freqtrade dry-run configurations; verify installed version.
2. Freqtrade API binds owner-private loopback only (`127.0.0.1`); Docker port publication must explicitly bind loopback rather than all interfaces. API must be **unreachable** from OpenBot domain; avoid installing third-party REST-to-MCP bridge with write methods.
3. FreqUI owner login with long unique credentials; secrets stored outside version control; no credentials in AI prompts, reports or screenshots.
4. Only owner-controlled deployment process may write strategies/config, start/stop trader or change mode. An LLM recommendation is not authorization.
5. Separate directories, file ownership and permissions. A read-only mount within an OpenBot workspace is insufficient if the agent can reach the parent host or Docker socket.
6. Strict allowlist/schema size/UTF-8 validation for exported reports. Untrusted market/news text is **data**, never executable instructions. Record timestamps/hashes.
7. Version-pin images and libraries; scan changes and retest before upgrades; keep an offline rollback/backup.
8. Audit every owner changeset and model-generated suggestion; do not let agents install plugins or subprocesses outside the sandbox without owner consent.

## Legal/licensing table

| Component/source | Known issue | Required action before use |
|---|---|---|
| Freqtrade | GPL-3.0 open-source obligations if redistributing; API contains privileged controls | Review actual distribution plan; do not expose API to OpenBot/Internet |
| FreqUI | Bundled/associated Freqtrade UI; verify pinned-version use | Verify startup, authentication and license |
| OpenBot | Current source covered by **PolyForm Noncommercial**; commercial use requires separate license; versions ≤0.1.11 historically Apache-2.0 per upstream | Obtain commercial permissions or use a properly licensed pinned release/replace with alternative if needed; do not assume future profitable use is automatically permitted |
| Binance Vision public datasets | August 2026 terms generally CC BY-NC-SA 4.0; separately written commercial rights | No downloading under blocked P1; written owner/legal source decision first |
| Binance public REST / WebSocket data | Terms and intended use may differ from archives | Review venue jurisdiction, account limits, terms, API rate caps and permitted use before continuous deployment |
| TA-Lib / SMC / volume-profile packages | Separate project licenses and input/data fidelity | Pin exact version and inspect dependency/transitive licenses and code |
| Paid orderflow/data providers | Accuracy and licensing unverified; may require monthly fees | Reject until actual trial/contract + expected economic value justify spend |

**No legal conclusion is made here:** this is a risk/approval checklist. A software package being free of charge does not confer permission to commercialize its underlying exchange datasets.

## Financial loss controls

Paper only, with hard mode check and **no trading credentials**. Proposed carry-forward risk ceilings from the old charter require owner ratification and test proof: 0.25% modeled risk per trade, 0.50% aggregate, maximum 2 concurrent, ≤2x leverage, 1% daily new-entry halt, max 12h holding. Avoid averaging down; do not scale up automatically. These limits are paper-lab learning bounds, not proof of real-world loss protection.

## Incident escalation

- **Exposure of real keys or writable API:** STOP, disconnect agent/network, revoke keys through exchange if any ever existed, preserve logs, isolate host.
- **Unexpected `dry_run=false`:** startup gate refuses run; halt immediately.
- **Missing paper management on crash:** report as outage; never claim exchange protection; clean restart and reconcile DB.
- **Invalid data provenance:** mark result INVALID / NOT FOR PROMOTION, quarantine affected research outputs.
- **Licence breach concern:** suspend related data access, preserve audit and consult appropriate rights holder/adviser.

## Future real capital (explicitly excluded)

A separate live-readiness program would need independent exchange-side stop placement, actual fill/nonfill/partial behavior, protection while AI and Freqtrade are offline, reconciliation, approval authentication, single authorized writer and full legal review. Switching one Freqtrade flag is **not** a valid promotion process.
