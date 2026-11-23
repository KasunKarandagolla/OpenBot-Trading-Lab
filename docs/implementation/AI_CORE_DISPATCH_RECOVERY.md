# AI-core parent dispatch recovery

The owner brief reports that job `20261123T084728Z-df41c5be1afc410796a1097cce9326d7`
prepared a 39,263-byte discovery packet at `7cadbf9`. The parent received
incomplete arguments, made zero native submissions, and the stage ended with
`NATIVE_DISPATCH_RESERVED_TASK_MISSING`. The brief also records one
`NATIVE_STORAGE_TIMED_OUT` observation. The ZIP identified by
`778ab36e05c20b042a6176aacbb863b7fb00cce170392eeb231a06a83cca3f02`
and the original clipped parent result were unavailable in this checkout.
The reported 1,301 reconciliation rows are an archive disposition count.
They provide no evidence of model execution.

## Established cause and limits

- The pinned OpenBot schema accepts only trimmed `title` and `brief` strings
  with limits of 120 and 100,000 UTF-16 code units respectively. A 39,263-byte
  brief can fit. The reported failure occurred before a native call.
  [Task schema](https://github.com/nightly-labs/openbot/blob/a0b754f8baa8fb49fb200ffb3759b17429a962a9/src/backend/agent-tasks/agent-tasks.ts#L50-L55)
  · [Input limits](https://github.com/nightly-labs/openbot/blob/a0b754f8baa8fb49fb200ffb3759b17429a962a9/packages/contracts/src/input-limits.ts#L75-L86)
- At the failing commit the runner serialized the inline brief inside an outer
  JSON object containing ticket metadata. Newlines, quotes, and backslashes
  incur escaping overhead. The runner allowed up to 64 KiB, but linked the
  ticket before stdout reached its caller. The detached baseline reproduced
  the defect with a 39,263-byte synthetic brief, 42,178 bytes of stdout, and
  an independently imposed 8 KiB fixture cap. The cap is a test input.
- Codex's command stream can incur collection, token-based rendering and
  persistence limits. The pinned source has a separate 64 KiB persisted command
  output limit. The inner `max_output_tokens` setting cannot attest the
  outer Code Mode result, OpenBot tool presentation, or what ultimately
  remained in parent context. The exact clipping layer for the real job
  remains unverified. [Command output rendering](https://github.com/openai/codex/blob/d32063f96c2dff1dc96af839b3952abb6acfeda4/codex-rs/core/src/unified_exec/output.rs)
  · [Persisted output policy](https://github.com/openai/codex/blob/d32063f96c2dff1dc96af839b3952abb6acfeda4/codex-rs/rollout/src/policy.rs)

For a bounded owner-side read, inspect only the saved `status --include-review`
call for this job in its original parent turn. Compare its completed
`CommandExecution.aggregated_output` and associated model-facing
`function_call_output` or Code Mode `custom_tool_call_output`, if both are
retained. Record just the UTF-8 lengths, parseability, and truncation marker
for each. Complete execution output with clipped tool output locates the
loss after execution. A complete stored tool result with clipped display
requires presentation or context evidence. Save only these measurements.
This inspection requires no market or model activity.

## Corrected path

Both DISCOVERY and SHORTLIST publish a compact JSON preview capped at 4,096
UTF-8 bytes including the trailing newline. Status can repeat a preview
within the publication window. The first grant requires a canonical
round trip of every argument byte and the separate output end marker. The
confirmation carries the bytes, so an echoed digest alone cannot grant a
ticket. The runner records the preview SHA-256, exact argument and brief
hashes, argument bytes, brief UTF-8 and UTF-16 lengths, and frame counts. The
grant contains no large argument object. A partial confirmation can report
`NATIVE_PARENT_OUTPUT_TRUNCATED` and leave the material eligible for another
preview. A same-length alteration produces `NATIVE_PARENT_ARGUMENT_MISMATCH`.
A preview without a grant expires as `NATIVE_PARENT_DELIVERY_UNCONFIRMED`.

The immutable grant is published under the job lock after a scoped parent
identity check. A duplicate call receives no permission to submit. A valid
grant with no observed native task remains independently diagnosable. The
worker makes zero Windows submission or collection reads before the grant,
while preparation still checks installed skill and owner identity. Bounded
receipt observation resumes after the grant.

The compact task brief points the existing agent to at most five order-bound
page reads. Each encoded frame is at most 12,288 bytes and the next command
comes from the preceding frame. A page never relies on a separately
transcribed digest or a model-generated path. The independent reader checks
all command outputs and model-facing tool bytes, full concatenated evidence
SHA-256, exact task and model, and final output provenance. The evidence
selection and analytical stages are unchanged. The 39,263-byte fixture
reassembles in four pages. The two authorized native tasks can use up to
twelve observed provider response records because tool reads also require
provider responses. Historical inline and paged receipts keep their original
packet and ticket rules.

[Local installation and archived acceptance](AI_CORE_LOCAL_ACCEPTANCE.md)
