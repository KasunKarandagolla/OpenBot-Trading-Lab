# Compact native paged Discovery acceptance

This is the first real test of `COMPACT_AI_CORE_PAGES_V1`. It uses the existing
Researcher, one synthetic Discovery task, no market requests and no trading.
The owner's reported earlier compact **inline** test is not paged acceptance.

1. In the existing owner-host checkout, fast-forward the clean
   `feature/external-first-market-researcher` branch to the verified published
   commit. Render `integration/openbot-market-research/SKILL.md` with the actual
   checkout path using the established installation procedure. The new
   orchestration skill must be installed and its approved local registration
   read back to match; a repository change does not install it. Keep the
   existing agent, provider/model and protected `market-research-review`
   skill. Run the setup-only preflight in the actual main chat and stop on any
   identity, permission, skill or schema failure. An unsupported provider is a
   compatibility failure; do not switch it for this test.
2. Render the exact commit-bound owner message from that checkout:

   ```bash
   sed "s/@@APPROVED_COMMIT@@/$(git rev-parse HEAD)/g" docs/implementation/OPENBOT_COMPACT_TEST_PROMPT.txt
   ```

   Send the rendered message once in the existing Researcher's main OpenBot
   chat. Use its installed fixed runner command and the returned exact status
   command. The single compact frame authorizes one task submission. If the
   frame is clipped or the submission outcome is uncertain, stop; do not
   submit a second task. Preserve the job and error for inspection.
3. After the response and attachment are saved, run the existing read-only
   `python3 -m researcher.openbot_runner replay-native --job-id JOB_ID` in the
   approved checkout. Require one validated DISCOVERY receipt, exact parent
   task arguments and acknowledged task ID, the configured provider/model,
   every provider-visible page and final reply, a cited synthetic hypothesis
   with a rival and a permitted question, no unauthorized operations, zero
   market requests and a verified archive. The attachment/final-delivery
   result is separate; report it as unverified unless observed.

A passing test establishes only the tested paged Discovery boundary for the
actual host, provider, model and record format. A separately observed two-stage
archived run and source qualification are still required before claiming a
complete AI Researcher or any live market coverage.
