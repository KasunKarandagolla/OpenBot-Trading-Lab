# Bounded Codex Vision forward review

Status: **PARTIAL — source/pixel reading and bounded request creation demonstrated; native OpenBot application and changed-view insight not demonstrated.** This reviewer is a Codex evaluation subagent, not the original Chart-Vision Analyst or Independent Risk Reviewer.

## Frozen evidence and scope

Candidate `XRPUSDT-20261107T050624-6eeb478477`; Binance PUBLIC USD-M, cutoff **2026-11-07 05:06:24.014 UTC** (`1794027984014`). Packet MANIFEST SHA-256 `bfe6695cb7b9f3d058a2585424f566855d06059ff3490b0e1612f9206085e17b`. This is historical review at evaluation time, not a current-market proposal. No later bars, outcome panels, private messages or other agent conclusions were read.

Tools actually used: `exec_command` to read the skill, source JSON and hashes; `view_image` with `detail=original` to deliver all four 1920×1080 PNGs to this inference; the real Python `trading_lab.skills bootstrap`, `request`, and `validate_assessment` interfaces. Native message/session/attachment receipts: **none**. Local pixel inspection does not establish native transfer.

| Default image | Visible bars | Verified PNG SHA-256 | Last bar availability (ms UTC) |
|---|---:|---|---:|
| 4h | 120 | d865f36bf3e8ee565612fb869d2e601a65eaaaa6114ab82e8e3629b89665e5f9 | 1794024000000 |
| 1h | 150 | 366701dbf8a4c969e22b0a0ea9fd3acd8b0019719c7abe259b42f5a25cab3148 | 1794027600000 |
| 15m | 144 | cff60e60fd8f9579f4ed1480ce2568c7845da8cc7362ddfbad742957e38150e4 | 1794027600000 |
| 5m | 72 | 487988f9f23575e1cea4646f1c5f1f6ab6e26796d72e75954b159d5a222b238a | 1794027900000 |

Each image's title identifies XRPUSDT/Binance PUBLIC USD-M and the common cutoff; price axes and UTC time axes are readable, and aligned volume bars are labeled base units. Defaults have no overlays, so no hidden VWAP/EMA reading is claimed. The varying last completed time is expected across timeframes, not a synchronized live candle. All four image hashes matched their source receipts.

## Independent clean read

- **VISIBLE:** The 4h view shows substantial downside extension after the earlier rally; the 1h view has repeated lower highs/lows after its breakdown. The 15m view also descends into the latest lows. These observations support continuation research, not automatic short admission.
- **VISIBLE:** The 5m view shows sharp downside expansion followed by a small base/bounce. It does not establish a higher-timeframe reversal or prove a sweep of a boundary known before the excursion. Candle volume is not CVD or liquidation evidence.
- **NUMERIC_VERIFIED:** The latest completed 5m close is **1.1560**, available 05:05 UTC, against the matching 5m source SHA `6eeb47847725228a0e6a81c714f76dbbd132142616d7f3eac8cf6dbcacddd09c`. The latest completed hourly bar closes **1.1549** at 05:00 UTC. The numerical feature record labels both 1h and 4h DOWN; these labels were checked after the clean pixel read.
- **Strongest opposing fact for a reversal long:** Declining higher-timeframe structure and unreclaimed nearby lower-high resistance. **Strongest opposing fact for an immediate short:** Price is already extended toward the lows and could rebound; chasing an extended leg can offer poor structural entry/target geometry even with the broader direction correct.

## Competing hypotheses and specific locations

These are descriptive research hypotheses, not new frozen strategies or exact order triggers.

1. **Continuation:** A corrective rebound stalls below pre-known lower-high resistance, then a later completed trigger qualifies under an existing versioned recipe. This interpretation weakens if local resistance is reclaimed and defended with a higher-low sequence. A short immediately at the lows is not thereby qualified.
2. **Local transition/reversal:** The base holds and later completed bars reclaim nearby resistance, then defend it under a registered recipe. A renewed downside break without reclaim weakens this interpretation. A green candle by itself is insufficient.

The strict current chart 2L/2R function recomputed from the raw completed 5m bars identifies resistance **1.1606** at pivot 03:55, known only **04:10**; resistance **1.1581** at pivot 04:20, known **04:35**; support **1.1512** at pivot 04:40, known **04:55**; resistance **1.1564** at pivot 04:50, known only **05:05**. These are numerical chart-feature references, not pixels transcribed as exact prices, and they do not replace the frozen recipe's own structure definition. The final 1.1560 close remains below those nearby resistance references.

The exact declared research horizon, stop buffer, realistic target obstacle, current execution costs and independent account-qualified risk remain unestablished. Candidate metadata states `NO_QUALIFIED_SETUP` with hypothesis null. Therefore the research conclusion remains **WATCH / no proposal**, with `TRIGGER_VALID` unknown and `TRADE_ADMISSIBLE` not established. No economic edge is inferred.

## Changed-view request

`work/vision-forward-request.json` was generated by the actual adapter, exit **0**, as `openbot.shared.request.v2`, kind CHART, outer request ID `vision-forward-pivots-r1`, chart request ID `vision-forward-pivots`, revision 1, 5m, 120 completed candles, volume, and only `confirmed_swings` overlay. It asks:

> Does the post-selloff bounce reclaim any pre-known 5m resistance, or remain below the breakdown structure?

The view extends the six-hour default to ten hours without future bars or crowding. It would make the sequence and causal beginning of lower-high levels easier to inspect. The request was **not submitted to an OpenBot native service** and no changed image was returned during this bounded review. `insight_gained=null` is truthful; no revised conclusion or agent-generated native revision is claimed. At any later submission, regenerate the outer UTC creation/expiry fields; keep the historical sealed cutoff unchanged.

## Reproduced findings and residual limits

- **P2, skill direct-fallback usability**, `integrations/openbot/skills/v2/agents/chart-vision-analyst/skills/openbot-chart-vision-analyst/SKILL.md:18`: `skills request` emits the full Shared envelope while the documented `workflow chart PACKET CHART_JSON ...` fallback accepts its nested chart object. Copying the generated request file directly into that fallback fails `CHART_UNKNOWN_FIELD`. Reproducer: `validate_request(envelope, identity)` raised that exact error; `validate_request(envelope['payload']['chart'], identity)` passed in the same process, command exit **0**. Add an exact extraction command or a direct-chart output option and a round-trip test. Runtime refusal is correct; the missing adaptation is a novice workflow gap.
- **Causal assessment limit**, `scripts/trading_lab/skills.py:validate_assessment`: the raw-OHLC price matcher checks a value at a cited bar's availability, not the semantic claim that a pivot was already confirmed. The real 1.1564 bar is complete at 04:55 but its 2L/2R confirmation is 05:05. A free-text claim can conflate those times unless structured pivot/known-at/version evidence is validated. Add typed feature evidence or explicitly limit claims of validator coverage; do not report generic source matching as causal-feature proof.
- A schema/receipt check cannot independently prove model pixel delivery or authenticate arbitrary native receipt strings. This review's actual view-image deliveries substantiate local inspection only.

The structured assessment below passed `validate_assessment`, command exit **0**. Its validator result is {"limitation": "Metadata assertions do not prove actual inference pixel delivery", "native_delivery_verified": false, "order_authorized": false, "pixel_delivery_independently_verified": false, "scope": "SCHEMA_SOURCE_AND_RECEIPT_CHECKS", "status": "PASS"}.

## Structured advisory assessment

```json
{
  "schema": "openbot.vision.assessment.v2",
  "candidate_id": "XRPUSDT-20261107T050624-6eeb478477",
  "packet_sha256": "bfe6695cb7b9f3d058a2585424f566855d06059ff3490b0e1612f9206085e17b",
  "cutoff_ms": 1794027984014,
  "execution_authority": "NONE",
  "order_authorized": false,
  "research_status": "WATCH",
  "interest": "MARKET_INTERESTING",
  "trigger": "UNKNOWN",
  "admissibility": "NOT_ESTABLISHED",
  "images": [
    {
      "request_id": "default-5m",
      "revision": 1,
      "image_sha256": "487988f9f23575e1cea4646f1c5f1f6ab6e26796d72e75954b159d5a222b238a",
      "source_sha256": "6eeb47847725228a0e6a81c714f76dbbd132142616d7f3eac8cf6dbcacddd09c",
      "packet_sha256": "bfe6695cb7b9f3d058a2585424f566855d06059ff3490b0e1612f9206085e17b",
      "timeframe": "5m",
      "symbol": "XRPUSDT",
      "venue": "BINANCE_PUBLIC_USDM",
      "cutoff_ms": 1794027984014,
      "last_available_ms": 1794027900000,
      "pixels_seen": true,
      "delivery": "LOCAL_PIXEL_INSPECTION",
      "attachment_id": null,
      "message_id": null
    }
  ],
  "observations": [
    {
      "text": "The 5m pixels show a sharp selloff followed by a small base and bounce; this is not sufficient evidence of a higher-timeframe reversal.",
      "classification": "VISIBLE",
      "evidence_id": "default-5m-r1",
      "price": null,
      "source_sha256": null,
      "available_at_ms": null
    },
    {
      "text": "The latest completed 5m close is 1.1560, available at 05:05 UTC.",
      "classification": "NUMERIC_VERIFIED",
      "evidence_id": "candles/5m.json:last-close",
      "price": "1.1560",
      "source_sha256": "6eeb47847725228a0e6a81c714f76dbbd132142616d7f3eac8cf6dbcacddd09c",
      "available_at_ms": 1794027900000
    }
  ],
  "hypotheses": [
    {
      "name": "Downside continuation after corrective rebound",
      "confirm_if": "A separately registered recipe establishes a later completed continuation trigger after testing a pre-known obstacle; this descriptive map alone is not a trigger.",
      "invalidate_if": "Reclaimed local resistance and a sustained higher-low sequence would undermine the immediate lower-high continuation interpretation."
    },
    {
      "name": "Local transition or failed downside extension",
      "confirm_if": "Subsequent completed bars reclaim pre-known local resistances and defend the base under an explicitly frozen recipe.",
      "invalidate_if": "A renewed completed downside break through the base without a reclaim would undermine the base/reversal hypothesis."
    }
  ],
  "contradictions": [
    "Higher-timeframe downside structure opposes a reversal long.",
    "A short at the immediate lows could chase an extended leg and face a rebound; attractive direction is not good entry location."
  ],
  "unknowns": [
    "Frozen packet has no qualified setup.",
    "No account-qualified Risk review, fees/slippage/funding stress or actual fill evidence.",
    "Trade-level flow/CVD unavailable; kline participation is a proxy.",
    "Targeted chart request generated but not rendered/received during this review.",
    "No native OpenBot message or attachment receipt."
  ],
  "insight_gained": null,
  "confidence": "PARTIAL_EVIDENCE"
}
```


## Second pass — actual requested pixels returned

Status update: **PASS for this bounded Codex local request/render/pixel/reassessment sequence; native OpenBot application remains PARTIAL/BLOCKED.** The parent operator rendered this reviewer's generated request with actual program code. This is operator transport of a Codex-generated request, not the original OpenBot Chart-Vision Analyst invoking its own tool.

The actual revision `vision-forward-pivots-r1/chart.png` was delivered with `view_image(detail=original)` and inspected at 1920×1080. Image SHA-256 `d2e650079a34fd80395fd16fa315a85ce7c11f4db8a6746b83fa468fc55c8292`; request SHA-256 `d8101a1c820539b8f57912b6beee9b6a916f74ce772b72013c0bc200aed4ba43`. Source SHA and packet SHA match the original sealed 5m source and MANIFEST. The view shows 120 completed 5m bars, first-open `1793991900000` (2026-11-06 19:05 UTC), last availability `1794027900000` (05:05 UTC), all before the unchanged cutoff. No later market data were read.

The UTC axis, USDT price axis, completed-candle header, source venue/symbol, base-volume panel and support/resistance legend are readable. No price focus cropping is applied. Five purple horizontal level segments are visible; they are not labeled with precise values in the pixels, so exact values were taken from the receipt and independently recomputed from raw bars. **All five receipt levels match `confirmed_swings` on the sealed data**, including their pivot and confirmation times. Two plotted overhead resistance levels are 1.1606 (known 04:10 UTC) and 1.1581 (known 04:35 UTC); plotted base support includes 1.1509, 1.1516 and 1.1512. There is no VWAP/EMA overlay, so neither is inferred visually.

The last raw 1.1564 resistance becomes known at 05:05, after the last candle's plotted opening coordinate at 05:00. It is therefore **not drawn as a horizontal level in this PNG**; this review does not misreport it as a visible line. It remains a separately typed numerical feature at the terminal close.

**Actual insight gained:** the expanded context and causal line starts make the base and overhead barriers explicit: the local bounce is contained below the two plotted pre-known resistance segments, while support clusters at the recent lows. This clarifies the revisit map and guards against labeling the bounce a structural reversal. The original clean charts already suggested that relationship, so the improvement is clearer evidence/location rather than a new directional call. **Conclusion unchanged: WATCH, no qualified frozen trigger and no trade proposal.** This one case is not an N versus N+V experiment or proof of incremental economic value.

The new structured assessment is `work/vision-forward-assessment-v2.json`. It includes mandatory `feature` tags and typed CONFIRMED_SWING evidence with feature version, pivot-open and known-at times. The current validator accepted it, command exit **0**. Moving the real 1.1564 swing's availability/known-at back to 04:55 reproduced `SWING_CONFIRMATION_OR_PRICE_MISMATCH`, confirming that the earlier causal-validation gap is corrected for the typed swing path. The parent also added `skills chart` to accept the Shared envelope directly; the old direct `workflow chart` shape refusal remains intentional.

Validator result: `{"limitation": "Metadata assertions do not prove actual inference pixel delivery", "native_delivery_verified": false, "order_authorized": false, "pixel_delivery_independently_verified": false, "scope": "SCHEMA_SOURCE_AND_RECEIPT_CHECKS", "status": "PASS"}`.
