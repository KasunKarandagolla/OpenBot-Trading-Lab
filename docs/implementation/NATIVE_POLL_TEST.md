# Native polling integration test

This separately authorized test exercises one synthetic empty-discovery task
through the existing parent, confirmed preview, one-time grant, child page
reader, provider receipt and artifact delivery. It makes zero market requests.
It does not establish AI-core market research acceptance.

Install the published commit and its updated orchestration skill using the
checkout and skill installation steps in
[AI-core local acceptance](AI_CORE_LOCAL_ACCEPTANCE.md). Keep the existing
provider and model. After setup-only preflight, render the exact owner message
from the pinned checkout:

```bash
sed "s/@@APPROVED_COMMIT@@/$(git rev-parse HEAD)/g" docs/implementation/OPENBOT_POLL_TEST_PROMPT.txt
```

Paste the complete output once in the existing Trading Lab Market
Researcher's main OpenBot chat. The runner's start response includes the
canonical status command. Use the complete preview from ordinary status and
the preview's exact grant command. A granted or uncertain submission cannot
be repeated.

After the parent finishes and attaches its artifact, audit the saved job:

```bash
python3 -m researcher.openbot_runner replay-native --job-id JOB_ID
```

Pass criteria are one verified DISCOVERY receipt with confirmed exact parent
arguments and complete child page bytes, one native task, zero market requests,
a valid ZIP, and independently observed delivery. The fixture reply contains
an empty rows array. Preserve the job and artifact on failure. Only after this
integration test passes should the separately authorized archived AI-core
smoke be considered.
