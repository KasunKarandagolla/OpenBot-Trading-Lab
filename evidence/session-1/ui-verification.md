# FreqUI and paper startup verification

**PASS — authenticated HTTP verification in Codex Cloud; browser rendering REQUIRES OWNER-HOST VERIFICATION.**

Official image contains FreqUI **3.2.1** (`/freqtrade/freqtrade/rpc/api_server/ui/installed/.uiversion`). `./scripts/lab.sh ui-up` started supported Freqtrade `webserver` mode. Actual Docker port binding was **127.0.0.1:8080 -> container 8080**. No public host bind, custom frontend or agent bridge.

`python scripts/ui_smoke.py` fetched HTML and 14 installed JS/CSS assets (all HTTP 200), ping (200), protected version without authentication (401), Basic-auth token login (200), authenticated version (200), authenticated `/api/v1/backtest/history` (200), and `/api/v1/backtest/history/result` (200). Returned native result contained **386 trades** from TrendPullbackBaselineV1. Password/JWT values were held in memory only and excluded from evidence. See `ui-http-smoke.json` for paths/statuses/timestamps.

No graphical screenshot or rendered-screen acceptance is claimed. On the owner host: start ui-up, open http://127.0.0.1:8080, connect to the local bot, use `owner` and the private api.json password, open Backtesting/history and inspect the exported run. Then run ui-down. The static entry point and ping are public locally; management/research APIs require authentication.

`./scripts/lab.sh paper-up` was a separate, deliberate temporary smoke, never installation/test default. Paper API authenticated successfully and showed futures, dry_run=true, max 2, configured stake 25, forced entry disabled, running strategy 1.0.0 and zero open paper trades. See `paper-http-smoke.json`. The SQLite file persisted locally (94,208 bytes at shutdown). This does not validate restart with positions, filled-paper lifecycle, future uptime or exchange protective stops.

Cloud UI observed idle memory: **252.6 MiB**, CPU **0.10%** at one snapshot; not a peak or capacity guarantee. Research runner observed about 276.4 MiB outside peak backtest work. Official image size **948,111,339 bytes**, linux/amd64. Docker VFS container copies consumed substantial additional disk.

UI was stopped/removed before the paper smoke to fit Cloud disk. Paper was explicitly stopped after environment recovery. Shutdown log confirms application shutdown complete and SIGINT exit 130. `shutdown-verification.json` records stopped state, loopback publication and no exchange-credential environment names. No temporary lab service is left running.
