# Owner-host setup-only preflight compatibility

Approved engineering baseline `fb6f8e3bb880e510929a737a744bedb5aeb995b5`.
This check covered the existing Researcher's setup session. It did not replay
the historical job's parent or child receipts.

## Provider schema

The active provider-session row pointed to an OpenBot-originated Codex
`0.171.0` thread using the `openai` backend and `gpt-6-luna`. The latest setup
turn began at `2026-11-22T05:02:41.806Z`. Windows Python accepted the exact
retained scope up to the setup command start at `05:16:26.436Z`, including 157
in-scope records and the exact bound turn model. The envelope used contiguous
ordinals, the existing timestamp/type/payload fields, and optional record
metadata. The required turn, command and response fields matched the
ordinal reader's existing contract. Additional payload fields such as
the agent message token count did not change those bindings.

The reader allows exactly `0.171.0` with that ordinal envelope. Both already
supported `0.169.0` formats still use the original adapter contract. Other
releases and unrecognized formats remain rejected. Owner, workspace,
backend, model, turn, timestamp, tool and receipt checks use the same paths.

At `05:29:51.441Z`, the saved turn contains `compacted`, including replacement
history, retained context and window IDs. A world-state record and a second
turn context follow it. Reading across that boundary still fails closed.
Supporting it would require validating replacement history ancestry, turn
attribution and receipt continuity across the compaction window.

The documented setup-only command returned `NATIVE_NOT_INVOKED` because the
Researcher had no running turn. Version compatibility passed on the retained
scope. A fresh active-context check still requires a separately authorized
setup-only turn. This check opened saved evidence, with zero market requests,
model requests or task submissions and `trade_authorization=false`.

## Registered orchestration skill

| Source | SHA-256 |
|---|---|
| Repository template | `1170500f182592cf6fe89f7aae04fb74fe68b7a0de96ae68b2bb2d601f318a27` |
| Both workspace orchestration files, rendered for the existing checkout | `a437942bb19fe9891ca176cbf66679c78b9edb10a773c52266fc7099df6319a0` |
| Repository and both workspace review files | `96830b0189fc13b141513d44d4146637a83f5ad6c10d8c51c954e2c9052250fb` |
| Registered revision 3, `SKILL.md` | `b07f402c6e9bed1a8b582afc2579170c030a3650314db0124bd098aaac527308` |
| Registered revision 3, archive | `d23cd2e5eb1036d7313da930b8340d5c32e2f4bc4b943aee822407308cf7f4e2` |

The registration is from the OpenBot local library. It retains three
bundles with archive times `2026-11-15T15:49:27Z`, `2026-11-18T20:10:36Z`
and `2026-11-21T12:36:05Z` respectively. The revision 3 archive and file
hashes agree with the workspace installation lock and with the earlier
workspace backup. The current workspace copies agree byte for byte with
the rendered repository template. OpenBot marks the registration modified
when installed bytes differ from the lock.

The full rendered comparison found behavioral differences. Revision 3
starts before native tool discovery, instructs the main agent to recover an
inline brief from disk, and tells the child to use zero tools. The approved
flow discovers the native tool first, sends the compact reserved argument
object, and requires fixed hash-bound page reads. Revision 3 also uses a
longer poll interval and omits the separate submission and response bounds.

Codex advertises the workspace `.agents` skill as the normal discovery
entry. The setup rollout contains two successful explicit
`openbot.read_local_skill` results for revision 3. Both returned the archive
body, which differs from the workspace body. The setup hash check covers the
workspace copies. Registration provenance requires its own readback.

The owner can approve publishing a new revision of the existing local
registration using the verified workspace directory
`.agents/skills/openbot-market-research` as the source. Require revision 3 as
the starting revision. Read back the successor archive and require its
`SKILL.md` to match the complete rendered template. Compare the archive and
file hashes against the new installation lock and both mirrors. Record the
approved commit, renderer substitution, revision and hashes. Keep the
review skill at its existing hash. Revision 3 remains blocked for use.

## Permission boundary

OpenBot 0.76.1 records this agent as Full access with its auto-approval
override enabled, and the provider context shows `danger-full-access`.
Computer Use is off. The provider exposes native shell execution and the
OpenBot tool catalog, including the native task, attachment, administrative
and routine operations. An unrelated MCP server is assigned to this agent.
Its installed entrypoint exposes synthetic fixture operations, including
plan preparation, with no order endpoint.

The required workflow uses the audited fixed WSL commands, scoped reads of
the provider and app records, local runner-state and artifact writes, and
the native discovery, same-agent task and attachment tools. The authorized
research run would also use approved public source access. Broader shell
writes, routine and agent administration, Computer Use and the unrelated
MCP server are outside that workflow.

Use the installed Workspace profile with the per-agent auto-approval
override off, and remove this agent's access to the unrelated MCP server.
The installed code maps Workspace to `workspaceWrite` and suppresses broad
automatic approvals. The runner writes under the checkout's `work/`
directory, including temporary requests to the Windows reader. Keep any
additional write grant at that boundary. Verify the Windows-to-WSL launcher,
query-only reader, local output path and attachment access in a
separately authorized setup-only check under that profile. The installed
contract supports Workspace, and the cross-OS setup under that profile
still needs owner-host verification.

## Decisions

| Gate | Decision |
|---|---|
| PROVIDER_SCHEMA | PASS for the verified 0.171.0 ordinal setup scope |
| REGISTERED_SKILL | BLOCKED pending the owner-approved replacement revision and readback |
| PERMISSIONS | OWNER_DECISION_REQUIRED for the narrowed profile and setup verification |

Overall status is NOT READY. The registry and permission changes require
separate owner authorization. Live acceptance requires separate authorization
after setup passes.

## Offline verification

The observed ordinal setup and receipt regressions both failed with the
baseline's version diagnostic. They pass with the exact release and
envelope allowlist. The focused suite passed 58 tests in 212.804 seconds.
The full suite passed 539 tests in 761.465 seconds from a scratch checkout
verified byte for byte against all 355 tracked files. Configuration
validation and comparisons of 28 protected paths against the baseline passed.
