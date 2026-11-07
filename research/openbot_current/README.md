# OpenBot current-market handoff

This stages a sealed, public Binance USD-M research packet for the existing OpenBot team. Capture uses the repository's bounded downloader. The pinned offline research image runs the existing kline converter, causal 15m setup and 5m confirmation logic, and local PNG renderer. The charts and data carry UTC cutoffs. The public exchange rules and quote travel separately from private Demo account information.

## WSL capture and stage

From the root of the isolated Trading Lab checkout, run the following command. Supply a new run directory for each capture. The Matplotlib argument points to the existing local recovery dependency cache.

```bash
bash scripts/lab-openbot-current.sh \
  "../current-market-$(date -u +%Y%m%dT%H%M%S)" \
  "$HOME/OpenBot-Trading-Lab-local-recovery/user_data/data/local_recovery/mpl" \
  /mnt/c/Users/OWNER/OpenBot/Shared
```

Omit the Shared argument for a standalone capture. Each market scan makes at most 22 requests. Staging verifies the manifest and the three-minute freshness window before publishing a new candidate directory under `OpenBot/Shared/TradingLab-Integration-v1/staged`. Rerun the capture when this window has elapsed. Review a sealed older packet only as a record of what was observable at its cutoff.

Use the existing AstraBot Lead conversation to delegate the sealed packet. Send Market Researcher and Chart-Vision Analyst separate native messages. Attach the two PNGs to the Vision delivery and retain its native transfer receipt. Then send the original Vision findings to the Researcher for rebuttal. Send the original evidence and rebuttal to Independent Risk Reviewer and then Director. Keep the original source messages, timestamps, provider session and message IDs, roles, packet hash and skill-use evidence. Record a clear distinction between local skill files, runtime injection evidence and skill application. Require the Director to conclude MARKET_ENTRY, LIMIT_ENTRY, CONDITIONAL_ENTRY or NO_OPPORTUNITY. An UNKNOWN or VETO holds any proposed entry. The included deterministic gate evaluates a Director's structured proposal and evidence. Its PASS is limited to the supplied research inputs.

## Demo read boundary

The former separate-terminal signed reader is now fail-closed. A terminal under the
same WSL user does not isolate credentials from full-access Windows/OpenBot agents.
`openbot_demo_readonly.py --owner-run` reports EXECUTION_BLOCKED_CREDENTIAL_BOUNDARY
without opening the credential file or making a signed request. See
[WORKFLOW_V2.md](WORKFLOW_V2.md) for the new public-data workflow, deterministic gate,
offline recovery harness and the remaining isolated-service requirements.

## Rollback

The handoff is manual. Archive or rename only `TradingLab-Integration-v1` under OpenBot Shared to remove the staged packets from that path. Existing OpenBot configuration and profiles are independent of this folder. The isolated clone and its run folders can be kept as evidence.
